"""
Image processing for geometry TikZ generation.

Contains the core logic for processing images and generating TikZ diagrams.
Two modes:
  - generate: Generate TikZ code and render images
  - segment: Generate segmentation annotations for existing outputs
"""

import json
import shutil
import re
from datetime import datetime
from pathlib import Path

from .llm_helper import generate_tikz_from_image, generate_synthetic_segmentation, SegmentationResult
from .tikz_helper import compile_tikz_to_png, save_failed_tikz


# =============================================================================
# STAGE 1: TikZ Generation
# =============================================================================

def process_generate(
    client,
    image_path: str,
    output_dir: Path,
    image_index: int,
    create_variation: bool = False,
    model: str = "Qwen/Qwen3-VL-235B-A22B-Instruct",
    dpi: int = 300,
    use_in_context_examples: bool = False
) -> bool:
    """
    Stage 1: Generate TikZ code from image and render PNG.
    
    Creates output structure:
        output_dir/
        └── generated_001/
            ├── original.png  # Original source image
            ├── img.png       # Rendered TikZ PNG
            ├── img.tex       # TikZ source code
            └── img.json      # Metadata
    
    Args:
        client: OpenAI client instance
        image_path: Path to input image
        output_dir: Root output directory
        image_index: Image index for naming (e.g., 1 -> "generated_001")
        create_variation: Whether to create variation
        model: Model to use for generation
        dpi: Output resolution
        use_in_context_examples: Whether to include in-context examples in prompt
    
    Returns:
        True if successful, False otherwise
    """
    base_dir_name = f"generated_{image_index:03d}"
    output_path = output_dir / base_dir_name
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Define output paths
    tex_path = output_path / "img.tex"
    png_path = output_path / "img.png"
    json_path = output_path / "img.json"
    original_path = output_path / "original.png"
    
    try:
        # Step 1: Generate TikZ code with reasoning from image
        print(f"  Generating TikZ code...", end=" ", flush=True)
        result = generate_tikz_from_image(
            client, 
            image_path, 
            create_variation=create_variation, 
            model=model,
            use_in_context_examples=use_in_context_examples
        )
        print("done")
        
        # Step 2: Copy original image
        if image_path and Path(image_path).exists():
            print(f"  Copying original image...", end=" ", flush=True)
            shutil.copy(image_path, original_path)
            print(f"done -> {original_path.name}")
        
        # Step 3: Save TikZ source code
        print(f"  Saving TikZ code...", end=" ", flush=True)
        with open(tex_path, 'w') as f:
            f.write(result.tikz_code)
        print(f"done -> {tex_path.name}")
        
        # Step 4: Compile TikZ to PNG
        print(f"  Compiling to PNG...", end=" ", flush=True)
        success = compile_tikz_to_png(result.tikz_code, str(png_path), dpi=dpi)
        
        if not success:
            print("failed")
            failed_path = output_path / "img_failed.tex"
            save_failed_tikz(result.tikz_code, str(failed_path))
            print(f"  Saved failed code to {failed_path.name}")
            return False
        
        print(f"done -> {png_path.name}")
        
        # Step 5: Get image dimensions
        width, height = 0, 0
        try:
            from PIL import Image
            with Image.open(png_path) as img:
                width, height = img.size
        except:
            pass
        
        # Step 6: Save metadata JSON
        metadata = {
            "source_image": image_path,
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "image": {
                "width": width,
                "height": height,
                "dpi": dpi,
            },
            "reasoning": result.reasoning,
            "tikz_code": result.tikz_code,
        }
        
        print(f"  Saving metadata...", end=" ", flush=True)
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"done -> {json_path.name}")
        
        return True
        
    except Exception as e:
        print(f"error: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# STAGE 2: Segmentation
# =============================================================================

def process_segment(
    client,
    output_dir: Path,
    image_index: int,
    model: str = "Qwen/Qwen3-VL-235B-A22B-Instruct",
    dpi: int = 300,
) -> bool:
    """
    Stage 2: Generate segmentation for an existing generated output.
    
    Requires existing:
        output_dir/generated_001/
            ├── img.png
            └── img.tex (or img.json with tikz_code)
    
    Creates:
        output_dir/generated_001/segmentation/
            ├── seg.json
            └── rendered/
                ├── 001_pos_query.png
                └── ...
    
    Args:
        client: OpenAI client instance
        output_dir: Root output directory
        image_index: Image index (e.g., 1 -> "generated_001")
        model: Model to use for segmentation
        dpi: Output resolution for rendered overlays
    
    Returns:
        True if successful, False otherwise
    """
    base_dir_name = f"generated_{image_index:03d}"
    output_path = output_dir / base_dir_name
    
    # Check if output exists
    png_path = output_path / "img.png"
    tex_path = output_path / "img.tex"
    json_path = output_path / "img.json"
    
    if not output_path.exists():
        print(f"  Error: {output_path} does not exist")
        return False
    
    if not png_path.exists():
        print(f"  Error: {png_path} does not exist")
        return False
    
    # Load TikZ code
    tikz_code = None
    if tex_path.exists():
        with open(tex_path, 'r') as f:
            tikz_code = f.read()
    elif json_path.exists():
        with open(json_path, 'r') as f:
            metadata = json.load(f)
            tikz_code = metadata.get('tikz_code')
    
    if not tikz_code:
        print(f"  Error: Could not load TikZ code")
        return False
    
    try:
        # Generate segmentation using the rendered image
        print(f"  Generating segmentation annotations...", end=" ", flush=True)
        segmentation = generate_synthetic_segmentation(
            client,
            str(png_path),
            tikz_code,
            model=model,
        )
        print(f"done ({len(segmentation.annotations)} annotations)")
        
        # Save segmentation results
        if segmentation and segmentation.annotations:
            _save_segmentation_results(
                output_path=output_path,
                tikz_code=tikz_code,
                segmentation=segmentation,
                dpi=dpi,
            )
        
        return True
        
    except Exception as e:
        print(f"error: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# Helper Functions
# =============================================================================

def _sanitize_filename(query: str, max_length: int = 40) -> str:
    """Convert a query string to a valid filename."""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[^\w\s-]', '', query)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = sanitized.lower().strip('_')
    return sanitized[:max_length] if sanitized else "query"


def _save_segmentation_results(
    output_path: Path,
    tikz_code: str,
    segmentation: SegmentationResult,
    dpi: int = 300,
) -> None:
    """
    Save segmentation annotations and render overlays.
    
    Creates:
        output_path/segmentation/
            ├── seg.json
            └── rendered/
                ├── 001_query_name.png
                └── ...
    """
    seg_dir = output_path / "segmentation"
    rendered_dir = seg_dir / "rendered"
    seg_dir.mkdir(parents=True, exist_ok=True)
    rendered_dir.mkdir(parents=True, exist_ok=True)
    
    # Save seg.json
    seg_json_path = seg_dir / "seg.json"
    annotations_data = [
        {
            "query": ann.query,
            "exists": ann.exists,
            "reasoning": ann.reasoning,
            "append_tikz": ann.append_tikz,
        }
        for ann in segmentation.annotations
    ]
    
    print(f"  Saving segmentation data...", end=" ", flush=True)
    with open(seg_json_path, 'w') as f:
        json.dump({"annotations": annotations_data}, f, indent=2)
    print(f"done -> segmentation/seg.json")
    
    # Render all annotations
    print(f"  Rendering segmentation overlays...", end=" ", flush=True)
    rendered_count = 0
    positive_count = 0
    negative_count = 0
    
    for i, ann in enumerate(segmentation.annotations):
        # Create filename from query (prefix with pos/neg)
        query_name = _sanitize_filename(ann.query)
        prefix = "pos" if ann.exists else "neg"
        render_filename = f"{i+1:03d}_{prefix}_{query_name}.png"
        render_path = rendered_dir / render_filename
        
        if ann.exists:
            # Positive: use the provided overlay
            if not ann.append_tikz.strip():
                continue
            combined_tikz = _append_overlay_to_tikz(tikz_code, ann.append_tikz)
        else:
            # Negative: add text overlay showing the query
            text_overlay = _create_negative_text_overlay(ann.query)
            combined_tikz = _append_overlay_to_tikz(tikz_code, text_overlay)
        
        # Compile to PNG
        if compile_tikz_to_png(combined_tikz, str(render_path), dpi=dpi):
            rendered_count += 1
            if ann.exists:
                positive_count += 1
            else:
                negative_count += 1
    
    print(f"done ({positive_count} pos, {negative_count} neg)")


def _append_overlay_to_tikz(tikz_code: str, overlay: str) -> str:
    """Append overlay TikZ code before \\end{tikzpicture}."""
    end_marker = "\\end{tikzpicture}"
    if end_marker in tikz_code:
        # Insert overlay before the end marker
        idx = tikz_code.rfind(end_marker)
        return tikz_code[:idx] + "\n% Segmentation overlay\n" + overlay + "\n" + tikz_code[idx:]
    else:
        # Just append if no end marker found
        return tikz_code + "\n% Segmentation overlay\n" + overlay


def _create_negative_text_overlay(query: str) -> str:
    """Create a TikZ text overlay for negative (non-existent) queries."""
    # Escape special LaTeX characters
    escaped_query = query.replace('_', r'\_').replace('&', r'\&').replace('%', r'\%')
    # Create centered red text with the query and a "?" or "NOT FOUND" indicator
    return f"""% Negative query overlay
\\node[red, font=\\large\\bfseries, fill=white, fill opacity=0.8, text opacity=1, rounded corners, inner sep=4pt] at (current bounding box.center) {{{escaped_query}?}};
\\node[red!70!black, font=\\small\\itshape, below=0.3cm of current bounding box.center] {{(not found)}};"""

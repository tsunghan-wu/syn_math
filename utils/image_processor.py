"""
Image processing for geometry TikZ generation.

Contains the core logic for processing images and generating TikZ diagrams.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from .llm_helper import generate_tikz_from_image
from .tikz_helper import compile_tikz_to_png, save_failed_tikz


def save_results(
    tikz_code: str,
    output_dir: Path,
    base_dir_name: str,
    reasoning: str = "",
    dpi: int = 300,
    model: str = "",
    source_image_path: str = "",
) -> bool:
    """
    Save all results for a generated TikZ diagram.
    
    Creates output structure:
        output_dir/
        └── generated_001/
            ├── original.png  # Original source image
            ├── img.png       # Rendered TikZ PNG
            ├── img.tex       # TikZ source code
            └── img.json      # Metadata (image stats, prompts, reasoning)
    
    Args:
        tikz_code: Generated TikZ code
        output_dir: Root output directory
        base_dir_name: Name for the base output subdirectory (e.g., "generated_001")
        reasoning: Step-by-step reasoning from the model
        dpi: Output resolution for PNG
        model: Model name used for generation
        source_image_path: Path to the source image
    
    Returns:
        True if successful, False otherwise
    """
    # Create output directory
    output_path = output_dir / base_dir_name
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Define output paths
    tex_path = output_path / "img.tex"
    png_path = output_path / "img.png"
    json_path = output_path / "img.json"
    original_path = output_path / "original.png"
    
    # Copy original image
    if source_image_path and Path(source_image_path).exists():
        print(f"  Copying original image...", end=" ", flush=True)
        shutil.copy(source_image_path, original_path)
        print(f"done -> {original_path.name}")
    
    # Save TikZ source code
    print(f"  Saving TikZ code...", end=" ", flush=True)
    with open(tex_path, 'w') as f:
        f.write(tikz_code)
    print(f"done -> {tex_path.name}")
    
    # Compile to PNG
    print(f"  Compiling to PNG...", end=" ", flush=True)
    success = compile_tikz_to_png(tikz_code, str(png_path), dpi=dpi)
    
    if not success:
        print("failed")
        # Save failed code for debugging
        failed_path = output_path / "img_failed.tex"
        save_failed_tikz(tikz_code, str(failed_path))
        print(f"  Saved failed code to {failed_path.name}")
        return False
    
    print(f"done -> {png_path.name}")
    
    # Get image dimensions
    width, height = 0, 0
    try:
        from PIL import Image
        with Image.open(png_path) as img:
            width, height = img.size
    except:
        pass
    
    # Build metadata JSON
    metadata = {
        "source_image": source_image_path,
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "image": {
            "width": width,
            "height": height,
            "dpi": dpi,
        },
        "reasoning": reasoning,
        "tikz_code": tikz_code,
    }
    
    # Save metadata JSON
    print(f"  Saving metadata...", end=" ", flush=True)
    with open(json_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"done -> {json_path.name}")
    
    return True


def process_single_image(
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
    Process a single image: generate TikZ code and save all results.
    
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
        
        # Step 2: Save all results (including reasoning)
        return save_results(
            tikz_code=result.tikz_code,
            reasoning=result.reasoning,
            output_dir=output_dir,
            base_dir_name=base_dir_name,
            dpi=dpi,
            model=model,
            source_image_path=image_path,
        )
        
    except Exception as e:
        print(f"error: {e}")
        import traceback
        traceback.print_exc()
        return False

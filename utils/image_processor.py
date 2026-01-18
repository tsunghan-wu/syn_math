"""
Image processing for geometry TikZ generation.

Contains the core logic for processing images and generating TikZ diagrams.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

from .llm_helper import generate_tikz_from_image
from .tikz_helper import (
    compile_tikz_with_coords,
    save_failed_tikz,
    generate_all_masks,
    generate_combination_masks,
    generate_labeled_pdf,
    parse_tikz_elements,
    extract_point_labels
)


def save_results(
    tikz_code: str,
    output_dir: Path,
    base_dir_name: str,
    sample_suffix: str = "",
    dpi: int = 300,
    generate_masks: bool = True
) -> bool:
    """
    Save all results for a generated TikZ diagram.
    
    Creates output structure:
        output_dir/
        └── generated_001/
            ├── png/
            │   └── img_a.png    # Rendered PNG (suffix from sample)
            ├── tikz/
            │   └── img_a.tex    # TikZ source code
            ├── pdf/
            │   └── img_a.pdf    # Labeled PDF with annotations
            └── json/
                └── img_a.json   # COCO format segmentation
    
    Args:
        tikz_code: Generated TikZ code
        output_dir: Root output directory
        base_dir_name: Name for the base output subdirectory (e.g., "generated_001")
        sample_suffix: Suffix for the sample (e.g., "a", "b", "c")
        dpi: Output resolution for PNG
        generate_masks: Whether to generate segmentation masks
    
    Returns:
        True if successful, False otherwise
    """
    # Create base directory and subdirectories
    base_output_dir = output_dir / base_dir_name
    png_dir = base_output_dir / "png"
    tikz_dir = base_output_dir / "tikz"
    pdf_dir = base_output_dir / "pdf"
    json_dir = base_output_dir / "json"
    
    for d in [png_dir, tikz_dir, pdf_dir, json_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Build filename with sample suffix
    file_base = f"img_{sample_suffix}" if sample_suffix else "img"
    
    # Define output paths
    tex_path = tikz_dir / f"{file_base}.tex"
    png_path = png_dir / f"{file_base}.png"
    pdf_path = pdf_dir / f"{file_base}.pdf"
    json_path = json_dir / f"{file_base}.json"
    
    # Save TikZ source code
    print(f"  Saving TikZ code...", end=" ", flush=True)
    with open(tex_path, 'w') as f:
        f.write(tikz_code)
    print(f"done -> tikz/{tex_path.name}")
    
    # Compile to PNG with coordinate extraction
    print(f"  Compiling to PNG...", end=" ", flush=True)
    success, bbox = compile_tikz_with_coords(tikz_code, str(png_path), dpi=dpi)
    
    if not success:
        print("failed")
        # Save failed code for debugging
        failed_path = tikz_dir / f"{file_base}_failed.tex"
        save_failed_tikz(tikz_code, str(failed_path))
        print(f"  Saved failed code to tikz/{failed_path.name}")
        return False
    
    print(f"done -> png/{png_path.name}")
    
    # Parse TikZ elements
    elements = parse_tikz_elements(tikz_code)
    labels = extract_point_labels(tikz_code)
    
    # Build COCO format segmentation data
    coco_data = _build_coco_segmentation(
        tikz_code=tikz_code,
        png_path=png_path,
        bbox=bbox,
        elements=elements,
        labels=labels,
        dpi=dpi,
        generate_masks=generate_masks
    )
    
    # Save COCO segmentation JSON
    print(f"  Saving segmentation data...", end=" ", flush=True)
    with open(json_path, 'w') as f:
        json.dump(coco_data, f, indent=2)
    print(f"done -> json/{json_path.name}")
    
    # Generate labeled PDF
    if generate_masks:
        print(f"  Generating labeled PDF...", end=" ", flush=True)
        combo_masks = generate_combination_masks(tikz_code, str(png_path), dpi=dpi, bbox=bbox)
        result_pdf = generate_labeled_pdf(
            tikz_code, str(png_path), elements, labels, combo_masks,
            pdf_output_path=str(pdf_path)
        )
        if result_pdf:
            print(f"done -> pdf/{pdf_path.name}")
        else:
            print("failed")
    
    return True


def _convert_tuples_to_lists(obj):
    """Recursively convert tuples to lists for JSON serialization."""
    if isinstance(obj, tuple):
        return list(_convert_tuples_to_lists(item) for item in obj)
    elif isinstance(obj, list):
        return [_convert_tuples_to_lists(item) for item in obj]
    elif isinstance(obj, dict):
        return {
            (f"{k[0]},{k[1]}" if isinstance(k, tuple) else k): _convert_tuples_to_lists(v)
            for k, v in obj.items()
        }
    else:
        return obj


def _build_coco_segmentation(
    tikz_code: str,
    png_path: Path,
    bbox: Dict[str, float],
    elements: Dict[str, Any],
    labels: dict,
    dpi: int,
    generate_masks: bool
) -> Dict[str, Any]:
    """
    Build COCO format segmentation data.
    
    COCO format structure:
    {
        "info": {...},
        "images": [{...}],
        "annotations": [{...}],
        "categories": [{...}]
    }
    """
    from PIL import Image
    
    # Get image dimensions
    try:
        with Image.open(png_path) as img:
            width, height = img.size
    except:
        width, height = 0, 0
    
    # Build COCO structure
    coco_data = {
        "info": {
            "description": "Geometry TikZ diagram segmentation",
            "version": "1.0"
        },
        "images": [{
            "id": 1,
            "file_name": png_path.name,
            "width": width,
            "height": height
        }],
        "categories": [
            {"id": 1, "name": "point", "supercategory": "geometry"},
            {"id": 2, "name": "line", "supercategory": "geometry"},
            {"id": 3, "name": "circle", "supercategory": "geometry"},
            {"id": 4, "name": "arc", "supercategory": "geometry"},
        ],
        "annotations": [],
        "metadata": {
            "bbox": bbox,
            "scale": elements.get("scale", 1.0),
            "labels": labels
        }
    }
    
    annotation_id = 1
    
    # Add point annotations
    for point in elements.get("points", []):
        coco_data["annotations"].append({
            "id": annotation_id,
            "image_id": 1,
            "category_id": 1,  # point
            "label": point.get("label", ""),
            "tikz_coords": point.get("coords", []),
            "segmentation": [],  # Points don't have polygon segmentation
            "area": 0,
            "iscrowd": 0
        })
        annotation_id += 1
    
    # Add line annotations
    for line in elements.get("lines", []):
        coco_data["annotations"].append({
            "id": annotation_id,
            "image_id": 1,
            "category_id": 2,  # line
            "endpoints": line.get("endpoints", []),
            "tikz_coords": {
                "start": line.get("start", []),
                "end": line.get("end", [])
            },
            "style": line.get("style", "solid"),
            "segmentation": [],
            "area": 0,
            "iscrowd": 0
        })
        annotation_id += 1
    
    # Add circle annotations
    for circle in elements.get("circles", []):
        coco_data["annotations"].append({
            "id": annotation_id,
            "image_id": 1,
            "category_id": 3,  # circle
            "center": circle.get("center", []),
            "radius": circle.get("radius", 0),
            "segmentation": [],
            "area": 0,
            "iscrowd": 0
        })
        annotation_id += 1
    
    # Add arc annotations
    for arc in elements.get("arcs", []):
        coco_data["annotations"].append({
            "id": annotation_id,
            "image_id": 1,
            "category_id": 4,  # arc
            "center": arc.get("center", []),
            "radius": arc.get("radius", 0),
            "start_angle": arc.get("start_angle", 0),
            "end_angle": arc.get("end_angle", 0),
            "segmentation": [],
            "area": 0,
            "iscrowd": 0
        })
        annotation_id += 1
    
    # Add relationships
    coco_data["relationships"] = elements.get("relationships", {})
    
    # Convert all tuples to lists for JSON serialization
    return _convert_tuples_to_lists(coco_data)


def process_single_image(
    client,
    image_path: str,
    output_dir: Path,
    image_index: int,
    sample_suffix: str = "",
    create_variation: bool = False,
    model: str = "Qwen/Qwen3-VL-235B-A22B-Instruct",
    dpi: int = 300,
    generate_masks: bool = True,
    use_in_context_examples: bool = False
) -> bool:
    """
    Process a single image: generate TikZ code and save all results.
    
    Args:
        client: OpenAI client instance
        image_path: Path to input image
        output_dir: Root output directory
        image_index: Image index for naming (e.g., 1 -> "generated_001")
        sample_suffix: Suffix for this sample (e.g., "a", "b", "c")
        create_variation: Whether to create variation
        model: Model to use for generation
        dpi: Output resolution
        generate_masks: Whether to generate segmentation masks
        use_in_context_examples: Whether to include in-context examples in prompt
    
    Returns:
        True if successful, False otherwise
    """
    base_dir_name = f"generated_{image_index:03d}"
    
    try:
        # Step 1: Generate TikZ code from image
        print(f"  Generating TikZ code...", end=" ", flush=True)
        tikz_code = generate_tikz_from_image(
            client, 
            image_path, 
            create_variation=create_variation, 
            model=model,
            use_in_context_examples=use_in_context_examples
        )
        print("done")
        
        # Step 2: Save all results
        return save_results(
            tikz_code=tikz_code,
            output_dir=output_dir,
            base_dir_name=base_dir_name,
            sample_suffix=sample_suffix,
            dpi=dpi,
            generate_masks=generate_masks
        )
        
    except Exception as e:
        print(f"error: {e}")
        import traceback
        traceback.print_exc()
        return False

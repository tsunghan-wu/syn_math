#!/usr/bin/env python3
"""
Geometry Image to TikZ Generator

Uses OpenAI's vision API to analyze geometry images and generate TikZ code
to recreate similar diagrams, with segmentation masks.

Usage:
    python generate_from_image.py --input image.png --output ./output
    python generate_from_image.py --input-dir ./samples --output ./output --count 10
    
Environment:
    Set OPENAI_API_KEY environment variable or pass via --api-key
"""

import json
import random
from pathlib import Path

# Local imports
from args import parse_args, get_api_key
from llm_helper import generate_tikz_from_image, create_openai_client
from tikz_helper import (
    compile_tikz_with_coords,
    save_tikz_code,
    save_segmentation,
    save_failed_tikz,
    generate_all_masks,
    generate_combination_masks,
    generate_labeled_pdf,
    parse_tikz_elements,
    extract_point_labels
)


def process_single_image(
    client,
    image_path: str,
    output_dir: Path,
    index: int,
    create_variation: bool = False,
    model: str = "Qwen/Qwen3-VL-235B-A22B-Instruct",
    save_tex: bool = False,
    dpi: int = 300,
    generate_masks: bool = True,
    use_in_context_examples: bool = False
) -> bool:
    """
    Process a single image and generate output.
    
    Args:
        client: OpenAI client instance
        image_path: Path to input image
        output_dir: Output directory
        index: Image index for naming
        create_variation: Whether to create variation
        model: OpenAI model to use
        save_tex: Whether to save TikZ source
        dpi: Output resolution
        generate_masks: Whether to generate segmentation masks
        use_in_context_examples: Whether to include in-context TikZ examples in prompt
    
    Returns:
        True if successful, False otherwise
    """
    image_name = Path(image_path).stem
    output_name = f"generated_{index:03d}_{image_name}"
    output_png = output_dir / f"{output_name}.png"
    
    try:
        # Generate TikZ code from image
        print(f"  Analyzing image with OpenAI...", end=" ", flush=True)
        tikz_code = generate_tikz_from_image(
            client, image_path, create_variation=create_variation, model=model,
            use_in_context_examples=use_in_context_examples
        )
        print("done")
        
        # Optionally save TikZ code
        if save_tex:
            tex_path = save_tikz_code(tikz_code, str(output_png))
            print(f"  Saved TikZ code to {Path(tex_path).name}")
        
        # Compile to PNG with coordinate extraction
        print(f"  Compiling to PNG...", end=" ", flush=True)
        success, bbox = compile_tikz_with_coords(tikz_code, str(output_png), dpi=dpi)
        
        if success:
            print(f"done -> {output_png.name}")
            
            # Parse TikZ elements for coordinate data
            elements = parse_tikz_elements(tikz_code)
            
            # Save coordinate/element data with relationships
            coord_data = {
                "bbox": bbox,
                "scale": elements.get("scale", 1.0),
                "elements": {
                    "circles": elements.get("circles", []),
                    "lines": elements.get("lines", []),
                    "points": elements.get("points", []),
                    "arcs": elements.get("arcs", [])
                },
                "relationships": elements.get("relationships", {})
            }
            coord_path = save_segmentation(coord_data, str(output_png))
            print(f"  Saved coordinates to {Path(coord_path).name}")
            
            # Generate segmentation masks from parsed TikZ elements
            if generate_masks:
                print(f"  Generating segmentation masks...", end=" ", flush=True)
                masks = generate_all_masks(tikz_code, str(output_png), dpi=dpi, bbox=bbox)
                if masks:
                    print(f"done ({len(masks)} masks)")
                    for elem_type, mask_path in masks.items():
                        print(f"    - {Path(mask_path).name}")
                else:
                    print("no elements found for masks")
                
                # Generate C(N,2) combination masks
                print(f"  Generating combination masks...", end=" ", flush=True)
                labels = extract_point_labels(tikz_code)
                combo_masks = generate_combination_masks(
                    tikz_code, str(output_png), dpi=dpi, bbox=bbox
                )
                total_combos = (
                    len(combo_masks.get('lines', {})) +
                    len(combo_masks.get('arcs', {})) +
                    len(combo_masks.get('points', {})) +
                    len(combo_masks.get('circles', {}))
                )
                print(f"done ({total_combos} individual masks)")
                print(f"    - {len(combo_masks.get('lines', {}))} line segments")
                print(f"    - {len(combo_masks.get('arcs', {}))} arcs")
                print(f"    - {len(combo_masks.get('points', {}))} points")
                print(f"    - {len(combo_masks.get('circles', {}))} circles")
                
                # Save combination mask metadata
                combo_json_path = str(output_png).replace('.png', '_combinations.json')
                # Convert paths to relative for JSON
                combo_data = {}
                for category, items in combo_masks.items():
                    combo_data[category] = {}
                    for label, data in items.items():
                        combo_data[category][label] = {
                            k: (Path(v).name if k == 'path' else v)
                            for k, v in data.items()
                        }
                with open(combo_json_path, 'w') as f:
                    json.dump(combo_data, f, indent=2)
                print(f"  Saved combination metadata to {Path(combo_json_path).name}")
                
                # Generate labeled PDF
                print(f"  Generating labeled PDF...", end=" ", flush=True)
                pdf_path = generate_labeled_pdf(
                    tikz_code, str(output_png), elements, labels, combo_masks
                )
                if pdf_path:
                    print(f"done -> {Path(pdf_path).name}")
                else:
                    print("failed")
            
            return True
        else:
            print("failed")
            # Save the failed TikZ code for debugging
            failed_tex = output_dir / f"{output_name}_failed.tex"
            save_failed_tikz(tikz_code, str(failed_tex))
            print(f"  Saved failed code to {failed_tex.name}")
            return False
            
    except Exception as e:
        print(f"error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    args = parse_args()
    
    # Get API key
    api_key = get_api_key(args)
    if not api_key:
        print("Error: OpenAI API key required. Set OPENAI_API_KEY or use --api-key")
        return 1
    
    # Initialize OpenAI client
    client = create_openai_client(api_key)
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Collect input images
    if args.input:
        image_paths = [args.input]
    else:
        input_dir = Path(args.input_dir)
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        image_paths = [
            str(p) for p in input_dir.iterdir()
            if p.suffix.lower() in image_extensions
        ]
        image_paths.sort()
        
        if args.count and args.count < len(image_paths):
            # Randomly sample if count specified
            image_paths = random.sample(image_paths, args.count)
    
    if not image_paths:
        print("Error: No images found")
        return 1
    
    print(f"Processing {len(image_paths)} image(s)...")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Mode: {'Variation' if args.variation else 'Recreation'}")
    print(f"Masks: {'Disabled' if args.no_masks else 'Enabled'}")
    print("-" * 50)
    
    success_count = 0
    for i, image_path in enumerate(image_paths):
        print(f"[{i+1}/{len(image_paths)}] Processing {Path(image_path).name}")
        
        if process_single_image(
            client=client,
            image_path=image_path,
            output_dir=output_dir,
            index=i+1,
            create_variation=args.variation,
            model=args.model,
            save_tex=args.save_tex,
            dpi=args.dpi,
            generate_masks=not args.no_masks
        ):
            success_count += 1
    
    print("-" * 50)
    print(f"Successfully generated {success_count}/{len(image_paths)} images")
    
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    exit(main())

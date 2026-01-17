#!/usr/bin/env python3
"""
Run generate_from_image.py on geometry images from classification.

Directly imports and calls generation functions (no subprocess).
"""

import json
import random
from pathlib import Path

# Local imports
from llm_helper import create_openai_client
from generate_from_image import process_single_image

# Configuration
JSONL_FILE = "image_classifications_01102026.jsonl"
IMAGE_ROOT = "/home/annelee/datasets/OpenMMReasoner-SFT-874K/sft_image"
OUTPUT_DIR = "geometry_generated_output_new_in_context_examples"
DEFAULT_COUNT = 50


def load_geometry_images(jsonl_path: str) -> list[str]:
    """Load all geometry image paths from JSONL file."""
    geometry_images = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                if entry.get('sub_category') == 'geometry':
                    geometry_images.append(entry['image_path'])
    return geometry_images


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run geometry image generation")
    parser.add_argument("--count", "-n", type=int, default=DEFAULT_COUNT,
                        help=f"Number of images to process (default: {DEFAULT_COUNT})")
    parser.add_argument("--output", "-o", type=str, default=OUTPUT_DIR,
                        help=f"Output directory (default: {OUTPUT_DIR})")
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-VL-235B-A22B-Instruct",
                        help="OpenAI model to use (default: Qwen/Qwen3-VL-235B-A22B-Instruct)")
    parser.add_argument("--no-save-tex", action="store_true",
                        help="Don't save TikZ source code (default: save tex)")
    parser.add_argument("--no-masks", action="store_true",
                        help="Skip generating segmentation masks")
    parser.add_argument("--variation", action="store_true",
                        help="Generate variations instead of recreations")
    parser.add_argument("--in-context-examples", action="store_true",
                        help="Include in-context TikZ examples in prompt for few-shot learning")
    parser.add_argument("--dpi", type=int, default=300,
                        help="DPI for output images (default: 300)")
    parser.add_argument("--shuffle", action="store_true",
                        help="Randomly shuffle images before selecting")
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    jsonl_path = script_dir / JSONL_FILE
    output_dir = Path(args.output)
    
    # Load geometry images
    print(f"Loading geometry images from: {jsonl_path}")
    geometry_images = load_geometry_images(jsonl_path)
    print(f"Found {len(geometry_images)} geometry images")
    
    # Select images to process
    if args.shuffle:
        random.shuffle(geometry_images)
    
    selected_images = geometry_images[:args.count]
    print(f"Processing {len(selected_images)} images")
    
    # Build full paths
    image_paths = []
    for img_path in selected_images:
        full_path = Path(IMAGE_ROOT) / img_path
        if full_path.exists():
            image_paths.append(str(full_path))
        else:
            print(f"Warning: Image not found: {full_path}")
    
    if not image_paths:
        print("Error: No valid images found")
        return 1
    
    # Initialize OpenAI client
    print("Initializing OpenAI client...")
    # api_key = get_api_key(None)
    # if not api_key:
    #     print("Error: OpenAI API key required. Set OPENAI_API_KEY or update args.py")
    #     return 1
    client = create_openai_client(None)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Mode: {'Variation' if args.variation else 'Recreation'}")
    print(f"Masks: {'Disabled' if args.no_masks else 'Enabled'}")
    print(f"In-context examples: {'Enabled' if args.in_context_examples else 'Disabled'}")
    print("-" * 50)
    
    # Process images
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
            save_tex=not args.no_save_tex,  # Default: save tex
            dpi=args.dpi,
            generate_masks=not args.no_masks,
            use_in_context_examples=args.in_context_examples
        ):
            success_count += 1
    
    print("-" * 50)
    print(f"Successfully generated {success_count}/{len(image_paths)} images")
    
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    exit(main())


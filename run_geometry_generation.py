#!/usr/bin/env python3
"""
Geometry Image to TikZ Generator

Processes geometry images and generates TikZ code using vision LLMs.

Usage:
    python run_geometry_generation.py -n 10 --in-context-examples
    python run_geometry_generation.py --shuffle -n 50
"""

import json
import random
from pathlib import Path

from utils import create_openai_client, process_single_image, parse_args


def load_geometry_images(jsonl_path: str) -> list[str]:
    """Load all geometry image paths from JSONL file."""
    geometry_images = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                if entry.get('sub_category') == 'function_graph':
                    geometry_images.append(entry['image_path'])
    return geometry_images


def main():
    args = parse_args()
    print(args)
    jsonl_path = Path(args.jsonl_file)
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
        full_path = Path(args.input_dir) / img_path
        if full_path.exists():
            image_paths.append(str(full_path))
        else:
            print(f"Warning: Image not found: {full_path}")
    
    if not image_paths:
        print("Error: No valid images found")
        return 1
    
    # Initialize OpenAI client
    print("Initializing LLM/VLM client...")
    client = create_openai_client(backend=args.backend, vllm_url=args.vllm_url)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Mode: {'Variation' if args.variation else 'Recreation'}")
    print(f"In-context examples: {'Enabled (5 random examples)' if args.in_context_examples else 'Disabled'}")
    print("-" * 50)
    
    # Process images
    success_count = 0
    
    for i, image_path in enumerate(image_paths):
        print(f"[{i+1}/{len(image_paths)}] Processing {Path(image_path).name}")
        
        if process_single_image(
            client=client,
            image_path=image_path,
            output_dir=output_dir,
            image_index=i+1,
            create_variation=args.variation,
            model=args.model,
            dpi=args.dpi,
            use_in_context_examples=args.in_context_examples
        ):
            success_count += 1
    
    print("-" * 50)
    print(f"Successfully generated {success_count}/{len(image_paths)} images")
    
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    exit(main())


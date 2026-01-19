#!/usr/bin/env python3
"""
Geometry Image to TikZ Generator

Two-stage processing:
  - Stage 1 (generate): Generate TikZ code and render images
  - Stage 2 (segment): Generate segmentation annotations for existing outputs

Usage:
    # Stage 1: Generate TikZ and render
    python run_geometry_generation.py --mode generate -n 50
    python run_geometry_generation.py -m generate -s 2D_geometry -n 100 --in-context-examples
    
    # Stage 2: Generate segmentation for existing outputs
    python run_geometry_generation.py --mode segment -n 50
    python run_geometry_generation.py -m segment -o geometry_output -n 100
"""

import json
import random
from pathlib import Path

from utils import create_openai_client, process_generate, process_segment, parse_args


def load_programmatic_images(jsonl_path: str, sub_categories: list[str]) -> list[str]:
    """
    Load image paths from JSONL file, filtering by programmatic images.
    
    Args:
        jsonl_path: Path to the JSONL file
        sub_categories: List of sub_class values to include
    
    Returns:
        List of image paths matching the criteria
    """
    images = []
    sub_categories_set = set(sub_categories)
    
    with open(jsonl_path, 'r') as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                # Filter: top_class == "program" AND sub_class in selected categories
                if (entry.get('top_class') == 'program' and 
                    entry.get('sub_class') in sub_categories_set):
                    images.append(entry['image_path'])
    return images


def run_generate_mode(args):
    """Stage 1: Generate TikZ code and render images."""
    jsonl_path = Path(args.jsonl_file)
    output_dir = Path(args.output)
    
    # Load programmatic images with selected sub-categories
    print(f"Loading images from: {jsonl_path}")
    print(f"Sub-categories: {args.sub_category}")
    images = load_programmatic_images(str(jsonl_path), args.sub_category)
    print(f"Found {len(images)} matching images")
    
    # Select images to process
    if args.shuffle:
        random.shuffle(images)
    
    selected_images = images[:args.count]
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
    print(f"Sub-categories: {', '.join(args.sub_category)}")
    print(f"Mode: {'Variation' if args.variation else 'Recreation'}")
    print(f"In-context examples: {'Enabled (5 random examples)' if args.in_context_examples else 'Disabled'}")
    print("-" * 50)
    
    # Process images
    success_count = 0
    
    for i, image_path in enumerate(image_paths):
        print(f"[{i+1}/{len(image_paths)}] Generating {Path(image_path).name}")
        
        if process_generate(
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


def run_segment_mode(args):
    """Stage 2: Generate segmentation for existing outputs."""
    output_dir = Path(args.output)
    
    if not output_dir.exists():
        print(f"Error: Output directory does not exist: {output_dir}")
        return 1
    
    # Find existing generated directories
    generated_dirs = sorted(output_dir.glob("generated_*"))
    if not generated_dirs:
        print(f"Error: No generated_* directories found in {output_dir}")
        return 1
    
    # Limit to count
    generated_dirs = generated_dirs[:args.count]
    print(f"Found {len(generated_dirs)} generated directories to process")
    
    # Initialize OpenAI client
    print("Initializing LLM/VLM client...")
    client = create_openai_client(backend=args.backend, vllm_url=args.vllm_url)
    
    print(f"Output directory: {output_dir.absolute()}")
    print("-" * 50)
    
    # Process each directory
    success_count = 0
    
    for i, gen_dir in enumerate(generated_dirs):
        # Extract index from directory name (e.g., "generated_001" -> 1)
        try:
            index = int(gen_dir.name.split('_')[1])
        except (IndexError, ValueError):
            print(f"[{i+1}/{len(generated_dirs)}] Skipping {gen_dir.name} (invalid name)")
            continue
        
        print(f"[{i+1}/{len(generated_dirs)}] Segmenting {gen_dir.name}")
        
        if process_segment(
            client=client,
            output_dir=output_dir,
            image_index=index,
            model=args.model,
            dpi=args.dpi,
        ):
            success_count += 1
    
    print("-" * 50)
    print(f"Successfully segmented {success_count}/{len(generated_dirs)} outputs")
    
    return 0 if success_count > 0 else 1


def main():
    args = parse_args()
    print(args)
    print(f"\n{'='*50}")
    print(f"MODE: {args.mode.upper()}")
    print(f"{'='*50}\n")
    
    if args.mode == "generate":
        return run_generate_mode(args)
    elif args.mode == "segment":
        return run_segment_mode(args)
    else:
        print(f"Error: Unknown mode '{args.mode}'")
        return 1


if __name__ == "__main__":
    exit(main())


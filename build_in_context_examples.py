#!/usr/bin/env python3
"""
Build in-context examples directory from reasoning traces.

Creates a directory with individual JSON files containing:
- reasoning: step-by-step analysis
- tikz_code: the TikZ code
- image_path: path to the original image

These can be randomly sampled during TikZ generation for few-shot learning.
"""

import json
import shutil
from pathlib import Path

# Configuration
REASONING_TRACES_FILE = "reasoning_vis/reasoning_traces.jsonl"
GENERATED_DIR = "geometry_comparison_viz/generated"
OUTPUT_DIR = "in-context-examples"


def load_reasoning_traces(input_path: str) -> list[dict]:
    """Load reasoning traces from JSONL."""
    traces = []
    with open(input_path, 'r') as f:
        for line in f:
            if line.strip():
                traces.append(json.loads(line))
    return traces


def find_generated_dir(generated_base: Path, index: int) -> Path | None:
    """Find generated directory for given index."""
    prefix = f"generated_{index:03d}_"
    for subdir in generated_base.iterdir():
        if subdir.is_dir() and subdir.name.startswith(prefix):
            return subdir
    return None


def main():
    script_dir = Path(__file__).parent
    traces_path = script_dir / REASONING_TRACES_FILE
    generated_base = script_dir / GENERATED_DIR
    output_dir = script_dir / OUTPUT_DIR
    
    # Load reasoning traces
    print(f"Loading reasoning traces from: {traces_path}")
    traces = load_reasoning_traces(str(traces_path))
    print(f"Found {len(traces)} traces")
    
    if not traces:
        print("No traces found. Run reasoning_generation.py first.")
        return 1
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    # Clear existing files
    for f in output_dir.glob("*.json"):
        f.unlink()
    
    # Process each trace
    saved_count = 0
    for trace in traces:
        index = trace['index']
        image_path = trace['image_path']
        tikz_code = trace['tikz_code']
        reasoning = trace['reasoning']
        
        # Find the generated directory to get the tex file path
        gen_dir = find_generated_dir(generated_base, index)
        
        # Create example entry
        example = {
            "index": index,
            "image_path": image_path,
            "tikz_code": tikz_code,
            "reasoning": reasoning
        }
        
        # Save as individual JSON file
        example_file = output_dir / f"example_{index:03d}.json"
        with open(example_file, 'w') as f:
            json.dump(example, f, indent=2, ensure_ascii=False)
        
        saved_count += 1
        print(f"  Saved: {example_file.name}")
    
    print(f"\nDone! Created {saved_count} in-context examples in {output_dir}")
    print(f"\nThese examples will be randomly sampled during TikZ generation.")
    
    return 0


if __name__ == "__main__":
    exit(main())


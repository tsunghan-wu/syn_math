#!/usr/bin/env python3
"""
Generate HTML comparison of original vs regenerated geometry images.
"""

import json
import os
from pathlib import Path

# Configuration
JSONL_FILE = "image_classifications_01102026.jsonl"
IMAGE_ROOT = "/home/annelee/datasets/OpenMMReasoner-SFT-874K/sft_image"
GENERATED_DIR = "geometry_generated_output"
OUTPUT_DIR = "geometry_comparison_viz"
NUM_COMPARISONS = 20


def load_geometry_images(jsonl_path: str, limit: int) -> list[dict]:
    """Load geometry image entries from JSONL file."""
    geometry_images = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                if entry.get('sub_category') == 'geometry':
                    geometry_images.append(entry)
                    if len(geometry_images) >= limit:
                        break
    return geometry_images


def find_generated_image(generated_dir: Path, original_name: str, index: int) -> str | None:
    """Find the generated image matching the original."""
    # Generated files are named: generated_001_mm_math_instruct_126630.png
    prefix = f"generated_{index:03d}_"
    
    for f in generated_dir.iterdir():
        if f.name.startswith(prefix) and f.name.endswith('.png') and '_mask' not in f.name:
            return f.name
    return None


def generate_html(comparisons: list[dict], output_path: Path):
    """Generate comparison HTML."""
    
    rows = []
    for i, comp in enumerate(comparisons):
        original_path = comp['original_path']
        generated_path = comp.get('generated_path', '')
        original_name = Path(comp['image_path']).name
        
        if generated_path:
            gen_img = f'<img src="{generated_path}" alt="Generated">'
        else:
            gen_img = '<div class="missing">Not generated</div>'
        
        rows.append(f'''
        <tr>
            <td class="index">{i+1}</td>
            <td class="image-cell">
                <img src="{original_path}" alt="Original">
                <div class="caption">{original_name}</div>
            </td>
            <td class="image-cell">
                {gen_img}
            </td>
        </tr>''')
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Geometry Image Comparison: Original vs Generated</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 20px;
            background: #1a1a2e;
            color: #eee;
        }}
        h1 {{
            color: #00d9ff;
            text-align: center;
            margin-bottom: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #16213e;
            border-radius: 10px;
            overflow: hidden;
        }}
        th {{
            background: #0f3460;
            color: #00d9ff;
            padding: 15px;
            text-align: center;
            font-size: 16px;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #0f3460;
            vertical-align: middle;
        }}
        .index {{
            width: 50px;
            text-align: center;
            font-weight: bold;
            color: #00d9ff;
            font-size: 18px;
        }}
        .image-cell {{
            text-align: center;
            width: 45%;
        }}
        .image-cell img {{
            max-width: 400px;
            max-height: 350px;
            object-fit: contain;
            background: white;
            border-radius: 8px;
            padding: 10px;
        }}
        .caption {{
            font-size: 11px;
            color: #888;
            margin-top: 8px;
            word-break: break-all;
        }}
        .missing {{
            color: #ff6b6b;
            padding: 50px;
            border: 2px dashed #ff6b6b;
            border-radius: 8px;
        }}
        tr:hover {{
            background: #1f4068;
        }}
    </style>
</head>
<body>
    <h1>Geometry Image Comparison: Original vs Generated</h1>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Original Image</th>
                <th>Generated (TikZ)</th>
            </tr>
        </thead>
        <tbody>
{''.join(rows)}
        </tbody>
    </table>
</body>
</html>
'''
    
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"Generated: {output_path}")


def main():
    script_dir = Path(__file__).parent
    jsonl_path = script_dir / JSONL_FILE
    generated_dir = script_dir / GENERATED_DIR
    output_dir = script_dir / OUTPUT_DIR
    output_path = output_dir / "index.html"
    
    print(f"Loading first {NUM_COMPARISONS} geometry images...")
    geometry_entries = load_geometry_images(jsonl_path, NUM_COMPARISONS)
    print(f"Loaded {len(geometry_entries)} entries")
    
    # Create symlink to images
    images_link = output_dir / "images"
    output_dir.mkdir(exist_ok=True)
    if not images_link.exists():
        images_link.symlink_to(IMAGE_ROOT)
        print(f"Created symlink: {images_link} -> {IMAGE_ROOT}")
    
    # Create symlink to generated dir
    generated_link = output_dir / "generated"
    if not generated_link.exists():
        generated_link.symlink_to(generated_dir.absolute())
        print(f"Created symlink: {generated_link} -> {generated_dir.absolute()}")
    
    # Build comparison data
    comparisons = []
    for i, entry in enumerate(geometry_entries):
        image_path = entry['image_path']
        original_name = Path(image_path).stem
        
        # Find generated image
        generated_name = find_generated_image(generated_dir, original_name, i + 1)
        
        comp = {
            'image_path': image_path,
            'original_path': f"images/{image_path}",
            'generated_path': f"generated/{generated_name}" if generated_name else None
        }
        comparisons.append(comp)
        
        status = "✓" if generated_name else "✗"
        print(f"  [{i+1:02d}] {status} {Path(image_path).name}")
    
    print(f"\nGenerating HTML...")
    generate_html(comparisons, output_path)
    
    print(f"\nTo view: cd {output_dir} && python -m http.server 8000")
    print("Then open: http://localhost:8000")


if __name__ == "__main__":
    main()


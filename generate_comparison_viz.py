#!/usr/bin/env python3
"""
Generate HTML comparison of original vs regenerated geometry images.

Supports the new output format:
    output_dir/
    └── generated_001_image_name/
        ├── img.tex      # TikZ source code
        ├── img.png      # Rendered PNG
        ├── img.pdf      # Labeled PDF
        └── img.json     # COCO segmentation

Usage:
    python generate_comparison_viz.py
    python generate_comparison_viz.py --generated-dir geometry_generated_output_new_in_context_examples_01172026 -n 50
"""

import argparse
import json
import os
from pathlib import Path

# Default configuration
DEFAULT_JSONL_FILE = "image_classifications_01102026.jsonl"
DEFAULT_IMAGE_ROOT = "/home/annelee/datasets/OpenMMReasoner-SFT-874K/sft_image"
DEFAULT_GENERATED_DIR = "geometry_generated_output_new_in_context_examples_01172026_v2"
DEFAULT_OUTPUT_DIR = "geometry_comparison_viz_v2"
DEFAULT_NUM_COMPARISONS = 100


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate HTML comparison visualization")
    parser.add_argument("--jsonl-file", "-j", type=str, default=DEFAULT_JSONL_FILE,
                        help=f"JSONL file with image classifications (default: {DEFAULT_JSONL_FILE})")
    parser.add_argument("--image-root", "-i", type=str, default=DEFAULT_IMAGE_ROOT,
                        help=f"Root directory for original images (default: {DEFAULT_IMAGE_ROOT})")
    parser.add_argument("--generated-dir", "-g", type=str, default=DEFAULT_GENERATED_DIR,
                        help=f"Directory with generated images (default: {DEFAULT_GENERATED_DIR})")
    parser.add_argument("--output-dir", "-o", type=str, default=DEFAULT_OUTPUT_DIR,
                        help=f"Output directory for visualization (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--count", "-n", type=int, default=DEFAULT_NUM_COMPARISONS,
                        help=f"Number of comparisons (default: {DEFAULT_NUM_COMPARISONS})")
    return parser.parse_args()


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


def find_generated_output(generated_dir: Path, original_name: str, index: int) -> dict | None:
    """
    Find the generated output directory matching the original.
    
    New format: generated_dir/generated_001_image_name/
        - img.png
        - img.pdf
        - img.tex
        - img.json
    
    Returns dict with paths if found, None otherwise.
    """
    prefix = f"generated_{index:03d}_"
    
    # Look for subdirectory matching the pattern
    for subdir in generated_dir.iterdir():
        if subdir.is_dir() and subdir.name.startswith(prefix):
            img_png = subdir / "img.png"
            img_pdf = subdir / "img.pdf"
            img_tex = subdir / "img.tex"
            img_json = subdir / "img.json"
            
            if img_png.exists():
                return {
                    'dir_name': subdir.name,
                    'png': img_png.name if img_png.exists() else None,
                    'pdf': img_pdf.name if img_pdf.exists() else None,
                    'tex': img_tex.name if img_tex.exists() else None,
                    'json': img_json.name if img_json.exists() else None,
                }
    
    # Fallback: check for old format (flat structure)
    for f in generated_dir.iterdir():
        if f.name.startswith(prefix) and f.name.endswith('.png') and '_mask' not in f.name:
            return {
                'dir_name': None,
                'png': f.name,
                'pdf': None,
                'tex': None,
                'json': None,
            }
    
    return None


def generate_html(comparisons: list[dict], output_path: Path):
    """Generate comparison HTML."""
    
    rows = []
    for i, comp in enumerate(comparisons):
        original_path = comp['original_path']
        generated = comp.get('generated')
        original_name = Path(comp['image_path']).name
        
        if generated:
            # New format with subdirectory
            if generated.get('dir_name'):
                png_path = f"generated/{generated['dir_name']}/{generated['png']}"
                pdf_link = ""
                if generated.get('pdf'):
                    pdf_path = f"generated/{generated['dir_name']}/{generated['pdf']}"
                    pdf_link = f'<a href="{pdf_path}" target="_blank" class="pdf-link">📄 PDF</a>'
                
                gen_img = f'''<img src="{png_path}" alt="Generated">
                <div class="links">{pdf_link}</div>'''
            else:
                # Old format (flat)
                gen_img = f'<img src="generated/{generated["png"]}" alt="Generated">'
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
    
    # Count stats
    total = len(comparisons)
    generated_count = sum(1 for c in comparisons if c.get('generated'))
    
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
            margin-bottom: 10px;
        }}
        .stats {{
            text-align: center;
            margin-bottom: 20px;
            color: #888;
        }}
        .stats span {{
            color: #00d9ff;
            font-weight: bold;
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
        .links {{
            margin-top: 8px;
        }}
        .pdf-link {{
            display: inline-block;
            padding: 5px 12px;
            background: #0f3460;
            color: #00d9ff;
            text-decoration: none;
            border-radius: 4px;
            font-size: 12px;
            margin: 2px;
        }}
        .pdf-link:hover {{
            background: #1f4068;
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
    <div class="stats">
        Generated <span>{generated_count}</span> / <span>{total}</span> images
    </div>
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
    args = parse_args()
    
    script_dir = Path(__file__).parent
    jsonl_path = script_dir / args.jsonl_file
    generated_dir = script_dir / args.generated_dir
    output_dir = script_dir / args.output_dir
    output_path = output_dir / "index.html"
    image_root = Path(args.image_root)
    
    print(f"Loading first {args.count} geometry images...")
    geometry_entries = load_geometry_images(jsonl_path, args.count)
    print(f"Loaded {len(geometry_entries)} entries")
    print(f"Generated directory: {generated_dir}")
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Create symlink to original images
    images_link = output_dir / "images"
    if not images_link.exists():
        images_link.symlink_to(image_root)
        print(f"Created symlink: {images_link} -> {image_root}")
    
    # Create symlink to generated dir
    generated_link = output_dir / "generated"
    if generated_link.exists():
        generated_link.unlink()  # Remove old symlink
    generated_link.symlink_to(generated_dir.absolute())
    print(f"Created symlink: {generated_link} -> {generated_dir.absolute()}")
    
    # Build comparison data
    comparisons = []
    generated_count = 0
    for i, entry in enumerate(geometry_entries):
        image_path = entry['image_path']
        original_name = Path(image_path).stem
        
        # Find generated output
        generated = find_generated_output(generated_dir, original_name, i + 1)
        
        comp = {
            'image_path': image_path,
            'original_path': f"images/{image_path}",
            'generated': generated
        }
        comparisons.append(comp)
        
        if generated:
            generated_count += 1
            status = "✓"
            extra = f" [{generated.get('dir_name', generated.get('png'))}]"
        else:
            status = "✗"
            extra = ""
        print(f"  [{i+1:02d}] {status} {Path(image_path).name}{extra}")
    
    print(f"\nGenerated {generated_count}/{len(geometry_entries)} images")
    print(f"Generating HTML...")
    generate_html(comparisons, output_path)
    
    print(f"\nTo view: cd {output_dir} && python -m http.server 8000")
    print("Then open: http://localhost:8000")


if __name__ == "__main__":
    main()

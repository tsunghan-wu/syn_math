#!/usr/bin/env python3
"""
Render TikZ .tex files to PNG images.

Supports two modes:
1. Single file: python render_tikz.py input.tex -o output.png
2. Directory: python render_tikz.py -i ./dirname
   - Looks for dirname/img.tex and renders to dirname/img.png

Usage:
    python render_tikz.py input.tex                     # Render single file
    python render_tikz.py input.tex -o output.png       # Specify output
    python render_tikz.py -i ./generated_001_name       # Render dirname/img.tex -> dirname/img.png
    python render_tikz.py -i ./generated_001_name --dpi 600  # Higher resolution
"""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


LATEX_PREAMBLE = r"""
\documentclass[tikz,border=10pt]{standalone}
\usepackage{xeCJK}
\usepackage{tikz}
\usepackage{tikz-3dplot}
\usepackage{amsmath,amssymb}
\usetikzlibrary{angles,quotes,calc,intersections,through,backgrounds,patterns,decorations.markings,arrows.meta,shapes}
\begin{document}
"""

LATEX_POSTAMBLE = r"""
\end{document}
"""


def is_complete_latex_document(content: str) -> bool:
    """Check if content is a complete LaTeX document or just TikZ code."""
    return '\\documentclass' in content


def render_tikz_to_png(tex_path: str, output_path: str = None, dpi: int = 300) -> bool:
    """
    Render a TikZ .tex file to PNG.
    
    Args:
        tex_path: Path to .tex file (can be just TikZ code or full document)
        output_path: Output PNG path (default: same name with .png extension)
        dpi: Resolution for output image
    
    Returns:
        True if successful, False otherwise
    """
    tex_path = Path(tex_path)
    
    if output_path is None:
        output_path = tex_path.with_suffix('.png')
    else:
        output_path = Path(output_path)
    
    # Read the tex file
    with open(tex_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Wrap in document if it's just TikZ code
    if not is_complete_latex_document(content):
        latex_doc = LATEX_PREAMBLE + content + LATEX_POSTAMBLE
    else:
        latex_doc = content
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_tex = os.path.join(tmpdir, "render.tex")
        tmp_pdf = os.path.join(tmpdir, "render.pdf")
        
        with open(tmp_tex, 'w', encoding='utf-8') as f:
            f.write(latex_doc)
        
        # Compile to PDF using pdflatex (more compatible than xelatex)
        try:
            result = subprocess.run(
                ["xelatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tmp_tex],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if not os.path.exists(tmp_pdf):
                print(f"Error compiling {tex_path.name}:")
                # Show relevant error lines
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'error' in line.lower() or '!' in line:
                            print(f"  {line}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"Error: Compilation timed out for {tex_path.name}")
            return False
        except FileNotFoundError:
            print("Error: pdflatex not found. Please install TeX Live.")
            return False
        
        # Convert PDF to PNG
        png_created = False
        
        # Try pdftoppm first (faster, better quality)
        try:
            subprocess.run(
                ["pdftoppm", "-png", "-r", str(dpi), "-singlefile", tmp_pdf,
                 os.path.join(tmpdir, "output")],
                capture_output=True,
                check=True,
                timeout=30
            )
            tmp_png = os.path.join(tmpdir, "output.png")
            if os.path.exists(tmp_png):
                shutil.copy(tmp_png, output_path)
                png_created = True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Try ImageMagick convert as fallback
        if not png_created:
            try:
                subprocess.run(
                    ["convert", "-density", str(dpi), tmp_pdf, "-quality", "100", str(output_path)],
                    capture_output=True,
                    check=True,
                    timeout=30
                )
                png_created = os.path.exists(output_path)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        if not png_created:
            print(f"Error: Could not convert PDF to PNG for {tex_path.name}")
            return False
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Render TikZ .tex files to PNG images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python render_tikz.py diagram.tex                     # Render single file
  python render_tikz.py diagram.tex -o output.png       # Specify output path
  python render_tikz.py -i ./generated_001_name         # Render dirname/img.tex -> dirname/img.png
  python render_tikz.py -i ./generated_001_name --dpi 600  # Higher resolution
        """
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "input_file",
        nargs="?",
        type=str,
        help="Path to a single .tex file to render"
    )
    input_group.add_argument(
        "--input-dir", "-i",
        type=str,
        help="Directory containing img.tex to render"
    )
    
    # Output options
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output path (for single file mode only)"
    )
    
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for output images (default: 300)"
    )
    
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing PNG files"
    )
    
    args = parser.parse_args()
    
    if args.input_file:
        # Single file mode
        input_path = Path(args.input_file)
        
        if not input_path.exists():
            print(f"Error: File not found: {input_path}")
            return 1
        
        output_path = args.output
        
        print(f"Rendering {input_path.name}...", end=" ", flush=True)
        if render_tikz_to_png(str(input_path), output_path, dpi=args.dpi):
            out_name = output_path if output_path else input_path.with_suffix('.png')
            print(f"done -> {out_name}")
            return 0
        else:
            print("failed")
            return 1
    
    else:
        # Directory mode - look for img.tex in the given directory
        input_dir = Path(args.input_dir)
        
        if not input_dir.exists():
            print(f"Error: Directory not found: {input_dir}")
            return 1
        
        tex_file = input_dir / "img.tex"
        output_path = input_dir / "img.png"
        
        if not tex_file.exists():
            print(f"Error: {tex_file} not found")
            return 1
        
        # Skip if already exists and not overwriting
        if output_path.exists() and not args.overwrite:
            print(f"Skipping {input_dir.name} (img.png already exists, use --overwrite)")
            return 0
        
        print(f"Rendering {input_dir.name}/img.tex...", end=" ", flush=True)
        
        if render_tikz_to_png(str(tex_file), str(output_path), dpi=args.dpi):
            print(f"done -> img.png")
            return 0
        else:
            print("failed")
            return 1


if __name__ == "__main__":
    exit(main())

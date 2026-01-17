"""
TikZ helper functions for compilation, parsing, and mask generation.
"""

import os
import re
import json
import subprocess
import tempfile
import shutil
import math
from pathlib import Path
from itertools import combinations
from PIL import Image, ImageDraw, ImageFont


# =============================================================================
# LaTeX Document Templates
# =============================================================================

LATEX_PREAMBLE = r"""
\documentclass[tikz,border=10pt]{standalone}
\usepackage{tikz}
\usepackage{amsmath,amssymb}
\usetikzlibrary{angles,quotes,calc,intersections,through,backgrounds,patterns,decorations.markings,arrows.meta,shapes}
\begin{document}
"""

LATEX_POSTAMBLE = r"""
\end{document}
"""

# Preamble with coordinate export enabled
LATEX_PREAMBLE_WITH_COORDS = r"""
\documentclass[tikz,border=10pt]{standalone}
\usepackage{tikz}
\usepackage{amsmath,amssymb}
\usetikzlibrary{angles,quotes,calc,intersections,through,backgrounds,patterns,decorations.markings,arrows.meta,shapes}

% Open coordinate output file
\newwrite\coordfile
\immediate\openout\coordfile=\jobname.coords

% Write bounding box at end of document
\makeatletter
\AtEndDocument{%
  \immediate\write\coordfile{BBOX:\strip@pt\pgf@picminx:\strip@pt\pgf@picminy:\strip@pt\pgf@picmaxx:\strip@pt\pgf@picmaxy}%
  \immediate\closeout\coordfile
}
\makeatother

\begin{document}
"""


# =============================================================================
# TikZ Compilation
# =============================================================================

def compile_tikz_to_png(tikz_code: str, output_path: str, dpi: int = 300) -> bool:
    """Compile TikZ code to PNG image."""
    latex_doc = LATEX_PREAMBLE + tikz_code + LATEX_POSTAMBLE
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = os.path.join(tmpdir, "geometry.tex")
        pdf_file = os.path.join(tmpdir, "geometry.pdf")
        
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_doc)
        
        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_file],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if not os.path.exists(pdf_file):
                print(f"Error: PDF not created")
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'error' in line.lower() or '!' in line:
                            print(f"  {line}")
                return False
                
        except subprocess.TimeoutExpired:
            print("Error: LaTeX compilation timed out")
            return False
        except FileNotFoundError:
            print("Error: pdflatex not found. Please install TeX Live.")
            return False
        
        # Convert PDF to PNG
        png_created = False
        
        # Try pdftoppm first
        try:
            subprocess.run(
                ["pdftoppm", "-png", "-r", str(dpi), "-singlefile", pdf_file,
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
        
        # Try ImageMagick convert
        if not png_created:
            try:
                subprocess.run(
                    ["convert", "-density", str(dpi), pdf_file, "-quality", "100", output_path],
                    capture_output=True,
                    check=True,
                    timeout=30
                )
                png_created = os.path.exists(output_path)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        if not png_created:
            print("Error: Could not convert PDF to PNG.")
            return False
        
        return True


def compile_tikz_with_coords(tikz_code: str, output_path: str, dpi: int = 300) -> tuple:
    """
    Compile TikZ code to PNG and extract bounding box coordinates.
    
    Returns:
        Tuple of (success: bool, bbox: dict or None)
        bbox contains: {'min_x', 'min_y', 'max_x', 'max_y'} in pt units
    """
    latex_doc = LATEX_PREAMBLE_WITH_COORDS + tikz_code + LATEX_POSTAMBLE
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = os.path.join(tmpdir, "geometry.tex")
        pdf_file = os.path.join(tmpdir, "geometry.pdf")
        coords_file = os.path.join(tmpdir, "geometry.coords")
        
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_doc)
        
        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_file],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if not os.path.exists(pdf_file):
                print(f"Error: PDF not created")
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'error' in line.lower() or '!' in line:
                            print(f"  {line}")
                return False, None
                
        except subprocess.TimeoutExpired:
            print("Error: LaTeX compilation timed out")
            return False, None
        except FileNotFoundError:
            print("Error: pdflatex not found. Please install TeX Live.")
            return False, None
        
        # Parse bounding box from coords file
        bbox = None
        if os.path.exists(coords_file):
            with open(coords_file, 'r') as f:
                for line in f:
                    if line.startswith('BBOX:'):
                        # Format: BBOX:minx:miny:maxx:maxy (values in pt, already stripped)
                        parts = line[5:].strip().split(':')
                        if len(parts) == 4:
                            try:
                                bbox = {
                                    'min_x': float(parts[0]),
                                    'min_y': float(parts[1]),
                                    'max_x': float(parts[2]),
                                    'max_y': float(parts[3])
                                }
                            except ValueError:
                                # If parsing fails, continue without bbox
                                pass
        
        # Convert PDF to PNG
        png_created = False
        
        try:
            subprocess.run(
                ["pdftoppm", "-png", "-r", str(dpi), "-singlefile", pdf_file,
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
        
        if not png_created:
            try:
                subprocess.run(
                    ["convert", "-density", str(dpi), pdf_file, "-quality", "100", output_path],
                    capture_output=True,
                    check=True,
                    timeout=30
                )
                png_created = os.path.exists(output_path)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        if not png_created:
            print("Error: Could not convert PDF to PNG.")
            return False, None
        
        return True, bbox


# =============================================================================
# File I/O Helpers
# =============================================================================

def save_tikz_code(tikz_code: str, output_path: str) -> str:
    """Save TikZ code to a .tex file."""
    tex_path = output_path.replace('.png', '.tex')
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(tikz_code)
    return tex_path


def save_segmentation(segmentation: dict, output_path: str) -> str:
    """Save segmentation/coordinate data to a JSON file."""
    json_path = output_path.replace('.png', '_coords.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(segmentation, f, indent=2)
    return json_path


def save_failed_tikz(tikz_code: str, output_path: str) -> str:
    """Save failed TikZ code for debugging."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(LATEX_PREAMBLE + tikz_code + LATEX_POSTAMBLE)
    return output_path


# =============================================================================
# TikZ Parsing - Extract Elements and Coordinates
# =============================================================================

def parse_tikz_scale(tikz_code: str) -> float:
    """Extract scale factor from tikzpicture options."""
    match = re.search(r'\\begin\{tikzpicture\}\s*\[\s*[^\]]*scale\s*=\s*([\d.]+)', tikz_code)
    if match:
        return float(match.group(1))
    return 1.0


def parse_coordinate(coord_str: str, named_coords: dict = None) -> tuple:
    """
    Parse a TikZ coordinate string to (x, y) tuple.
    
    Handles:
    - Numeric: (1.5, -2.3)
    - Named: (A), (center)
    - Relative: ++(1,0), +(0,1)
    - Calculations: ($(A)!0.5!(B)$) - returns None for complex cases
    """
    coord_str = coord_str.strip()
    
    # Handle named coordinates
    if named_coords and coord_str in named_coords:
        return named_coords[coord_str]
    
    # Try numeric coordinate
    numeric_match = re.match(r'^([-\d.]+)\s*,\s*([-\d.]+)$', coord_str)
    if numeric_match:
        return (float(numeric_match.group(1)), float(numeric_match.group(2)))
    
    # Can't parse complex coordinates
    return None


def extract_latex_macros(tikz_code: str) -> dict:
    """Extract \def and \newcommand macro definitions from TikZ code."""
    macros = {}
    
    # Pattern: \def\name{value}
    def_pattern = r'\\def\\([a-zA-Z]+)\{([^}]+)\}'
    for match in re.finditer(def_pattern, tikz_code):
        name = match.group(1).strip()
        value = match.group(2).strip()
        macros[name] = value
    
    # Pattern: \newcommand{\name}{value}
    newcmd_pattern = r'\\newcommand\{\\([a-zA-Z]+)\}\{([^}]+)\}'
    for match in re.finditer(newcmd_pattern, tikz_code):
        name = match.group(1).strip()
        value = match.group(2).strip()
        macros[name] = value
    
    return macros


def resolve_macro(value_str: str, macros: dict) -> str:
    """Resolve a value that might be a LaTeX macro like \r to its actual value."""
    value_str = value_str.strip()
    
    # Check if it's a macro reference like \r or \radius
    if value_str.startswith('\\'):
        macro_name = value_str[1:]  # Remove the backslash
        if macro_name in macros:
            return macros[macro_name]
    
    return value_str


def extract_named_coordinates(tikz_code: str) -> dict:
    """Extract named coordinate definitions from TikZ code."""
    named = {}
    
    # Pattern: \coordinate (name) at (x, y);
    coord_pattern = r'\\coordinate\s*\(([^)]+)\)\s*at\s*\(([^)]+)\)\s*;'
    for match in re.finditer(coord_pattern, tikz_code):
        name = match.group(1).strip()
        coord = parse_coordinate(match.group(2).strip())
        if coord:
            named[name] = coord
    
    # Pattern: \coordinate [options] (name) at (x, y);
    coord_pattern2 = r'\\coordinate\s*\[[^\]]*\]\s*\(([^)]+)\)\s*at\s*\(([^)]+)\)\s*;'
    for match in re.finditer(coord_pattern2, tikz_code):
        name = match.group(1).strip()
        coord = parse_coordinate(match.group(2).strip())
        if coord:
            named[name] = coord
    
    # Pattern: \node (name) at (x, y) {...};
    node_pattern = r'\\node\s*\(([^)]+)\)\s*at\s*\(([^)]+)\)'
    for match in re.finditer(node_pattern, tikz_code):
        name = match.group(1).strip()
        coord = parse_coordinate(match.group(2).strip())
        if coord:
            named[name] = coord
    
    # Pattern: \node[...] (name) at (x, y) {...};
    node_pattern2 = r'\\node\s*\[[^\]]*\]\s*\(([^)]+)\)\s*at\s*\(([^)]+)\)'
    for match in re.finditer(node_pattern2, tikz_code):
        name = match.group(1).strip()
        coord = parse_coordinate(match.group(2).strip())
        if coord:
            named[name] = coord
    
    return named


def extract_point_labels(tikz_code: str) -> dict:
    """
    Extract point labels from TikZ code.
    
    Looks for patterns like:
    - \fill (x,y) circle (r) node[...] {$A$};
    - \node at (x,y) {$A$};
    - \node[...] at (x,y) {$A$};
    - \coordinate (A) at (x,y);
    
    Returns:
        Dict mapping (x, y) tuples to label strings
    """
    labels = {}
    
    # Pattern 1: \fill (x,y) circle ... node[...] {$label$}
    pattern1 = r'\\fill[^;]*\(([^)]+)\)\s*circle[^;]*node[^{]*\{\$?([A-Za-z0-9]+)\$?\}'
    for match in re.finditer(pattern1, tikz_code):
        coord_str = match.group(1).strip()
        label = match.group(2).strip()
        coord_match = re.match(r'^([-\d.]+)\s*,\s*([-\d.]+)$', coord_str)
        if coord_match:
            coord = (float(coord_match.group(1)), float(coord_match.group(2)))
            labels[coord] = label
    
    # Pattern 2: \filldraw (x,y) circle ... node[...] {$label$}
    pattern2 = r'\\filldraw[^;]*\(([^)]+)\)\s*circle[^;]*node[^{]*\{\$?([A-Za-z0-9]+)\$?\}'
    for match in re.finditer(pattern2, tikz_code):
        coord_str = match.group(1).strip()
        label = match.group(2).strip()
        coord_match = re.match(r'^([-\d.]+)\s*,\s*([-\d.]+)$', coord_str)
        if coord_match:
            coord = (float(coord_match.group(1)), float(coord_match.group(2)))
            labels[coord] = label
    
    # Pattern 3: \coordinate (label) at (x,y)
    pattern3 = r'\\coordinate\s*\(([^)]+)\)\s*at\s*\(([^)]+)\)'
    for match in re.finditer(pattern3, tikz_code):
        label = match.group(1).strip()
        coord_str = match.group(2).strip()
        coord_match = re.match(r'^([-\d.]+)\s*,\s*([-\d.]+)$', coord_str)
        if coord_match:
            coord = (float(coord_match.group(1)), float(coord_match.group(2)))
            labels[coord] = label
    
    # Pattern 4: \node at (x,y) {$label$} or \node[...] at (x,y) {$label$}
    # These are standalone labels that need to be matched to nearby points
    pattern4 = r'\\node(?:\s*\[[^\]]*\])?\s*at\s*\(([^)]+)\)\s*\{\$?([A-Za-z])\$?\}'
    standalone_labels = []
    for match in re.finditer(pattern4, tikz_code):
        coord_str = match.group(1).strip()
        label = match.group(2).strip()
        coord_match = re.match(r'^([-\d.]+)\s*,\s*([-\d.]+)$', coord_str)
        if coord_match:
            coord = (float(coord_match.group(1)), float(coord_match.group(2)))
            standalone_labels.append((coord, label))
    
    # Pattern 5: Extract \fill points without labels for matching
    fill_points = []
    pattern5 = r'\\fill[^;]*\(([^)]+)\)\s*circle'
    for match in re.finditer(pattern5, tikz_code):
        coord_str = match.group(1).strip()
        coord_match = re.match(r'^([-\d.]+)\s*,\s*([-\d.]+)$', coord_str)
        if coord_match:
            coord = (float(coord_match.group(1)), float(coord_match.group(2)))
            if coord not in labels:  # Only if not already labeled
                fill_points.append(coord)
    
    # Match standalone labels to nearby fill points
    label_match_tolerance = 0.5  # Label within 0.5 units of point
    for label_coord, label in standalone_labels:
        best_point = None
        best_dist = float('inf')
        for point in fill_points:
            dist = math.sqrt((point[0] - label_coord[0])**2 + (point[1] - label_coord[1])**2)
            if dist < best_dist and dist < label_match_tolerance:
                best_dist = dist
                best_point = point
        if best_point:
            labels[best_point] = label
            fill_points.remove(best_point)  # Remove matched point
    
    return labels


def get_point_label(point_pos: tuple, labels: dict, tolerance: float = 0.01) -> str:
    """Get label for a point position, with tolerance for floating point comparison."""
    for coord, label in labels.items():
        if abs(coord[0] - point_pos[0]) < tolerance and abs(coord[1] - point_pos[1]) < tolerance:
            return label
    return None


def generate_derived_arcs(elements: dict, labels: dict) -> list:
    """
    Generate arcs from pairs of points that lie on the same circle.
    
    For each pair of points on a circle, generates two arcs:
    - Inner arc (shorter path)
    - Outer arc (longer path)
    
    Returns:
        List of arc dictionaries with labels
    """
    derived_arcs = []
    relationships = elements.get("relationships", {})
    points_on_circles = relationships.get("points_on_circles", [])
    circles = elements.get("circles", [])
    points = elements.get("points", [])
    
    # Group points by circle
    circle_points = {}  # circle_idx -> list of (point_idx, point_pos)
    for poc in points_on_circles:
        ci = poc["circle_idx"]
        pi = poc["point_idx"]
        if ci not in circle_points:
            circle_points[ci] = []
        circle_points[ci].append((pi, poc["point_pos"]))
    
    # For each circle, generate arcs between all pairs of points
    for ci, pts in circle_points.items():
        if len(pts) < 2:
            continue
        
        circle = circles[ci]
        center = circle["center"]
        radius = circle["radius"]
        
        # Get center label
        center_label = get_point_label(tuple(center), labels)
        
        # Generate all pairs (no self-arcs - must be different points)
        for (pi1, pos1), (pi2, pos2) in combinations(pts, 2):
            # Skip if same point index (safety check)
            if pi1 == pi2:
                continue
            
            # Get labels for points
            label1 = get_point_label(tuple(pos1), labels) or f"P{pi1}"
            label2 = get_point_label(tuple(pos2), labels) or f"P{pi2}"
            
            # Skip if same label (no Arc_AA)
            if label1 == label2:
                continue
            
            # Calculate angles from center to each point
            angle1 = math.degrees(math.atan2(pos1[1] - center[1], pos1[0] - center[0]))
            angle2 = math.degrees(math.atan2(pos2[1] - center[1], pos2[0] - center[0]))
            
            # Normalize angles to [0, 360)
            angle1 = angle1 % 360
            angle2 = angle2 % 360
            
            # Determine inner and outer arcs
            # Inner arc: shorter path
            # Outer arc: longer path (goes the other way around)
            
            if angle1 > angle2:
                angle1, angle2 = angle2, angle1
                label1, label2 = label2, label1
            
            inner_span = angle2 - angle1
            outer_span = 360 - inner_span
            
            # Inner arc (shorter)
            if inner_span <= 180:
                inner_start, inner_end = angle1, angle2
                outer_start, outer_end = angle2, angle1 + 360
            else:
                inner_start, inner_end = angle2, angle1 + 360
                outer_start, outer_end = angle1, angle2
                inner_span, outer_span = outer_span, inner_span
            
            # Add inner arc
            derived_arcs.append({
                "center": center,
                "radius": radius,
                "start_angle": inner_start,
                "end_angle": inner_end,
                "arc_type": "inner",
                "point1_label": label1,
                "point2_label": label2,
                "circle_center_label": center_label,
                "label": f"Arc_{label1}{label2}_inner"
            })
            
            # Add outer arc
            derived_arcs.append({
                "center": center,
                "radius": radius,
                "start_angle": outer_start,
                "end_angle": outer_end,
                "arc_type": "outer",
                "point1_label": label1,
                "point2_label": label2,
                "circle_center_label": center_label,
                "label": f"Arc_{label1}{label2}_outer"
            })
    
    return derived_arcs


def generate_all_line_combinations(elements: dict, labels: dict) -> list:
    """
    Generate all C(N,2) line segment combinations between points.
    
    Returns:
        List of line segment dictionaries with labels
    """
    all_lines = []
    points = elements.get("points", [])
    
    # Generate all pairs
    for (i, p1), (j, p2) in combinations(enumerate(points), 2):
        pos1 = p1["position"]
        pos2 = p2["position"]
        
        label1 = get_point_label(tuple(pos1), labels) or f"P{i}"
        label2 = get_point_label(tuple(pos2), labels) or f"P{j}"
        
        all_lines.append({
            "start": pos1,
            "end": pos2,
            "point1_idx": i,
            "point2_idx": j,
            "point1_label": label1,
            "point2_label": label2,
            "label": f"Line_{label1}{label2}"
        })
    
    return all_lines


def split_lines_at_labeled_points(elements: dict, labels: dict) -> list:
    """
    Split line segments at labeled points that lie on them.
    
    For example, if M is on line AB, this generates:
    - Line AM (from A to M)
    - Line BM (from B to M)
    
    Returns:
        List of additional line segment dictionaries
    """
    additional_lines = []
    lines = elements.get("lines", [])
    relationships = elements.get("relationships", {})
    points_on_lines = relationships.get("points_on_lines", [])
    
    # Group points by line
    line_points = {}  # line_idx -> list of (point_idx, point_pos, t_param)
    for pol in points_on_lines:
        li = pol["line_idx"]
        pi = pol["point_idx"]
        t = pol["parameter_t"]
        pos = pol["point_pos"]
        position_type = pol["position_on_line"]
        
        # Skip endpoints (t=0 or t=1) - we only want interior points
        if position_type == "middle" and 0.01 < t < 0.99:
            if li not in line_points:
                line_points[li] = []
            line_points[li].append((pi, pos, t))
    
    # For each line with interior points, create sub-segments
    for li, interior_points in line_points.items():
        if li >= len(lines):
            continue
            
        line = lines[li]
        start = line["start"]
        end = line["end"]
        
        # Get labels for line endpoints
        start_label = get_point_label(tuple(start), labels)
        end_label = get_point_label(tuple(end), labels)
        
        # Skip if endpoints don't have labels
        if not start_label or not end_label:
            continue
        
        # For each interior point, create segments to both endpoints
        for pi, pos, t in interior_points:
            point_label = get_point_label(tuple(pos), labels)
            
            # Skip if point doesn't have a label
            if not point_label:
                continue
            
            # Skip if same label as an endpoint
            if point_label == start_label or point_label == end_label:
                continue
            
            # Create segment from start to this point
            additional_lines.append({
                "start": start,
                "end": pos,
                "point1_label": start_label,
                "point2_label": point_label,
                "label": f"Line_{start_label}{point_label}",
                "derived_from": f"Line_{start_label}{end_label}"
            })
            
            # Create segment from this point to end
            additional_lines.append({
                "start": pos,
                "end": end,
                "point1_label": point_label,
                "point2_label": end_label,
                "label": f"Line_{point_label}{end_label}",
                "derived_from": f"Line_{start_label}{end_label}"
            })
    
    return additional_lines


def compute_geometric_relationships(elements: dict, tolerance: float = 0.15) -> dict:
    """
    Compute geometric relationships between elements.
    
    Detects:
    - Points on circles
    - Points on line segments
    
    Args:
        elements: Dict with circles, lines, points
        tolerance: Relative tolerance for distance comparisons (default 15% to account for LLM coordinate imprecision)
    
    Returns:
        Dict with relationships
    """
    relationships = {
        "points_on_circles": [],  # [(point_idx, circle_idx), ...]
        "points_on_lines": [],    # [(point_idx, line_idx), ...]
    }
    
    points = elements.get('points', [])
    circles = elements.get('circles', [])
    lines = elements.get('lines', [])
    
    # Check points on circles
    for pi, point in enumerate(points):
        pos = point['position']
        for ci, circle in enumerate(circles):
            center = circle['center']
            radius = circle['radius']
            
            # Distance from point to circle center
            dist = math.sqrt((pos[0] - center[0])**2 + (pos[1] - center[1])**2)
            
            # Check if point is on circle (within tolerance)
            if abs(dist - radius) < radius * tolerance:
                relationships["points_on_circles"].append({
                    "point_idx": pi,
                    "circle_idx": ci,
                    "point_pos": pos,
                    "circle_center": center,
                    "distance_to_center": dist,
                    "circle_radius": radius
                })
    
    # Check points on lines
    for pi, point in enumerate(points):
        pos = point['position']
        for li, line in enumerate(lines):
            start = line['start']
            end = line['end']
            
            # Vector from start to end
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            line_len = math.sqrt(dx**2 + dy**2)
            
            if line_len < 1e-6:
                continue
            
            # Vector from start to point
            px = pos[0] - start[0]
            py = pos[1] - start[1]
            
            # Project point onto line
            t = (px * dx + py * dy) / (line_len ** 2)
            
            # Closest point on line segment
            t_clamped = max(0, min(1, t))
            closest_x = start[0] + t_clamped * dx
            closest_y = start[1] + t_clamped * dy
            
            # Distance from point to closest point on line
            dist = math.sqrt((pos[0] - closest_x)**2 + (pos[1] - closest_y)**2)
            
            # Check if point is on line (within tolerance relative to line length)
            if dist < line_len * tolerance:
                # Determine if point is at start, end, or middle
                if t < tolerance:
                    position_on_line = "start"
                elif t > 1 - tolerance:
                    position_on_line = "end"
                else:
                    position_on_line = "middle"
                
                relationships["points_on_lines"].append({
                    "point_idx": pi,
                    "line_idx": li,
                    "point_pos": pos,
                    "line_start": start,
                    "line_end": end,
                    "position_on_line": position_on_line,
                    "parameter_t": t
                })
    
    return relationships


def parse_tikz_elements(tikz_code: str) -> dict:
    """
    Parse TikZ code to extract all drawing elements with their coordinates.
    
    Returns dict with element types and their coordinate data.
    """
    elements = {
        "circles": [],
        "lines": [],
        "points": [],
        "arcs": [],
        "scale": parse_tikz_scale(tikz_code)
    }
    
    # Extract named coordinates and macros first
    named_coords = extract_named_coordinates(tikz_code)
    macros = extract_latex_macros(tikz_code)
    
    # Helper to resolve coordinate
    def resolve_coord(coord_str):
        coord = parse_coordinate(coord_str, named_coords)
        if coord:
            return coord
        # Try to look up named coordinate
        if coord_str in named_coords:
            return named_coords[coord_str]
        return None
    
    # Helper to parse radius (handles macros, units)
    def parse_radius(radius_str):
        # First resolve any macros like \r
        radius_str = resolve_macro(radius_str, macros)
        
        # Parse radius (handle units like cm, pt)
        radius_match = re.match(r'^([\d.]+)\s*(cm|pt|mm)?$', radius_str)
        if radius_match:
            radius = float(radius_match.group(1))
            unit = radius_match.group(2) or ''
            # Convert to cm (TikZ default unit)
            if unit == 'pt':
                radius = radius / 28.45  # 1cm = 28.45pt
            elif unit == 'mm':
                radius = radius / 10
            return radius
        else:
            try:
                return float(radius_str)
            except ValueError:
                return 1.0
    
    # Extract circles: \draw ... (center) circle (radius)
    circle_pattern = r'\\draw[^;]*\(([^)]+)\)\s*circle\s*\(([^)]+)\)'
    for match in re.finditer(circle_pattern, tikz_code):
        center_str = match.group(1).strip()
        radius_str = match.group(2).strip()
        
        center = resolve_coord(center_str)
        radius = parse_radius(radius_str)
        
        if center:
            elements["circles"].append({
                "center": center,
                "radius": radius
            })
    
    # Extract line segments - split by statements first
    statements = tikz_code.split(';')
    for stmt in statements:
        if '\\draw' in stmt and '--' in stmt and 'circle' not in stmt.lower():
            # Extract all points in this draw command
            points = re.findall(r'\(([^)]+)\)', stmt)
            resolved_points = []
            for p in points:
                # Skip options and node content
                if '=' in p or p.startswith('[') or 'node' in p.lower():
                    continue
                coord = resolve_coord(p)
                if coord:
                    resolved_points.append(coord)
            
            # Create line segments between consecutive points
            for i in range(len(resolved_points) - 1):
                # Check for cycle (closed path)
                elements["lines"].append({
                    "start": resolved_points[i],
                    "end": resolved_points[i + 1]
                })
            
            # Handle cycle (closed path)
            if 'cycle' in stmt.lower() and len(resolved_points) >= 3:
                elements["lines"].append({
                    "start": resolved_points[-1],
                    "end": resolved_points[0]
                })
    
    # Extract filled points: \fill ... (point) circle (size)
    point_pattern = r'\\fill[^;]*\(([^)]+)\)\s*circle\s*\(([^)]+)\)'
    for match in re.finditer(point_pattern, tikz_code):
        pos_str = match.group(1).strip()
        size_str = match.group(2).strip()
        
        pos = resolve_coord(pos_str)
        
        # Parse size
        size_match = re.match(r'^([\d.]+)\s*(pt|cm|mm)?$', size_str)
        if size_match:
            size = float(size_match.group(1))
            unit = size_match.group(2) or 'pt'
            if unit == 'cm':
                size = size * 28.45
            elif unit == 'mm':
                size = size * 2.845
        else:
            size = 2.0  # default point size in pt
        
        if pos:
            elements["points"].append({
                "position": pos,
                "size": size  # in pt
            })
    
    # Also check for \filldraw points
    filldraw_point_pattern = r'\\filldraw[^;]*\(([^)]+)\)\s*circle\s*\(([^)]+)\)'
    for match in re.finditer(filldraw_point_pattern, tikz_code):
        pos_str = match.group(1).strip()
        size_str = match.group(2).strip()
        
        pos = resolve_coord(pos_str)
        
        size_match = re.match(r'^([\d.]+)\s*(pt|cm|mm)?$', size_str)
        if size_match:
            size = float(size_match.group(1))
            unit = size_match.group(2) or 'pt'
            if unit == 'cm':
                size = size * 28.45
            elif unit == 'mm':
                size = size * 2.845
        else:
            size = 2.0
        
        if pos:
            elements["points"].append({
                "position": pos,
                "size": size
            })
    
    # Extract arcs: arc (start_angle:end_angle:radius)
    arc_pattern = r'\(([^)]+)\)\s*arc\s*\((\d+):(\d+):([^)]+)\)'
    for match in re.finditer(arc_pattern, tikz_code):
        start_pos_str = match.group(1).strip()
        start_angle = float(match.group(2))
        end_angle = float(match.group(3))
        radius_str = match.group(4).strip()
        
        start_pos = resolve_coord(start_pos_str)
        
        radius_match = re.match(r'^([\d.]+)\s*(cm|pt|mm)?$', radius_str)
        if radius_match:
            radius = float(radius_match.group(1))
            unit = radius_match.group(2) or ''
            if unit == 'pt':
                radius = radius / 28.45
            elif unit == 'mm':
                radius = radius / 10
        else:
            try:
                radius = float(radius_str)
            except ValueError:
                radius = 0.5
        
        if start_pos:
            # Calculate center from start position and start angle
            # Arc starts at start_pos, so center is at start_pos - radius*(cos(start_angle), sin(start_angle))
            start_rad = math.radians(start_angle)
            center_x = start_pos[0] - radius * math.cos(start_rad)
            center_y = start_pos[1] - radius * math.sin(start_rad)
            
            elements["arcs"].append({
                "center": (center_x, center_y),
                "radius": radius,
                "start_angle": start_angle,
                "end_angle": end_angle
            })
    
    # Arc with options: arc[start angle=X, end angle=Y, radius=Z]
    arc_options_pattern = r'\(([^)]+)\)\s*arc\s*\[([^\]]+)\]'
    for match in re.finditer(arc_options_pattern, tikz_code):
        start_pos_str = match.group(1).strip()
        options = match.group(2)
        
        start_pos = resolve_coord(start_pos_str)
        
        # Parse options
        start_angle = None
        end_angle = None
        radius = None
        
        sa_match = re.search(r'start\s*angle\s*=\s*([\d.-]+)', options)
        if sa_match:
            start_angle = float(sa_match.group(1))
        
        ea_match = re.search(r'end\s*angle\s*=\s*([\d.-]+)', options)
        if ea_match:
            end_angle = float(ea_match.group(1))
        
        r_match = re.search(r'radius\s*=\s*([\d.]+)\s*(cm|pt|mm)?', options)
        if r_match:
            radius = float(r_match.group(1))
            unit = r_match.group(2) or ''
            if unit == 'pt':
                radius = radius / 28.45
            elif unit == 'mm':
                radius = radius / 10
        
        if start_pos and start_angle is not None and end_angle is not None and radius:
            start_rad = math.radians(start_angle)
            center_x = start_pos[0] - radius * math.cos(start_rad)
            center_y = start_pos[1] - radius * math.sin(start_rad)
            
            elements["arcs"].append({
                "center": (center_x, center_y),
                "radius": radius,
                "start_angle": start_angle,
                "end_angle": end_angle
            })
    
    # Deduplicate points (remove points at same position)
    unique_points = []
    seen_positions = set()
    for point in elements["points"]:
        pos = point["position"]
        # Round to avoid floating point issues
        pos_key = (round(pos[0], 3), round(pos[1], 3))
        if pos_key not in seen_positions:
            seen_positions.add(pos_key)
            unique_points.append(point)
    elements["points"] = unique_points
    
    # Filter out very short "tick mark" lines (decorative elements)
    MIN_LINE_LENGTH = 0.3  # Minimum length in TikZ units to be considered a real line
    filtered_lines = []
    for line in elements["lines"]:
        start = line["start"]
        end = line["end"]
        length = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
        if length >= MIN_LINE_LENGTH:
            filtered_lines.append(line)
    elements["lines"] = filtered_lines
    
    # Compute geometric relationships
    elements["relationships"] = compute_geometric_relationships(elements)
    
    return elements


# =============================================================================
# Pillow-based Mask Generation
# =============================================================================

def tikz_to_pixel_coords(
    tikz_coord: tuple,
    scale: float,
    bbox: dict,
    image_size: tuple,
    dpi: int,
    border_pt: float = 10 * 28.45 / 72  # 10pt border in inches * 72 = pt, then to pixels
) -> tuple:
    """
    Convert TikZ coordinates to pixel coordinates.
    
    Args:
        tikz_coord: (x, y) in TikZ units (cm)
        scale: TikZ scale factor
        bbox: Bounding box in pt {'min_x', 'min_y', 'max_x', 'max_y'}
        image_size: (width, height) in pixels
        dpi: Image resolution
        border_pt: Border size in pt (standalone class adds 10pt border by default)
    
    Returns:
        (pixel_x, pixel_y) tuple
    """
    if bbox is None:
        # Fallback: assume standard coordinate system
        # TikZ default: 1 unit = 1cm = 28.45pt
        # With 300 DPI: 1pt = 300/72 pixels ≈ 4.17 pixels
        # So 1cm ≈ 28.45 * 4.17 ≈ 118.6 pixels
        
        pt_per_cm = 28.45
        pixels_per_pt = dpi / 72.0
        pixels_per_cm = pt_per_cm * pixels_per_pt
        
        # Assume center of image is origin, apply scale
        x_tikz, y_tikz = tikz_coord
        x_scaled = x_tikz * scale
        y_scaled = y_tikz * scale
        
        # Convert to pixels from center
        img_w, img_h = image_size
        pixel_x = img_w / 2 + x_scaled * pixels_per_cm
        pixel_y = img_h / 2 - y_scaled * pixels_per_cm  # Y is inverted in images
        
        return (pixel_x, pixel_y)
    
    # With bounding box from compilation
    pt_per_cm = 28.45
    pixels_per_pt = dpi / 72.0
    
    # Apply TikZ scale to coordinates (convert to pt)
    x_tikz, y_tikz = tikz_coord
    x_pt = x_tikz * scale * pt_per_cm
    y_pt = y_tikz * scale * pt_per_cm
    
    # Border offset in pt
    border = 10.0  # standalone border=10pt
    
    # Calculate image dimensions in pt (from bounding box + border)
    bbox_width_pt = bbox['max_x'] - bbox['min_x']
    bbox_height_pt = bbox['max_y'] - bbox['min_y']
    
    # Total size including border
    total_width_pt = bbox_width_pt + 2 * border
    total_height_pt = bbox_height_pt + 2 * border
    
    # Scale factor from pt to pixels
    img_w, img_h = image_size
    scale_x = img_w / total_width_pt
    scale_y = img_h / total_height_pt
    
    # Convert TikZ pt coordinates to pixel coordinates
    # Origin in TikZ is at (0,0), but in the image it's offset by bbox min + border
    pixel_x = (x_pt - bbox['min_x'] + border) * scale_x
    pixel_y = img_h - (y_pt - bbox['min_y'] + border) * scale_y  # Invert Y
    
    return (pixel_x, pixel_y)


def generate_masks_from_elements(
    elements: dict,
    image_path: str,
    bbox: dict = None,
    dpi: int = 300,
    line_width: int = 3
) -> dict:
    """
    Generate segmentation masks using Pillow based on parsed TikZ elements.
    
    Args:
        elements: Dict from parse_tikz_elements()
        image_path: Path to the rendered PNG (to get dimensions)
        bbox: Bounding box from compilation (optional)
        dpi: Image resolution
        line_width: Width of lines in pixels for masks
    
    Returns:
        Dict of {element_type: mask_image_path}
    """
    # Load original image to get dimensions
    with Image.open(image_path) as img:
        image_size = img.size
    
    scale = elements.get('scale', 1.0)
    masks_generated = {}
    base_path = image_path.replace('.png', '')
    
    # Helper to convert coordinates
    def to_pixel(coord):
        return tikz_to_pixel_coords(coord, scale, bbox, image_size, dpi)
    
    # Helper to convert radius from TikZ units (cm) to pixels
    def radius_to_pixels(radius_cm):
        pt_per_cm = 28.45
        pixels_per_pt = dpi / 72.0
        return radius_cm * scale * pt_per_cm * pixels_per_pt
    
    # Generate circles mask
    if elements['circles']:
        mask = Image.new('L', image_size, 0)  # Black background
        draw = ImageDraw.Draw(mask)
        
        for circle in elements['circles']:
            center_px = to_pixel(circle['center'])
            radius_px = radius_to_pixels(circle['radius'])
            
            # Draw circle outline
            bbox_circle = [
                center_px[0] - radius_px,
                center_px[1] - radius_px,
                center_px[0] + radius_px,
                center_px[1] + radius_px
            ]
            draw.ellipse(bbox_circle, outline=255, width=line_width)
        
        mask_path = f"{base_path}_mask_circles.png"
        mask.save(mask_path)
        masks_generated['circles'] = mask_path
    
    # Generate lines mask
    if elements['lines']:
        mask = Image.new('L', image_size, 0)
        draw = ImageDraw.Draw(mask)
        
        for line in elements['lines']:
            start_px = to_pixel(line['start'])
            end_px = to_pixel(line['end'])
            draw.line([start_px, end_px], fill=255, width=line_width)
        
        mask_path = f"{base_path}_mask_lines.png"
        mask.save(mask_path)
        masks_generated['lines'] = mask_path
    
    # Generate points mask
    if elements['points']:
        mask = Image.new('L', image_size, 0)
        draw = ImageDraw.Draw(mask)
        
        for point in elements['points']:
            pos_px = to_pixel(point['position'])
            # Use slightly larger radius for visibility
            size_px = max(point['size'] * dpi / 72.0, 4)  # At least 4 pixels
            
            bbox_point = [
                pos_px[0] - size_px,
                pos_px[1] - size_px,
                pos_px[0] + size_px,
                pos_px[1] + size_px
            ]
            draw.ellipse(bbox_point, fill=255)
        
        mask_path = f"{base_path}_mask_points.png"
        mask.save(mask_path)
        masks_generated['points'] = mask_path
    
    # Generate arcs mask
    if elements['arcs']:
        mask = Image.new('L', image_size, 0)
        draw = ImageDraw.Draw(mask)
        
        for arc in elements['arcs']:
            center_px = to_pixel(arc['center'])
            radius_px = radius_to_pixels(arc['radius'])
            
            bbox_arc = [
                center_px[0] - radius_px,
                center_px[1] - radius_px,
                center_px[0] + radius_px,
                center_px[1] + radius_px
            ]
            
            # Pillow arc uses degrees, 0 is 3 o'clock, counterclockwise
            # TikZ uses same convention
            # But image Y is inverted, so we need to flip angles
            start_angle = -arc['end_angle']
            end_angle = -arc['start_angle']
            
            draw.arc(bbox_arc, start_angle, end_angle, fill=255, width=line_width)
        
        mask_path = f"{base_path}_mask_arcs.png"
        mask.save(mask_path)
        masks_generated['arcs'] = mask_path
    
    # Generate combined mask
    mask = Image.new('L', image_size, 0)
    draw = ImageDraw.Draw(mask)
    
    # Draw all elements
    for circle in elements.get('circles', []):
        center_px = to_pixel(circle['center'])
        radius_px = radius_to_pixels(circle['radius'])
        bbox_circle = [
            center_px[0] - radius_px,
            center_px[1] - radius_px,
            center_px[0] + radius_px,
            center_px[1] + radius_px
        ]
        draw.ellipse(bbox_circle, outline=255, width=line_width)
    
    for line in elements.get('lines', []):
        start_px = to_pixel(line['start'])
        end_px = to_pixel(line['end'])
        draw.line([start_px, end_px], fill=255, width=line_width)
    
    for point in elements.get('points', []):
        pos_px = to_pixel(point['position'])
        size_px = max(point.get('size', 2) * dpi / 72.0, 4)
        bbox_point = [
            pos_px[0] - size_px,
            pos_px[1] - size_px,
            pos_px[0] + size_px,
            pos_px[1] + size_px
        ]
        draw.ellipse(bbox_point, fill=255)
    
    for arc in elements.get('arcs', []):
        center_px = to_pixel(arc['center'])
        radius_px = radius_to_pixels(arc['radius'])
        bbox_arc = [
            center_px[0] - radius_px,
            center_px[1] - radius_px,
            center_px[0] + radius_px,
            center_px[1] + radius_px
        ]
        start_angle = -arc['end_angle']
        end_angle = -arc['start_angle']
        draw.arc(bbox_arc, start_angle, end_angle, fill=255, width=line_width)
    
    mask_path = f"{base_path}_mask_all.png"
    mask.save(mask_path)
    masks_generated['all'] = mask_path
    
    return masks_generated


def generate_all_masks(tikz_code: str, output_path: str, dpi: int = 300, bbox: dict = None) -> dict:
    """
    Generate segmentation masks for all element types from TikZ code.
    
    Args:
        tikz_code: Original TikZ code
        output_path: Path to the rendered PNG image
        dpi: Resolution for mask images
        bbox: Optional bounding box from compilation
    
    Returns:
        Dict of {element_type: mask_path}
    """
    # Parse TikZ code to extract elements
    elements = parse_tikz_elements(tikz_code)
    
    # Check if we found any elements
    total_elements = (
        len(elements.get('circles', [])) +
        len(elements.get('lines', [])) +
        len(elements.get('points', [])) +
        len(elements.get('arcs', []))
    )
    
    if total_elements == 0:
        return {}
    
    # Generate masks using Pillow
    return generate_masks_from_elements(elements, output_path, bbox=bbox, dpi=dpi)


def generate_combination_masks(
    tikz_code: str,
    output_path: str,
    dpi: int = 300,
    bbox: dict = None,
    line_width: int = 3
) -> dict:
    """
    Generate C(N,2) combination masks for lines and arcs.
    
    Creates individual masks for:
    - Each possible line segment between any two points
    - Each arc (inner and outer) between points on same circle
    
    Args:
        tikz_code: Original TikZ code
        output_path: Path to the rendered PNG image
        dpi: Resolution for mask images
        bbox: Optional bounding box from compilation
        line_width: Width of lines in pixels for masks
    
    Returns:
        Dict with 'lines' and 'arcs' subdicts mapping labels to mask paths
    """
    # Parse elements and extract labels
    elements = parse_tikz_elements(tikz_code)
    labels = extract_point_labels(tikz_code)
    
    # Load original image to get dimensions
    with Image.open(output_path) as img:
        image_size = img.size
    
    scale = elements.get('scale', 1.0)
    base_path = output_path.replace('.png', '')
    masks_dir = f"{base_path}_masks"
    os.makedirs(masks_dir, exist_ok=True)
    
    result = {
        'lines': {},
        'arcs': {},
        'points': {},
        'circles': {}
    }
    
    # Helper functions
    def to_pixel(coord):
        return tikz_to_pixel_coords(coord, scale, bbox, image_size, dpi)
    
    def radius_to_pixels(radius_cm):
        pt_per_cm = 28.45
        pixels_per_pt = dpi / 72.0
        return radius_cm * scale * pt_per_cm * pixels_per_pt
    
    # Generate masks only for actually drawn line segments (not all combinations)
    lines = elements.get('lines', [])
    for i, line in enumerate(lines):
        mask = Image.new('L', image_size, 0)
        draw = ImageDraw.Draw(mask)
        
        start_px = to_pixel(line['start'])
        end_px = to_pixel(line['end'])
        draw.line([start_px, end_px], fill=255, width=line_width)
        
        # Get labels for the endpoints
        start_label = get_point_label(tuple(line['start']), labels) or f"P{i}a"
        end_label = get_point_label(tuple(line['end']), labels) or f"P{i}b"
        label = f"Line_{start_label}{end_label}"
        
        mask_path = os.path.join(masks_dir, f"{label}.png")
        mask.save(mask_path)
        result['lines'][label] = {
            'path': mask_path,
            'start': line['start'],
            'end': line['end'],
            'point1_label': start_label,
            'point2_label': end_label
        }
    
    # Generate split line segments (e.g., AM and BM when M is on line AB)
    split_lines = split_lines_at_labeled_points(elements, labels)
    for line_data in split_lines:
        mask = Image.new('L', image_size, 0)
        draw = ImageDraw.Draw(mask)
        
        start_px = to_pixel(line_data['start'])
        end_px = to_pixel(line_data['end'])
        draw.line([start_px, end_px], fill=255, width=line_width)
        
        label = line_data['label']
        mask_path = os.path.join(masks_dir, f"{label}.png")
        mask.save(mask_path)
        result['lines'][label] = {
            'path': mask_path,
            'start': line_data['start'],
            'end': line_data['end'],
            'point1_label': line_data['point1_label'],
            'point2_label': line_data['point2_label'],
            'derived_from': line_data.get('derived_from')
        }
    
    # Generate derived arcs from points on circles
    derived_arcs = generate_derived_arcs(elements, labels)
    for arc_data in derived_arcs:
        mask = Image.new('L', image_size, 0)
        draw = ImageDraw.Draw(mask)
        
        center_px = to_pixel(arc_data['center'])
        radius_px = radius_to_pixels(arc_data['radius'])
        
        bbox_arc = [
            center_px[0] - radius_px,
            center_px[1] - radius_px,
            center_px[0] + radius_px,
            center_px[1] + radius_px
        ]
        
        # Pillow arc: 0 is 3 o'clock, angles go counterclockwise
        # Image Y is inverted, so negate angles
        start_angle = -arc_data['end_angle']
        end_angle = -arc_data['start_angle']
        
        draw.arc(bbox_arc, start_angle, end_angle, fill=255, width=line_width)
        
        label = arc_data['label']
        mask_path = os.path.join(masks_dir, f"{label}.png")
        mask.save(mask_path)
        result['arcs'][label] = {
            'path': mask_path,
            'center': arc_data['center'],
            'radius': arc_data['radius'],
            'start_angle': arc_data['start_angle'],
            'end_angle': arc_data['end_angle'],
            'arc_type': arc_data['arc_type'],
            'point1_label': arc_data['point1_label'],
            'point2_label': arc_data['point2_label'],
            'circle_center_label': arc_data.get('circle_center_label')
        }
    
    # Generate individual point masks
    points = elements.get('points', [])
    for i, point in enumerate(points):
        mask = Image.new('L', image_size, 0)
        draw = ImageDraw.Draw(mask)
        
        pos_px = to_pixel(point['position'])
        size_px = max(point.get('size', 2) * dpi / 72.0, 4)
        
        bbox_point = [
            pos_px[0] - size_px,
            pos_px[1] - size_px,
            pos_px[0] + size_px,
            pos_px[1] + size_px
        ]
        draw.ellipse(bbox_point, fill=255)
        
        label = get_point_label(tuple(point['position']), labels) or f"P{i}"
        mask_path = os.path.join(masks_dir, f"Point_{label}.png")
        mask.save(mask_path)
        result['points'][f"Point_{label}"] = {
            'path': mask_path,
            'position': point['position'],
            'label': label
        }
    
    # Generate individual circle masks
    circles = elements.get('circles', [])
    for i, circle in enumerate(circles):
        mask = Image.new('L', image_size, 0)
        draw = ImageDraw.Draw(mask)
        
        center_px = to_pixel(circle['center'])
        radius_px = radius_to_pixels(circle['radius'])
        
        bbox_circle = [
            center_px[0] - radius_px,
            center_px[1] - radius_px,
            center_px[0] + radius_px,
            center_px[1] + radius_px
        ]
        draw.ellipse(bbox_circle, outline=255, width=line_width)
        
        center_label = get_point_label(tuple(circle['center']), labels) or f"C{i}"
        label = f"Circle_{center_label}"
        mask_path = os.path.join(masks_dir, f"{label}.png")
        mask.save(mask_path)
        result['circles'][label] = {
            'path': mask_path,
            'center': circle['center'],
            'radius': circle['radius'],
            'center_label': center_label
        }
    
    return result


def generate_labeled_pdf(
    tikz_code: str,
    output_path: str,
    elements: dict,
    labels: dict,
    combination_masks: dict
) -> str:
    """
    Generate a PDF document with labeled elements.
    
    Creates a multi-page PDF showing:
    - Page 1: Original figure with all labels
    - Following pages: Each element type with its masks listed
    
    Args:
        tikz_code: Original TikZ code
        output_path: Base path for output
        elements: Parsed elements dict
        labels: Point labels dict
        combination_masks: Output from generate_combination_masks()
    
    Returns:
        Path to generated PDF
    """
    # Create LaTeX document for labeled output
    latex_content = r"""
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{tikz}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{longtable}
\usetikzlibrary{angles,quotes,calc,intersections,through,backgrounds,patterns,decorations.markings,arrows.meta,shapes}

\begin{document}

\section*{Geometry Figure Segmentation Report}

\subsection*{Original Figure}
\begin{center}
""" + tikz_code + r"""
\end{center}

\subsection*{Points}
\begin{longtable}{lcc}
\toprule
\textbf{Label} & \textbf{X} & \textbf{Y} \\
\midrule
"""
    
    # Add points
    points = elements.get('points', [])
    for i, point in enumerate(points):
        pos = point['position']
        label = get_point_label(tuple(pos), labels) or f"P{i}"
        is_center = False
        for ci, circle in enumerate(elements.get('circles', [])):
            if abs(circle['center'][0] - pos[0]) < 0.01 and abs(circle['center'][1] - pos[1]) < 0.01:
                is_center = True
                break
        center_note = " (circle center)" if is_center else ""
        latex_content += f"{label}{center_note} & {pos[0]:.3f} & {pos[1]:.3f} \\\\\n"
    
    latex_content += r"""
\bottomrule
\end{longtable}

\subsection*{Circles}
\begin{longtable}{lcc}
\toprule
\textbf{Name} & \textbf{Center} & \textbf{Radius} \\
\midrule
"""
    
    # Add circles
    for label, data in combination_masks.get('circles', {}).items():
        center = data['center']
        radius = data['radius']
        center_label = data.get('center_label', '?')
        latex_content += f"Circle at {center_label} & ({center[0]:.3f}, {center[1]:.3f}) & {radius:.3f} \\\\\n"
    
    latex_content += r"""
\bottomrule
\end{longtable}

\subsection*{Line Segments (Drawn)}
\begin{longtable}{lll}
\toprule
\textbf{Segment} & \textbf{From} & \textbf{To} \\
\midrule
"""
    
    # Add only drawn line segments
    for label, data in combination_masks.get('lines', {}).items():
        p1 = data['point1_label']
        p2 = data['point2_label']
        latex_content += f"{p1}{p2} & {p1} & {p2} \\\\\n"
    
    latex_content += r"""
\bottomrule
\end{longtable}

\subsection*{Arcs (C(N,2) for Points on Same Circle)}
\begin{longtable}{llll}
\toprule
\textbf{Arc} & \textbf{Circle} & \textbf{Points} & \textbf{Type} \\
\midrule
"""
    
    # Add arcs - all C(N,2) combinations for points on same circle
    for label, data in combination_masks.get('arcs', {}).items():
        p1 = data['point1_label']
        p2 = data['point2_label']
        arc_type = data['arc_type']
        circle_center = data.get('circle_center_label', '?')
        latex_content += f"Arc {p1}{p2} & Circle {circle_center} & {p1}, {p2} & {arc_type} \\\\\n"
    
    latex_content += r"""
\bottomrule
\end{longtable}

\subsection*{Geometric Relationships}
"""
    
    # Add relationships
    relationships = elements.get('relationships', {})
    
    poc = relationships.get('points_on_circles', [])
    if poc:
        latex_content += r"\textbf{Points on Circles:}" + "\n" + r"\begin{itemize}" + "\n"
        for rel in poc:
            pi = rel['point_idx']
            ci = rel['circle_idx']
            pos = rel['point_pos']
            point_label = get_point_label(tuple(pos), labels) or f"P{pi}"
            
            # Get circle center label
            circle = elements['circles'][ci]
            center_label = get_point_label(tuple(circle['center']), labels) or f"C{ci}"
            
            latex_content += f"  \\item Point {point_label} is on Circle {center_label}\n"
        latex_content += r"\end{itemize}" + "\n"
    
    pol = relationships.get('points_on_lines', [])
    if pol:
        latex_content += r"\textbf{Points on Lines:}" + "\n" + r"\begin{itemize}" + "\n"
        for rel in pol:
            pi = rel['point_idx']
            pos = rel['point_pos']
            point_label = get_point_label(tuple(pos), labels) or f"P{pi}"
            
            start = rel['line_start']
            end = rel['line_end']
            start_label = get_point_label(tuple(start), labels) or "?"
            end_label = get_point_label(tuple(end), labels) or "?"
            position = rel['position_on_line']
            
            latex_content += f"  \\item Point {point_label} is at {position} of line {start_label}{end_label}\n"
        latex_content += r"\end{itemize}" + "\n"
    
    latex_content += r"""
\end{document}
"""
    
    # Compile to PDF
    pdf_path = output_path.replace('.png', '_labels.pdf')
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = os.path.join(tmpdir, "labels.tex")
        pdf_file = os.path.join(tmpdir, "labels.pdf")
        
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        try:
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_file],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if os.path.exists(pdf_file):
                shutil.copy(pdf_file, pdf_path)
                return pdf_path
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    return None


def get_latex_preamble() -> str:
    """Return the LaTeX preamble."""
    return LATEX_PREAMBLE


def get_latex_postamble() -> str:
    """Return the LaTeX postamble."""
    return LATEX_POSTAMBLE

"""
Classification prompts for image and caption categorization.
"""


def get_category_classification_prompt() -> str:
    """Get the prompt for mutually exclusive category classification using descriptions."""
    return """Classify this image into EXACTLY ONE of the following categories:

**geometry** - 2D geometry math diagrams:
  - Triangles, circles, angles, arcs, polygons
  - Geometric constructions with labeled points/vertices (e.g., A, B, C)
  - Problems involving parallel lines, perpendicular lines, tangents
  - Inscribed/circumscribed shapes, angle bisectors, medians
  - Pure geometric figures WITHOUT coordinate axes

**coordinates** - Coordinate systems and mathematical function graphs:
  - Cartesian coordinate systems with x/y axes and tick marks
  - Function graphs (parabolas, lines, curves, trigonometric functions)
  - Number lines with labeled points
  - Plotted points or curves on a coordinate plane
  - NOTE: Must have visible axes/coordinate system, NOT just shapes

**charts** - Data visualizations:
  - Bar charts, histograms (vertical or horizontal bars showing data)
  - Line charts showing trends over time
  - Pie charts showing proportions
  - Scatter plots with data points
  - Any chart showing real-world data with labels/legends

**other** - Everything else:
  - Text-only images, formulas, equations
  - Tables, flowcharts, diagrams
  - Photos, illustrations, decorative images
  - Anything that doesn't clearly fit the above categories

RULES:
- Choose EXACTLY ONE category
- If uncertain, choose "other"
- "coordinates" requires visible axes; a shape on a grid is still "geometry" unless axes are labeled

Respond with JSON: {"reasoning": "<brief explanation>", "category": "<geometry|coordinates|charts|other>"}
"""


def get_caption_classification_prompt(caption: str, code: str) -> str:
    """Get the classification prompt for caption-only categorization (no image)."""
    return f"""Based on the caption/description and TikZ code below, classify this figure by answering true/false for each category:

1. **is_geometry**: Is this a 2D geometry math problem?
   - Triangles, circles, angles, arcs, polygons
   - Geometric constructions with labeled points/vertices
   - Problems involving parallel lines, perpendicular lines, tangents
   - Inscribed/circumscribed shapes

2. **is_coordinate**: Does this contain coordinate systems or function graphs (NOT charts)?
   - 1D or 2D coordinate systems with axes and ticks
   - Function graphs, mathematical plots, curves
   - Number lines, Cartesian planes with plotted points
   - NOTE: If is_chart is true, is_coordinate must be false

3. **is_chart**: Is this a data visualization?
   - Bar charts, histograms
   - Line plots, time series
   - Pie charts, scatter plots
   - State diagrams, flowcharts

IMPORTANT RULES:
- BE CONSERVATIVE: When uncertain, answer FALSE. We have lots of data, so it's better to miss some than to include wrong ones.
- If is_chart is TRUE, then is_coordinate must be FALSE (mutually exclusive).
- If the figure contains ONLY text, formulas, equations, tables, or is purely text-based without any visual diagram, answer FALSE for ALL categories.
- Generic diagrams, illustrations, or decorative figures should be FALSE for all.

Caption/Description:
{caption}

TikZ code:
{code}

Respond with ONLY a JSON object in this exact format (no other text):
{{"reasoning": "<brief explanation>", "is_geometry": true/false, "is_coordinate": true/false, "is_chart": true/false}}
"""


def get_classification_prompt(caption: str, code: str) -> str:
    """Get the classification prompt for image + caption categorization."""
    return f"""Classify this image by answering true/false for each category:

1. **is_geometry**: Is this a 2D geometry math problem?
   - Triangles, circles, angles, arcs, polygons
   - Geometric constructions with labeled points/vertices
   - Problems involving parallel lines, perpendicular lines, tangents
   - Inscribed/circumscribed shapes

2. **is_coordinate**: Does this contain coordinate systems or function graphs (NOT charts)?
   - 1D or 2D coordinate systems with axes and ticks
   - Function graphs, mathematical plots, curves
   - Number lines, Cartesian planes with plotted points
   - NOTE: If is_chart is true, is_coordinate must be false

3. **is_chart**: Is this a data visualization?
   - Bar charts, histograms
   - Line plots, time series
   - Pie charts, scatter plots
   - State diagrams, flowcharts

IMPORTANT RULES:
- BE CONSERVATIVE: When uncertain, answer FALSE. We have lots of data, so it's better to miss some than to include wrong ones.
- If is_chart is TRUE, then is_coordinate must be FALSE (mutually exclusive).
- If the image contains ONLY text, formulas, equations, tables, or is purely text-based without any visual diagram, answer FALSE for ALL categories.
- Generic illustrations or decorative figures should be FALSE for all.

Caption/Description:
{caption}


Respond with ONLY a JSON object in this exact format (no other text):
{{"reasoning": "<brief explanation>", "is_geometry": true/false, "is_coordinate": true/false, "is_chart": true/false}}
"""


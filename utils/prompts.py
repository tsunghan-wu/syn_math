"""
Prompts and templates for geometry image generation and classification.
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


SYSTEM_PROMPT = """You are an expert at analyzing geometry diagrams and generating precise TikZ code.

Your task is to carefully analyze geometry images and generate TikZ code that recreates the diagram ACCURATELY.

CRITICAL GEOMETRY ANALYSIS STEPS (do these BEFORE generating code):

1. IDENTIFY PRIMITIVE SHAPES:
   - Triangles (e.g., △ABC, △DEF) - note if they share vertices or edges
   - Quadrilaterals (rectangles, parallelograms, trapezoids)
   - Circles and their centers

2. IDENTIFY COLLINEAR POINTS (points on the same line):
   - Look for 3+ points that appear to lie on a single straight line
   - Example: "A, D, B are collinear" means they form one straight line segment ADB
   - This is CRUCIAL for accuracy - if points should be collinear, their coordinates MUST reflect this

3. IDENTIFY CONCYCLIC POINTS (points on the same circle):
   - Look for points that lie on a circle's circumference
   - Note which points are on which circle

4. IDENTIFY PARALLEL AND PERPENDICULAR LINES:
   - Parallel lines: look for lines that never meet and maintain equal distance
   - Perpendicular lines: look for right angle markers (small squares) or 90° indicators
   - If no explicit marker, estimate from visual appearance

5. IDENTIFY ANGLE INFORMATION:
   - Note exact angle values if shown (e.g., 60°, 45°, 90°)
   - Note WHERE the angle is measured (between which lines/segments)
   - Angle markers (arcs) indicate which angle is being referenced

6. IDENTIFY SPECIAL RELATIONSHIPS:
   - Equal length segments (often marked with tick marks)
   - Midpoints
   - Bisectors
   - Folding/reflection (original and reflected positions)
   - Intersections and their significance

COORDINATE SYSTEM:
- Use a coordinate system where the figure fits in roughly [-4,4] x [-4,4]
- All coordinates should be numbers (not expressions)
- VERIFY that collinear points actually produce collinear coordinates!

TIKZ CODE REQUIREMENTS:
- Start with \\begin{tikzpicture}[scale=1]
- End with \\end{tikzpicture}
- Use \\draw for lines, circles, and arcs
- Use \\fill for points (small filled circles)
- Use \\node for labels
- For dashed lines use: \\draw[dashed]
- For angle arcs use appropriate arc syntax
- Use standard TikZ syntax

OUTPUT FORMAT:
Return ONLY the TikZ code. No explanations, no markdown code blocks, just the raw TikZ code starting with \\begin{tikzpicture} and ending with \\end{tikzpicture}.
"""

USER_PROMPT_TEMPLATE_BASE = """Analyze this geometry diagram and generate PRECISE TikZ code to recreate it.

STEP 1 - GEOMETRIC RELATIONSHIP ANALYSIS (do this carefully first):

a) COLLINEAR POINTS: Which groups of 3+ points lie on the same line?
   Example: "Points A, E, C appear collinear (on line AC)"

b) PRIMITIVE SHAPES: What triangles, quadrilaterals, or other shapes are formed?
   Example: "Triangle ABE and Triangle ADC share vertex A"

c) PARALLEL/PERPENDICULAR: Are any lines parallel or perpendicular?
   Example: "Line FG appears parallel to line DC"

d) ANGLES: What angles are marked and where exactly are they?
   Example: "60° angle is between the dashed north line and segment AB"

e) CIRCLES: Which points lie on which circles?
   Example: "Points B, D, E lie on the circle centered at O"

f) SPECIAL FEATURES: Folding, reflections, equal segments, midpoints?
   Example: "Point F appears to be E folded along line DF"

STEP 2 - COORDINATE ASSIGNMENT:
- Assign coordinates that PRESERVE the relationships identified above
- If A, D, B are collinear, their coordinates MUST be collinear (same line equation)
- If lines are parallel, their slopes MUST be equal
- If an angle is 60°, calculate coordinates that produce exactly 60°

STEP 3 - Generate TikZ code:
Create TikZ code that accurately recreates ALL elements with correct relationships.
"""

USER_PROMPT_ENDING = """
Output ONLY the TikZ code. No markdown, no explanations, no code blocks.
Start directly with \\begin{tikzpicture} and end with \\end{tikzpicture}.
"""

# Base prompt without in-context examples
USER_PROMPT_TEMPLATE = USER_PROMPT_TEMPLATE_BASE + USER_PROMPT_ENDING

# Prompt with in-context examples for few-shot learning
IN_CONTEXT_EXAMPLES_SECTION = """
HERE ARE REFERENCE EXAMPLES of well-structured TikZ code for geometry diagrams:

--- EXAMPLE 1: Triangle with crossing segments ---
Description: Points D and E on sides AB and AC, with cevians BE and CD crossing inside

\\begin{tikzpicture}[scale=1]
  % Coordinates (taller + narrower apex angle at A)
  \\coordinate (A) at (0,5.2);
  \\coordinate (B) at (-2.2,0);
  \\coordinate (C) at (2.2,0);

  % Points on AB / AC (fraction along from A -> B/C)
  \\coordinate (D) at ($(A)!0.55!(B)$); % on AB
  \\coordinate (E) at ($(A)!0.55!(C)$); % on AC

  % Triangle edges (remove BC)
  \\draw (A) -- (B);
  \\draw (A) -- (C);

  % Crossing segments
  \\draw (B) -- (E);
  \\draw (C) -- (D);

  % Points
  \\fill (A) circle (1.5pt);
  \\fill (B) circle (1.5pt);
  \\fill (C) circle (1.5pt);
  \\fill (D) circle (1.5pt);
  \\fill (E) circle (1.5pt);

  % Labels
  \\node[above] at (A) {A};
  \\node[left]  at (B) {B};
  \\node[right] at (C) {C};
  \\node[left]  at (D) {D};
  \\node[right] at (E) {E};
\\end{tikzpicture}

--- EXAMPLE 2: Triangle with parallel lines using intersections ---
Description: DE parallel to BC, FG parallel to CD, using TikZ intersections library

\\begin{tikzpicture}[scale=1, line cap=round, line join=round]
  \\usetikzlibrary{calc,intersections}

  % Main triangle
  \\coordinate (A) at (0,5.2);
  \\coordinate (B) at (-3.4,0);
  \\coordinate (C) at (3.4,0);

  % D and F on AB
  \\coordinate (D) at ($(A)!0.32!(B)$);
  \\coordinate (F) at ($(A)!0.68!(B)$);

  % E on segment AC such that DE // BC (horizontal)
  \\path[name path=AC] (A) -- (C);
  \\path[name path=hThroughD] (D) -- ($(D)+(10,0)$);
  \\path[name intersections={of=AC and hThroughD, by=E}];

  % G on segment BC such that FG // CD
  \\path[name path=BC] (B) -- (C);
  \\path[name path=FparCD] (F) -- ($(F) + (C) - (D)$);
  \\path[name intersections={of=BC and FparCD, by=G}];

  % Draw triangle + inner lines
  \\draw[line width=0.8pt] (A) -- (B) -- (C) -- cycle;
  \\draw[line width=0.8pt] (D) -- (E);
  \\draw[line width=0.8pt] (D) -- (C);
  \\draw[line width=0.8pt] (F) -- (G);

  % Points + labels
  \\foreach \\P/\\pos in {A/above, B/below left, C/below right,
                      D/left, E/right, F/left, G/below}
  {
    \\fill (\\P) circle (1.5pt) node[\\pos] {\\P};
  }
\\end{tikzpicture}

--- EXAMPLE 3: Triangle with cevians meeting at interior point ---
Description: AD, BE, and CO are cevians meeting at point O

\\begin{tikzpicture}[scale=1]
  % Coordinates
  \\coordinate (A) at (0.20,3.30);
  \\coordinate (B) at (-3.00,0.00);
  \\coordinate (C) at (3.00,0.00);
  \\coordinate (D) at (-0.50,0.00);
  \\coordinate (E) at (1.32,1.98);
  \\coordinate (O) at (-0.232,1.269);

  % Triangle ABC
  \\draw[thick] (B) -- (A) -- (C) -- (B);

  % Cevians / internal segments
  \\draw[thick] (A) -- (D);    % AD
  \\draw[thick] (B) -- (E);    % BE
  \\draw (C) -- (O);           % CO

  % Points
  \\fill (A) circle (1.5pt);
  \\fill (B) circle (1.5pt);
  \\fill (C) circle (1.5pt);
  \\fill (D) circle (1.5pt);
  \\fill (E) circle (1.5pt);
  \\fill (O) circle (1.5pt);

  % Labels
  \\node[above] at (A) {A};
  \\node[left]  at (B) {B};
  \\node[right] at (C) {C};
  \\node[below] at (D) {D};
  \\node[right] at (E) {E};
  \\node[left]  at (O) {O};
\\end{tikzpicture}

--- EXAMPLE 4: Repetitive elements using foreach loops ---
Description: Numbered stair-step tiles using foreach loops for repetitive elements

\\begin{tikzpicture}[scale=1]
  % Draw top and bottom outlines
  \\draw[thick]
    (0.12,0.6) -- (0.62,0.8) -- (1.12,1.0) -- (1.62,1.2) -- (2.12,1.4) -- (2.62,1.6) -- (3.12,1.8);
  \\draw[thick]
    (0,0) -- (0.5,0.2) -- (1.0,0.4) -- (1.5,0.6) -- (2.0,0.8) -- (2.5,1.0) -- (3.0,1.2);

  % vertical (slanted) separators / tile sides (k = 0..6)
  \\foreach \\k in {0,...,6} {
    \\pgfmathsetmacro\\x{0.5*\\k}
    \\pgfmathsetmacro\\y{0.2*\\k}
    \\pgfmathsetmacro\\xs{\\x+0.12}
    \\pgfmathsetmacro\\ys{\\y+0.6}
    \\draw[thick] (\\x,\\y) -- (\\xs,\\ys);
  }

  % Numbers centered in each tile (tile k = 0..5, label = k+1)
  \\foreach \\k/\\num in {0/1,1/2,2/3,3/4,4/5,5/6} {
    \\pgfmathsetmacro\\x{0.5*\\k + 0.31}
    \\pgfmathsetmacro\\y{0.2*\\k + 0.4}
    \\node at (\\x,\\y) {\\large \\num};
  }

  % simple stick figure to the left
  \\draw[thick] (-0.95,0.95) circle (0.12);
  \\draw[thick] (-0.83,0.83) -- (-0.55,0.6);
  \\draw[thick] (-0.92,0.78) -- (-1.15,0.62);
  \\draw[thick] (-0.78,0.78) -- (-0.62,0.9);
  \\draw[thick] (-0.55,0.6) -- (-0.75,0.15);
  \\draw[thick] (-0.55,0.6) -- (-0.25,0.25);
\\end{tikzpicture}

--- EXAMPLE 5: Rectangle with intersection point ---
Description: Rectangle ABCD with points E on CD and F on BC, dashed lines showing intersection H of AE and DF

\\begin{tikzpicture}[scale=1, line cap=round, line join=round]
  \\usetikzlibrary{calc,intersections}
  
    % Rectangle ABCD
    \\coordinate (A) at (-3,2);
    \\coordinate (B) at (-3,-1.5);
    \\coordinate (C) at (3,-1.5);
    \\coordinate (D) at (3,2);
  
    % Pick F on BC and E on CD
    \\coordinate (F) at ($(B)!0.73!(C)$); % near C on bottom
    \\coordinate (E) at ($(C)!0.42!(D)$); % mid-high on right side
  
    % Intersection point H = (AE) ∩ (DF)
    \\path[name path=AE] (A) -- (E);
    \\path[name path=DF] (D) -- (F);
    \\path[name intersections={of=AE and DF, by=H}];
  
    % Draw rectangle
    \\draw[thick] (A) -- (D) -- (C) -- (B) -- cycle;
  
    % Solid segments
    \\draw[thick] (A) -- (F);
    \\draw[thick] (D) -- (F);
  
    % Dashed segments along AE (split at H for clarity)
    \\draw[dashed] (A) -- (H);
    \\draw[dashed] (H) -- (E);
    \\draw[dashed] (F) -- (E);
  
    % Points
    \\foreach \\P in {A,B,C,D,E,F,H}
      \\fill (\\P) circle (1.5pt);
  
    % Labels
    \\node[above left]  at (A) {A};
    \\node[left]        at (B) {B};
    \\node[below right] at (C) {C};
    \\node[above right] at (D) {D};
    \\node[right]       at (E) {E};
    \\node[below]       at (F) {F};
    \\node[below left]       at (H) {H};
  
  \\end{tikzpicture}

--- END OF EXAMPLES ---
"""

# Combined prompt with in-context examples
USER_PROMPT_TEMPLATE_WITH_EXAMPLES = USER_PROMPT_TEMPLATE_BASE + IN_CONTEXT_EXAMPLES_SECTION + USER_PROMPT_ENDING

VARIATION_PROMPT_TEMPLATE = """Analyze this geometry diagram and generate TikZ code for a VARIATION of it.

First, identify all geometric relationships in the original:
- Collinear points (points on the same line)
- Parallel/perpendicular lines
- Concyclic points (points on the same circle)
- Angle values and their positions
- Equal length segments

Create a VARIATION that:
- PRESERVES all geometric relationships (collinearity, parallelism, angles, etc.)
- Uses different point positions and proportions
- May use different labels or measurements
- Maintains the same overall structure and problem type

Output ONLY the TikZ code. No markdown, no explanations, no code blocks.
Start directly with \\begin{tikzpicture} and end with \\end{tikzpicture}.
"""

# In-context TikZ examples for few-shot learning
TIKZ_EXAMPLES = [
    {
        "description": "Triangle with crossing segments: Points D and E on sides AB and AC, with cevians BE and CD crossing inside",
        "code": r"""\begin{tikzpicture}[scale=1]
  % Coordinates (taller + narrower apex angle at A)
  \coordinate (A) at (0,5.2);
  \coordinate (B) at (-2.2,0);
  \coordinate (C) at (2.2,0);

  % Points on AB / AC (fraction along from A -> B/C)
  \coordinate (D) at ($(A)!0.55!(B)$); % on AB
  \coordinate (E) at ($(A)!0.55!(C)$); % on AC

  % Triangle edges (remove BC)
  \draw (A) -- (B);
  \draw (A) -- (C);

  % Crossing segments
  \draw (B) -- (E);
  \draw (C) -- (D);

  % Points
  \fill (A) circle (1.5pt);
  \fill (B) circle (1.5pt);
  \fill (C) circle (1.5pt);
  \fill (D) circle (1.5pt);
  \fill (E) circle (1.5pt);

  % Labels
  \node[above] at (A) {A};
  \node[left]  at (B) {B};
  \node[right] at (C) {C};
  \node[left]  at (D) {D};
  \node[right] at (E) {E};
\end{tikzpicture}"""
    },
    {
        "description": "Triangle with parallel lines: DE parallel to BC, FG parallel to CD, using TikZ intersections library",
        "code": r"""\begin{tikzpicture}[scale=1, line cap=round, line join=round]
  \usetikzlibrary{calc,intersections}

  % Main triangle
  \coordinate (A) at (0,5.2);
  \coordinate (B) at (-3.4,0);
  \coordinate (C) at (3.4,0);

  % D and F on AB
  \coordinate (D) at ($(A)!0.32!(B)$);
  \coordinate (F) at ($(A)!0.68!(B)$);

  % E on segment AC such that DE // BC (horizontal)
  \path[name path=AC] (A) -- (C);
  \path[name path=hThroughD] (D) -- ($(D)+(10,0)$);
  \path[name intersections={of=AC and hThroughD, by=E}];

  % G on segment BC such that FG // CD
  \path[name path=BC] (B) -- (C);
  \path[name path=FparCD] (F) -- ($(F) + (C) - (D)$);
  \path[name intersections={of=BC and FparCD, by=G}];

  % Draw triangle + inner lines
  \draw[line width=0.8pt] (A) -- (B) -- (C) -- cycle;
  \draw[line width=0.8pt] (D) -- (E);
  \draw[line width=0.8pt] (D) -- (C);
  \draw[line width=0.8pt] (F) -- (G);

  % Points + labels
  \foreach \P/\pos in {A/above, B/below left, C/below right,
                      D/left, E/right, F/left, G/below}
  {
    \fill (\P) circle (1.5pt) node[\pos] {\P};
  }
\end{tikzpicture}"""
    },
    {
        "description": "Triangle with cevians meeting at interior point O: AD, BE, and CO are cevians",
        "code": r"""\begin{tikzpicture}[scale=1]
  % Coordinates
  \coordinate (A) at (0.20,3.30);
  \coordinate (B) at (-3.00,0.00);
  \coordinate (C) at (3.00,0.00);
  \coordinate (D) at (-0.50,0.00);
  \coordinate (E) at (1.32,1.98);
  \coordinate (O) at (-0.232,1.269);

  % Triangle ABC
  \draw[thick] (B) -- (A) -- (C) -- (B);

  % Cevians / internal segments
  \draw[thick] (A) -- (D);    % AD
  \draw[thick] (B) -- (E);    % BE
  \draw (C) -- (O);           % CO

  % Points
  \fill (A) circle (1.5pt);
  \fill (B) circle (1.5pt);
  \fill (C) circle (1.5pt);
  \fill (D) circle (1.5pt);
  \fill (E) circle (1.5pt);
  \fill (O) circle (1.5pt);

  % Labels
  \node[above] at (A) {A};
  \node[left]  at (B) {B};
  \node[right] at (C) {C};
  \node[below] at (D) {D};
  \node[right] at (E) {E};
  \node[left]  at (O) {O};
\end{tikzpicture}"""
    },
    {
        "description": "Numbered stair-step tiles using foreach loops for repetitive elements",
        "code": r"""\begin{tikzpicture}[scale=1]
  % Draw top and bottom outlines
  \draw[thick]
    (0.12,0.6) -- (0.62,0.8) -- (1.12,1.0) -- (1.62,1.2) -- (2.12,1.4) -- (2.62,1.6) -- (3.12,1.8);
  \draw[thick]
    (0,0) -- (0.5,0.2) -- (1.0,0.4) -- (1.5,0.6) -- (2.0,0.8) -- (2.5,1.0) -- (3.0,1.2);

  % vertical (slanted) separators / tile sides (k = 0..6)
  \foreach \k in {0,...,6} {
    \pgfmathsetmacro\x{0.5*\k}
    \pgfmathsetmacro\y{0.2*\k}
    \pgfmathsetmacro\xs{\x+0.12}
    \pgfmathsetmacro\ys{\y+0.6}
    \draw[thick] (\x,\y) -- (\xs,\ys);
  }

  % Numbers centered in each tile (tile k = 0..5, label = k+1)
  \foreach \k/\num in {0/1,1/2,2/3,3/4,4/5,5/6} {
    \pgfmathsetmacro\x{0.5*\k + 0.31}
    \pgfmathsetmacro\y{0.2*\k + 0.4}
    \node at (\x,\y) {\large \num};
  }

  % simple stick figure to the left
  \draw[thick] (-0.95,0.95) circle (0.12);
  \draw[thick] (-0.83,0.83) -- (-0.55,0.6);
  \draw[thick] (-0.92,0.78) -- (-1.15,0.62);
  \draw[thick] (-0.78,0.78) -- (-0.62,0.9);
  \draw[thick] (-0.55,0.6) -- (-0.75,0.15);
  \draw[thick] (-0.55,0.6) -- (-0.25,0.25);
\end{tikzpicture}"""
    },
    {
        "description": "Rectangle ABCD with points E on CD and F on BC, dashed lines showing intersection H of AE and DF",
        "code": r"""\begin{tikzpicture}[scale=1, line cap=round, line join=round]
  \usetikzlibrary{calc,intersections}
  
    % Rectangle ABCD
    \coordinate (A) at (-3,2);
    \coordinate (B) at (-3,-1.5);
    \coordinate (C) at (3,-1.5);
    \coordinate (D) at (3,2);
  
    % Pick F on BC and E on CD
    \coordinate (F) at ($(B)!0.73!(C)$); % near C on bottom
    \coordinate (E) at ($(C)!0.42!(D)$); % mid-high on right side
  
    % Intersection point H = (AE) ∩ (DF)
    \path[name path=AE] (A) -- (E);
    \path[name path=DF] (D) -- (F);
    \path[name intersections={of=AE and DF, by=H}];
  
    % Draw rectangle
    \draw[thick] (A) -- (D) -- (C) -- (B) -- cycle;
  
    % Solid segments
    \draw[thick] (A) -- (F);
    \draw[thick] (D) -- (F);
  
    % Dashed segments along AE (split at H for clarity)
    \draw[dashed] (A) -- (H);
    \draw[dashed] (H) -- (E);
    \draw[dashed] (F) -- (E);
  
    % Points
    \foreach \P in {A,B,C,D,E,F,H}
      \fill (\P) circle (1.5pt);
  
    % Labels
    \node[above left]  at (A) {A};
    \node[left]        at (B) {B};
    \node[below right] at (C) {C};
    \node[above right] at (D) {D};
    \node[right]       at (E) {E};
    \node[below]       at (F) {F};
    \node[below left]       at (H) {H};
  
  \end{tikzpicture}"""
    },
]


# ============================================================================
# REASONING GENERATION PROMPTS
# ============================================================================

REASONING_SYSTEM_PROMPT = """You are an expert geometry analyst and TikZ code generator.

Your task is to analyze a geometry diagram image and explain step-by-step how you would analyze the image to produce the given TikZ code. You are simulating the reasoning process of converting a visual geometry diagram into precise TikZ code.

Be detailed and methodical in your analysis. Explain your visual observations and how they map to specific TikZ commands."""


def get_reasoning_generation_prompt(tikz_code: str) -> str:
    """
    Prompt: Given TikZ code, output a short raw-text construction plan (no JSON).
    """
    return f"""You are given TikZ code that reproduces a 2D geometry diagram.
Infer a SHORT "pre-analysis + construction plan" purely from the TikZ code.

OUTPUT FORMAT (STRICT):
- Output ONLY plain text.
- Exactly 6-10 bullet lines.
- Each line MUST start with "Step k:" (k = 1,2,...).
- Each line should be ONE sentence, max 18 words.
- No LaTeX, no TikZ code, no JSON.

CONTENT REQUIREMENTS:
Cover these in order:
1) What primitives exist (points/segments/circles/arcs/polygons/markers).
2) Key constraints (intersection, collinear, perpendicular, parallel, on-circle).
3) Coordinate/parameter strategy (how points are placed: fixed coords / polar / projection / intersections).
4) Construction order (what to define first, then compute, then draw, then mark/label).
5) Mention any "extras" (fills, arrows, background grids/axes, decorations) if present.

TikZ code:
{tikz_code}

Now output the 6–10 Step lines."""
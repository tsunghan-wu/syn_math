"""
LLM helper functions for OpenAI Vision API interactions.
"""

import base64
import json
import os
import random
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from openai import OpenAI

from .prompts import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE_BASE,
    USER_PROMPT_ENDING,
    VARIATION_PROMPT_TEMPLATE
)


class TikZGenerationResult(BaseModel):
    """Structured output for TikZ generation with reasoning."""
    reasoning: str
    tikz_code: str

# Default path for in-context examples (relative to this file's parent)
IN_CONTEXT_EXAMPLES_DIR = Path(__file__).parent.parent / "in-context-examples"


def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_image_media_type(image_path: str) -> str:
    """Get the media type based on file extension."""
    ext = Path(image_path).suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(ext, "image/png")


def load_in_context_examples(examples_dir: Path = None) -> list[dict]:
    """
    Load all in-context examples from the examples directory.
    
    Args:
        examples_dir: Path to directory containing example JSON files.
                     Defaults to IN_CONTEXT_EXAMPLES_DIR.
    
    Returns:
        List of example dictionaries with 'reasoning' and 'tikz_code' keys.
    """
    if examples_dir is None:
        examples_dir = IN_CONTEXT_EXAMPLES_DIR
    
    examples = []
    if not examples_dir.exists():
        return examples
    
    for json_file in sorted(examples_dir.glob("*.json")):
        try:
            with open(json_file, 'r') as f:
                example = json.load(f)
                examples.append(example)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load {json_file}: {e}")
    
    return examples


def sample_in_context_examples(n: int = 3, examples_dir: Path = None) -> list[dict]:
    """
    Randomly sample n in-context examples.
    
    Args:
        n: Number of examples to sample
        examples_dir: Path to examples directory
    
    Returns:
        List of n randomly selected example dictionaries.
    """
    examples = load_in_context_examples(examples_dir)
    if len(examples) <= n:
        return examples
    return random.sample(examples, n)


def build_dynamic_examples_prompt(examples: list[dict]) -> str:
    """
    Build the in-context examples section of the prompt from sampled examples.
    
    Args:
        examples: List of example dictionaries with 'reasoning' and 'tikz_code'
    
    Returns:
        Formatted string containing the examples section.
    """
    if not examples:
        return ""
    
    sections = ["\nHERE ARE REFERENCE EXAMPLES of geometry analysis and TikZ code generation:\n"]
    
    for i, example in enumerate(examples, 1):
        reasoning = example.get('reasoning', '')
        tikz_code = example.get('tikz_code', '')
        
        sections.append(f"--- EXAMPLE {i} ---")
        sections.append(f"Analysis:\n{reasoning}\n")
        sections.append(f"TikZ Code:\n{tikz_code}\n")
    
    sections.append("--- END OF EXAMPLES ---\n")
    
    return "\n".join(sections)


def build_prompt_with_dynamic_examples(n_examples: int = 5) -> str:
    """
    Build a complete user prompt with randomly sampled in-context examples.
    
    Args:
        n_examples: Number of examples to include (default: 5)
    
    Returns:
        Complete user prompt string with dynamic examples.
    """
    examples = sample_in_context_examples(n_examples)
    examples_section = build_dynamic_examples_prompt(examples)
    return USER_PROMPT_TEMPLATE_BASE + examples_section + USER_PROMPT_ENDING


def extract_tikz_code(response: str) -> str:
    """
    Extract TikZ code from LLM response.
    
    Handles various formats:
    - Raw TikZ code
    - Code wrapped in markdown code blocks
    - Code with extra text before/after
    """
    # Remove markdown code blocks if present
    if "```" in response:
        lines = response.split("\n")
        in_code_block = False
        code_lines = []
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                code_lines.append(line)
        if code_lines:
            response = "\n".join(code_lines)
    
    # Extract tikzpicture environment
    if "\\begin{tikzpicture}" in response:
        start = response.find("\\begin{tikzpicture}")
        end = response.find("\\end{tikzpicture}")
        if end != -1:
            response = response[start:end + len("\\end{tikzpicture}")]
    
    return response.strip()


def generate_tikz_from_image(
    client: OpenAI,
    image_path: str,
    create_variation: bool = False,
    model: str = "gpt-4o",
    use_in_context_examples: bool = False
) -> TikZGenerationResult:
    """
    Use OpenAI's vision API to generate TikZ code from an image with reasoning.
    
    Args:
        client: OpenAI client instance
        image_path: Path to the geometry image
        create_variation: If True, create a variation instead of exact recreation
        model: OpenAI model to use (gpt-4o, gpt-4-vision-preview, etc.)
        use_in_context_examples: If True, include in-context TikZ examples in prompt
    
    Returns:
        TikZGenerationResult with reasoning and tikz_code
    """
    # Encode image
    base64_image = encode_image_to_base64(image_path)
    media_type = get_image_media_type(image_path)
    
    # Build system prompt for structured output
    system_prompt = SYSTEM_PROMPT + """

OUTPUT FORMAT:
You MUST respond with a JSON object containing two fields:
1. "reasoning": A SHORT pre-analysis + construction plan in exactly 6-10 steps.
   - Each line MUST start with "Step k:" (k = 1,2,...).
   - Each step should be ONE sentence, max 18 words.
   - Cover: primitives, constraints, coordinate strategy, construction order, extras.
   - Example format:
     "Step 1: Primitives are five points, three triangle edges, two crossing segments, and labels.
      Step 2: D and E are midpoints of AB and AC respectively, and BE and CD intersect inside.
      Step 3: Place A,B,C at fixed coordinates and compute D,E by 0.5 interpolation (midpoints).
      ..."
2. "tikz_code": The complete TikZ code starting with \\begin{tikzpicture} and ending with \\end{tikzpicture}
"""
    
    # Select user prompt
    if create_variation:
        user_prompt = VARIATION_PROMPT_TEMPLATE
    elif use_in_context_examples:
        # Use dynamic examples randomly sampled from in-context-examples directory
        user_prompt = build_prompt_with_dynamic_examples(n_examples=5)
    else:
        user_prompt = USER_PROMPT_TEMPLATE
    
    # Call API with structured output parsing
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ],
        response_format=TikZGenerationResult,
    )
    
    # Extract parsed response
    result = response.choices[0].message.parsed
    
    # Clean up TikZ code if needed
    if result:
        result.tikz_code = extract_tikz_code(result.tikz_code)
        return result
    
    # Fallback: try to extract from raw content
    response_text = response.choices[0].message.content or ""
    tikz_code = extract_tikz_code(response_text)
    return TikZGenerationResult(reasoning="", tikz_code=tikz_code)


def create_openai_client(backend: str, vllm_url: str) -> OpenAI:
    """Create and return an OpenAI client instance."""
    if backend == "vllm":
        api_key = "EMPTY"
        base_url = vllm_url
    elif backend == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError("OPENAI_API_KEY is not set. Please create a .env file with OPENAI_API_KEY=your_key")
        base_url = "https://api.openai.com/v1"
    else:
        raise ValueError(f"Unknown backend: {backend}")
    return OpenAI(api_key=api_key, base_url=base_url)

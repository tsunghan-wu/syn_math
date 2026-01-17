"""
LLM helper functions for OpenAI Vision API interactions.
"""

import base64
from pathlib import Path
from openai import OpenAI

from prompts import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE_WITH_EXAMPLES,
    VARIATION_PROMPT_TEMPLATE
)


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
) -> str:
    """
    Use OpenAI's vision API to generate TikZ code from an image.
    
    Args:
        client: OpenAI client instance
        image_path: Path to the geometry image
        create_variation: If True, create a variation instead of exact recreation
        model: OpenAI model to use (gpt-4o, gpt-4-vision-preview, etc.)
        use_in_context_examples: If True, include in-context TikZ examples in prompt
    
    Returns:
        TikZ code string
    """
    # Encode image
    base64_image = encode_image_to_base64(image_path)
    media_type = get_image_media_type(image_path)
    
    # Select prompt
    if create_variation:
        user_prompt = VARIATION_PROMPT_TEMPLATE
    elif use_in_context_examples:
        user_prompt = USER_PROMPT_TEMPLATE_WITH_EXAMPLES
    else:
        user_prompt = USER_PROMPT_TEMPLATE
    
    # Call API
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
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
    )
    
    # Extract response
    response_text = response.choices[0].message.content.strip()
    
    # Extract TikZ code
    tikz_code = extract_tikz_code(response_text)
    
    return tikz_code


def create_openai_client(api_key: str) -> OpenAI:
    """Create and return an OpenAI client instance."""
    return OpenAI(api_key="EMPTY", base_url="http://brewster.millennium.berkeley.edu:8000/v1")

"""
Prompts package for geometry image generation and classification.
"""

from .classification import (
    get_category_classification_prompt,
    get_caption_classification_prompt,
    get_classification_prompt,
)

from .tikz import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE_BASE,
    USER_PROMPT_ENDING,
    USER_PROMPT_TEMPLATE,
    IN_CONTEXT_EXAMPLES_SECTION,
    USER_PROMPT_TEMPLATE_WITH_EXAMPLES,
    VARIATION_PROMPT_TEMPLATE,
    TIKZ_EXAMPLES,
    REASONING_SYSTEM_PROMPT,
    get_reasoning_generation_prompt,
)

__all__ = [
    # Classification
    "get_category_classification_prompt",
    "get_caption_classification_prompt",
    "get_classification_prompt",
    # TikZ
    "SYSTEM_PROMPT",
    "USER_PROMPT_TEMPLATE_BASE",
    "USER_PROMPT_ENDING",
    "USER_PROMPT_TEMPLATE",
    "IN_CONTEXT_EXAMPLES_SECTION",
    "USER_PROMPT_TEMPLATE_WITH_EXAMPLES",
    "VARIATION_PROMPT_TEMPLATE",
    "TIKZ_EXAMPLES",
    "REASONING_SYSTEM_PROMPT",
    "get_reasoning_generation_prompt",
]


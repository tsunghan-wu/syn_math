"""
Utils package for geometry TikZ generation.

Two-stage processing:
  - Stage 1 (generate): Generate TikZ code and render images
  - Stage 2 (segment): Generate segmentation annotations for existing outputs
"""

from .args import parse_args
from .llm_helper import (
    create_openai_client,
    generate_tikz_from_image,
    generate_synthetic_segmentation,
    TikZGenerationResult,
    SegmentationAnnotation,
    SegmentationResult,
)
from .image_processor import process_generate, process_segment

__all__ = [
    'parse_args',
    'create_openai_client',
    'generate_tikz_from_image',
    'generate_synthetic_segmentation',
    'TikZGenerationResult',
    'SegmentationAnnotation',
    'SegmentationResult',
    'process_generate',
    'process_segment',
]


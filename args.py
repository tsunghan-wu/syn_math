"""
Argument parsing for geometry image generation.
"""

import argparse
import os


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate TikZ geometry diagrams from images using OpenAI Vision API"
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input", "-i",
        type=str,
        help="Path to a single input image"
    )
    input_group.add_argument(
        "--input-dir", "-d",
        type=str,
        help="Directory containing input images"
    )
    
    # Output options
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="./generated_output",
        help="Output directory for generated images (default: ./generated_output)"
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=None,
        help="Number of images to generate (for --input-dir mode)"
    )
    
    # API options
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="OpenAI API key (or set OPENAI_API_KEY env var)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5-mini",
        choices=["gpt-5-mini"],
        help="OpenAI model to use (default: gpt-5-mini)"
    )
    
    # Generation options
    parser.add_argument(
        "--variation",
        action="store_true",
        help="Generate variations instead of exact recreations"
    )
    parser.add_argument(
        "--save-tex",
        action="store_true",
        help="Save TikZ source code alongside PNG files"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for PNG output (default: 300)"
    )
    parser.add_argument(
        "--no-masks",
        action="store_true",
        help="Skip generating segmentation masks"
    )
    
    return parser.parse_args()


def get_api_key(args) -> str:
    """Get API key from args or environment."""
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    return api_key


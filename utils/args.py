# Configuration
JSONL_FILE = "image_classifications_01102026.jsonl"
IMAGE_ROOT = "/home/annelee/datasets/OpenMMReasoner-SFT-874K/sft_image"
OUTPUT_DIR = "function_graph_01182026_v4"
DEFAULT_COUNT = 50

import argparse

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run geometry image generation")
    # Input dir and output dir
    parser.add_argument("--jsonl-file", "-j", type=str, default=JSONL_FILE,
                        help=f"JSONL file (default: {JSONL_FILE})")
    parser.add_argument("--input-dir", "-i", type=str, default=IMAGE_ROOT,
                        help=f"Input directory (default: {IMAGE_ROOT})")
    parser.add_argument("--output", "-o", type=str, default=OUTPUT_DIR,
                        help=f"Output directory (default: {OUTPUT_DIR})")
    # Backend and model
    parser.add_argument("--backend", type=str, default="vllm", choices=["vllm", "openai"],
                        help="Backend to use for generation (default: vllm)")
    parser.add_argument("--vllm-url", type=str, default="http://brewster.millennium.berkeley.edu:8000/v1",
                        help="vLLM server URL (default: http://brewster.millennium.berkeley.edu:8000/v1)")
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-VL-235B-A22B-Instruct",
                        help="OpenAI model to use (default: Qwen/Qwen3-VL-235B-A22B-Instruct)")
    # Generation options
    parser.add_argument("--variation", action="store_true",
                        help="Generate variations instead of recreations")
    parser.add_argument("--in-context-examples", action="store_true",
                        help="Include in-context TikZ examples in prompt for few-shot learning")
    parser.add_argument("--count", "-n", type=int, default=DEFAULT_COUNT,
                        help=f"Number of images to process (default: {DEFAULT_COUNT})")
    # Rendering options
    parser.add_argument("--dpi", type=int, default=300,
                        help="DPI for output images (default: 300)")
    parser.add_argument("--shuffle", action="store_true",
                        help="Randomly shuffle images before selecting")
    args = parser.parse_args()
    return args
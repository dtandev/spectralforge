"""
SpectralForge
TODO: One-sentence description of what this script does — no processing logic exists yet.

Usage:
    python src/main.py --help
    python src/main.py --input <path> --output <path>
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TODO: describe what this script does",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py --input data/input/sample.tif --output data/output/
  python src/main.py --input data/input/ --output data/output/ --verbose
        """,
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to input file or directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to output directory",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    # TODO: add additional arguments specific to this product

    return parser.parse_args()


def run(input_path: Path, output_path: Path) -> None:
    """
    Main processing logic.

    Args:
        input_path: Path to the input file or directory.
        output_path: Path to the output directory.
    """
    logger.info(f"Processing: {input_path}")
    output_path.mkdir(parents=True, exist_ok=True)

    # TODO: implement spectral data processing logic here — no source code
    # existed in this repo before /scaffold generated this placeholder.
    raise NotImplementedError("Implement your processing logic in run()")


def main() -> int:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        run(args.input, args.output)
        logger.info("Done.")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

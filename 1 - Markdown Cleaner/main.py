"""
Markdown Cleaner CLI — Phase 1
Removes code blocks and tables from a markdown file.

Usage:
    python main.py
    python main.py --input myfile.md
    python main.py --input myfile.md --output-dir results
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from parser import parse_and_clean


# ─── Constants ────────────────────────────────────────────────────────
DEFAULT_INPUT_FILENAME = "input.md"
DEFAULT_OUTPUT_DIR = "output"
OUTPUT_PREFIX = "cleaned"


def get_base_dir() -> Path:
    """
    Get the directory where the executable (or script) lives.
    Works both when running as .py and as compiled .exe (PyInstaller).
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled exe (PyInstaller)
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent


def generate_output_filename() -> str:
    """Generate a unique filename with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{OUTPUT_PREFIX}_{timestamp}.md"


def setup_cli() -> argparse.Namespace:
    """Setup command line argument parser."""
    base = get_base_dir()

    cli = argparse.ArgumentParser(
        prog="md-cleaner",
        description="Remove code blocks and tables from Markdown files.",
        epilog="Output files are saved in the output directory with timestamps.",
    )

    cli.add_argument(
        "-i", "--input",
        type=str,
        default=str(base / DEFAULT_INPUT_FILENAME),
        help=f"Path to input markdown file (default: {DEFAULT_INPUT_FILENAME})",
    )

    cli.add_argument(
        "-o", "--output-dir",
        type=str,
        default=str(base / DEFAULT_OUTPUT_DIR),
        help=f"Path to output directory (default: {DEFAULT_OUTPUT_DIR})",
    )

    cli.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed information about removed elements",
    )

    return cli.parse_args()


def main() -> int:
    """Main entry point."""
    args = setup_cli()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    # ── Validate input ────────────────────────────────────────────
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        print(f"        Place your markdown file as '{DEFAULT_INPUT_FILENAME}' "
              f"next to this program.")
        return 1

    if not input_path.is_file():
        print(f"[ERROR] Input path is not a file: {input_path}")
        return 1

    # ── Read input ────────────────────────────────────────────────
    print(f"[INFO]  Reading: {input_path}")
    try:
        content = input_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fallback for files with different encoding
        content = input_path.read_text(encoding="utf-8-sig")

    if not content.strip():
        print("[WARN]  Input file is empty.")
        return 0

    # ── Parse and clean ───────────────────────────────────────────
    result = parse_and_clean(content)

    print(f"[INFO]  Found {result.code_block_count} code block(s)")
    print(f"[INFO]  Found {result.table_count} table(s)")

    if args.verbose:
        for i, block in enumerate(result.removed_code_blocks, 1):
            preview = block[:80].replace('\n', '\\n')
            print(f"        Code block #{i}: {preview}...")
        for i, table in enumerate(result.removed_tables, 1):
            preview = table[:80].replace('\n', '\\n')
            print(f"        Table #{i}: {preview}...")

    # ── Write output ──────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)

    output_filename = generate_output_filename()
    output_path = output_dir / output_filename

    output_path.write_text(result.cleaned_text, encoding="utf-8")

    print(f"[INFO]  Output saved: {output_path}")
    print("[DONE]  Cleaning complete.")

    return 0


if __name__ == "__main__":
    sys.exit(main())


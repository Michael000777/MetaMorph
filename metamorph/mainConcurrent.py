from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

try:
    from metamorph.core import DEFAULT_OUTDIR, run_MetaMorph_on_csv
except ModuleNotFoundError:
    # Support the documented direct script form:
    # `python metamorph/mainConcurrent.py ...`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from metamorph.core import DEFAULT_OUTDIR, run_MetaMorph_on_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run MetaMorph concurrently on a dataset and generate a report."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to CSV file to process.",
    )
    parser.add_argument(
        "--dataset-id",
        "-d",
        help="Optional dataset identifier. Defaults to the input filename stem.",
    )
    parser.add_argument(
        "--outdir",
        "-o",
        default=DEFAULT_OUTDIR,
        help=f"Output directory for the generated report files. Defaults to {DEFAULT_OUTDIR}/.",
    )
    parser.add_argument(
        "--llm",
        "-l",
        type=str,
        default="gpt-5-nano",
        help="OpenAI LLM model to use.",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=2,
        help="Maximum number of columns to process concurrently.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_MetaMorph_on_csv(
        input_path=args.input,
        outdir=args.outdir,
        dataset_id=args.dataset_id,
        llm=args.llm,
        max_concurrency=args.max_concurrency,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

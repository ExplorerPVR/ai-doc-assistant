"""Customer reviews CSV cleaning script with deduplication and retry mechanism."""

import argparse
import csv
import functools
import logging
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("clean_reviews")


def retry(
    times: int = 3,
    delay: float = 0.5,
    exceptions: tuple[type[Exception], ...] = (OSError,),
) -> Callable[[F], F]:
    """Decorator factory that retries an operation when listed exceptions occur."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_err: Exception | None = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as err:
                    last_err = err
                    err_cls = type(err).__name__
                    logger.warning(
                        f"Attempt {attempt}/{times} for '{func.__name__}' "
                        f"failed with {err_cls}: {err}"
                    )
                    if attempt == times:
                        logger.error(
                            f"Final attempt {times} failed for '{func.__name__}'."
                        )
                        raise
                    if delay > 0:
                        time.sleep(delay)
            if last_err is not None:
                raise last_err

        return wrapper  # type: ignore[return-value]

    return decorator


def clean_rows(
    rows: list[list[str]],
) -> tuple[list[list[str]], dict[str, int]]:
    """Clean CSV rows by removing blank rows and duplicates while preserving order."""
    stats = {
        "rows_read": 0,
        "empty_removed": 0,
        "duplicates_removed": 0,
        "rows_written": 0,
    }

    if not rows:
        return [], stats

    # Keep header row as-is
    header = [cell.strip() for cell in rows[0]]
    cleaned: list[list[str]] = [header]

    seen_signatures: set[tuple[str, ...]] = set()

    # Process all data rows following header
    for raw_row in rows[1:]:
        stats["rows_read"] += 1
        stripped = [cell.strip() for cell in raw_row]

        # Check if every field in the row is empty or pure whitespace
        if all(cell == "" for cell in stripped):
            stats["empty_removed"] += 1
            continue

        # Check for duplicate row based on stripped field values
        signature = tuple(stripped)
        if signature in seen_signatures:
            stats["duplicates_removed"] += 1
            continue

        seen_signatures.add(signature)
        cleaned.append(stripped)

    stats["rows_written"] = len(cleaned)
    return cleaned, stats


@retry(times=3, delay=0.5, exceptions=(OSError,))
def read_csv(path: Path) -> list[list[str]]:
    """Read a CSV file as UTF-8 and return rows as lists of string fields."""
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open(mode="r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        return list(reader)


@retry(times=3, delay=0.5, exceptions=(OSError,))
def write_csv(path: Path, rows: list[list[str]]) -> None:
    """Write cleaned CSV rows to destination path in UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def run_clean_reviews(input_path: Path, output_path: Path) -> dict[str, int]:
    """Execute reading, cleaning, writing, and print/log the summary stats."""
    rows = read_csv(input_path)
    cleaned, stats = clean_rows(rows)
    write_csv(output_path, cleaned)

    summary_msg = (
        f"Rows read: {stats['rows_read']}, "
        f"empty rows removed: {stats['empty_removed']}, "
        f"duplicates removed: {stats['duplicates_removed']}, "
        f"rows written: {stats['rows_written']}"
    )
    logger.info(summary_msg)
    print(summary_msg)
    return stats


def main() -> None:
    """CLI entrypoint supporting flags, positional args, and defaults."""
    parser = argparse.ArgumentParser(
        description="Clean messy customer reviews CSV by dropping empty rows."
    )
    parser.add_argument(
        "positional_args",
        nargs="*",
        help="Optional positional arguments: <input_path> <output_path>",
    )
    parser.add_argument(
        "--input",
        "-i",
        dest="input_flag",
        type=Path,
        default=None,
        help="Path to input CSV file (default: data/messy_reviews.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output_flag",
        type=Path,
        default=None,
        help="Path to output CSV file (default: data/clean_reviews.csv)",
    )
    args = parser.parse_args()

    # Determine input and output paths
    if args.input_flag:
        input_path = args.input_flag
    elif args.positional_args and len(args.positional_args) >= 1:
        input_path = Path(args.positional_args[0])
    else:
        input_path = Path("data/messy_reviews.csv")

    if args.output_flag:
        output_path = args.output_flag
    elif args.positional_args and len(args.positional_args) >= 2:
        output_path = Path(args.positional_args[1])
    else:
        output_path = Path("data/clean_reviews.csv")

    try:
        run_clean_reviews(input_path, output_path)
    except FileNotFoundError as err:
        logger.error(f"Input file error: {err}")
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        logger.error(f"Execution failed: {err}")
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Unit tests for customer reviews CSV cleaning script and retry decorator."""

from pathlib import Path

import pytest

from scripts.clean_reviews import (
    clean_rows,
    read_csv,
    retry,
    run_clean_reviews,
)


def test_empty_and_whitespace_rows_are_removed() -> None:
    """Test 1: Verify empty and whitespace-only rows are dropped from data."""
    rows = [
        ["id", "name", "rating", "review"],
        ["1", "Alice", "5", "Great product!"],
        ["", "", "", ""],
        ["   ", "\t", "  ", ""],
        ["2", "Bob", "4", "Fast delivery."],
    ]
    cleaned, stats = clean_rows(rows)
    assert stats["rows_read"] == 4
    assert stats["empty_removed"] == 2
    assert stats["duplicates_removed"] == 0
    assert stats["rows_written"] == 3
    assert len(cleaned) == 3
    assert cleaned[1] == ["1", "Alice", "5", "Great product!"]
    assert cleaned[2] == ["2", "Bob", "4", "Fast delivery."]


def test_duplicate_rows_are_removed_and_first_is_kept() -> None:
    """Test 2: Verify duplicate rows are eliminated and first instance is preserved."""
    rows = [
        ["id", "name", "rating", "review"],
        ["1", "Alice", "5", "Great product!"],
        ["2", "Bob", "4", "Fast delivery."],
        ["1", "Alice", "5", "Great product!"],
    ]
    cleaned, stats = clean_rows(rows)
    assert stats["rows_read"] == 3
    assert stats["duplicates_removed"] == 1
    assert stats["rows_written"] == 3
    assert cleaned[1] == ["1", "Alice", "5", "Great product!"]
    assert cleaned[2] == ["2", "Bob", "4", "Fast delivery."]


def test_surrounding_whitespace_duplicates_are_removed() -> None:
    """Test 3: Verify whitespace-padded rows count as duplicates."""
    rows = [
        ["id", "name", "rating", "review"],
        ["1", "Alice", "5", "Great product!"],
        ["  1  ", " Alice ", " 5 ", " Great product!  "],
        ["3", "Charlie", "3", "Average"],
    ]
    cleaned, stats = clean_rows(rows)
    assert stats["rows_read"] == 3
    assert stats["duplicates_removed"] == 1
    assert stats["rows_written"] == 3
    assert cleaned[1] == ["1", "Alice", "5", "Great product!"]
    assert cleaned[2] == ["3", "Charlie", "3", "Average"]


def test_already_clean_file_comes_back_unchanged(tmp_path: Path) -> None:
    """Test 4: Verify an already clean CSV file produces identical clean output."""
    input_file = tmp_path / "clean_input.csv"
    output_file = tmp_path / "clean_output.csv"

    content = "id,name,rating,review\n1,Alice,5,Loved it\n2,Bob,4,Good\n"
    input_file.write_text(content, encoding="utf-8")

    stats = run_clean_reviews(input_file, output_file)
    assert stats["rows_read"] == 2
    assert stats["empty_removed"] == 0
    assert stats["duplicates_removed"] == 0
    assert stats["rows_written"] == 3
    assert output_file.read_text(encoding="utf-8").replace("\r\n", "\n") == content


def test_file_with_only_header_produces_only_header(tmp_path: Path) -> None:
    """Test 5: Verify a CSV containing only a header outputs only the header."""
    input_file = tmp_path / "header_only.csv"
    output_file = tmp_path / "header_out.csv"

    content = "id,name,rating,review\n"
    input_file.write_text(content, encoding="utf-8")

    stats = run_clean_reviews(input_file, output_file)
    assert stats["rows_read"] == 0
    assert stats["empty_removed"] == 0
    assert stats["duplicates_removed"] == 0
    assert stats["rows_written"] == 1
    assert output_file.read_text(encoding="utf-8").replace("\r\n", "\n") == content


def test_missing_input_file_raises_error_after_retries(tmp_path: Path) -> None:
    """Test 6: Verify non-existent file triggers retries and ultimately raises error."""
    missing_file = tmp_path / "does_not_exist.csv"
    with pytest.raises(FileNotFoundError):
        read_csv(missing_file)


def test_retry_decorator_succeeds_after_transient_failure() -> None:
    """Test 7: Verify retry decorator succeeds when failure resolves."""
    call_count = 0

    @retry(times=3, delay=0, exceptions=(OSError,))
    def flaky_operation() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("Temporary I/O glitch")
        return "success"

    result = flaky_operation()
    assert result == "success"
    assert call_count == 2


def test_messy_sample_csv_end_to_end(tmp_path: Path) -> None:
    """End-to-end test on a messy CSV with blanks, duplicates, and padding."""
    input_file = tmp_path / "messy.csv"
    output_file = tmp_path / "messy_clean.csv"

    csv_data = (
        "id,customer_name,rating,comment\n"
        "101,  John Doe , 5 , Excellent service! \n"
        ",,,\n"
        "102,Jane Smith,4,Solid quality\n"
        "   ,   ,   ,   \n"
        "101,John Doe,5,Excellent service!\n"
        "103, Bob Vance ,2,Slow delivery\n"
    )
    input_file.write_text(csv_data, encoding="utf-8")

    stats = run_clean_reviews(input_file, output_file)
    assert stats["rows_read"] == 6
    assert stats["empty_removed"] == 2
    assert stats["duplicates_removed"] == 1
    assert stats["rows_written"] == 4

    clean_content = output_file.read_text(encoding="utf-8").replace("\r\n", "\n")
    expected = (
        "id,customer_name,rating,comment\n"
        "101,John Doe,5,Excellent service!\n"
        "102,Jane Smith,4,Solid quality\n"
        "103,Bob Vance,2,Slow delivery\n"
    )
    assert clean_content == expected

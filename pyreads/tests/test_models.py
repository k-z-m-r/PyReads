"""Tests for the _models module with Pydantic data models."""

from datetime import UTC, datetime
from typing import Any

import pytest
from pandas import DataFrame

from pyreads.models import Book, Library, Series

# --- Fixtures -----------------------------------------------------------------


@pytest.fixture
def example_series() -> Series:
    return Series(name="The Example Series", number=2)


@pytest.fixture
def example_book(example_series: Series) -> Book:
    return Book(
        title="Example Book",
        authorName="John Doe",
        numberOfPages=300,
        dateRead=datetime(2025, 8, 20, tzinfo=UTC),
        userRating=5,
        review="Great book!",
        series=example_series,
    )


@pytest.fixture
def example_book_no_series() -> Book:
    return Book(
        title="Standalone Book",
        authorName="Jane Doe",
        numberOfPages=150,
        dateRead=datetime(2025, 8, 19, tzinfo=UTC),
        userRating=4,
    )


@pytest.fixture
def example_library(
    example_book: Book, example_book_no_series: Book
) -> Library:
    return Library(owner=1, books=[example_book, example_book_no_series])


# --- Series Tests -------------------------------------------------------------


def test_series_str(example_series: Series) -> None:
    assert str(example_series) == "(The Example Series, #2)"


# --- Book Tests ---------------------------------------------------------------


def test_book_full_title_with_series(example_book: Book) -> None:
    expected: str = "Example Book (The Example Series, #2) by John Doe"
    assert example_book.full_title == expected


def test_book_full_title_without_series(example_book_no_series: Book) -> None:
    expected: str = "Standalone Book by Jane Doe"
    assert example_book_no_series.full_title == expected


# --- Library Tests ------------------------------------------------------------


def test_library_dataframe(
    example_library: Library,
    example_book: Book,
) -> None:
    df: DataFrame = example_library.dataframe

    # Check type
    assert isinstance(df, DataFrame)

    # Check correct number of rows
    assert len(df) == 2

    # Check that first row matches first book data
    first_row: dict[str, Any] = df.iloc[0].to_dict()
    for field in [
        "title",
        "authorName",
        "numberOfPages",
        "userRating",
        "review",
    ]:
        assert first_row[field] == getattr(example_book, field)

    # Check that series is represented as dict in dataframe
    assert example_book.series
    assert isinstance(first_row["series"], dict)
    assert first_row["series"]["name"] == example_book.series.name
    assert first_row["series"]["number"] == example_book.series.number

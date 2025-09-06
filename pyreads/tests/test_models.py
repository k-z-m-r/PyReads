"""Tests for the _models module with Pydantic data models."""

from datetime import date
from typing import Any

import pytest

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
        dateRead=date(
            2025,
            8,
            20,
        ),
        userRating=5,
        userReview="Great book!",
        series=example_series,
    )


@pytest.fixture
def example_book_no_series() -> Book:
    return Book(
        title="Standalone Book",
        authorName="Jane Doe",
        numberOfPages=150,
        dateRead=date(
            2025,
            8,
            19,
        ),
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
    df = example_library.dataframe

    # Check correct number of rows
    assert len(df) == 2

    # Check that first row matches first book data
    first_row: dict[str, Any] = df.iloc[0].to_dict()

    # Map titles back to model attributes
    field_map = {
        "Title": "title",
        "Author Name": "authorName",
        "Number of Pages": "numberOfPages",
        "Date Read": "dateRead",
        "User Rating": "userRating",
        "User Review": "userReview",
        "Series": "series",
    }

    for col_title, attr in field_map.items():
        expected_value = getattr(example_book, attr)
        if attr == "series" and expected_value is not None:
            # Series should be preserved as dict-like object in DataFrame
            assert isinstance(first_row[col_title], dict)
            assert first_row[col_title]["name"] == expected_value.name
            assert first_row[col_title]["number"] == expected_value.number
        else:
            assert first_row[col_title] == expected_value

"""Tests for the _models module with Pydantic data models."""

from datetime import date
from typing import Any

from pytest import fixture, raises

from pyreads.models import Book, Library

# --- Fixtures -----------------------------------------------------------------


@fixture
def example_book() -> Book:
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
        seriesName="The Example Series",
        seriesEntry="2",
    )


@fixture
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


@fixture
def example_library(
    example_book: Book, example_book_no_series: Book
) -> Library:
    return Library(userId=1, books=[example_book, example_book_no_series])


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
        "Series Name": "seriesName",
        "Series Entry": "seriesEntry",
    }

    for col_title, attr in field_map.items():
        expected_value = getattr(example_book, attr)
        assert first_row[col_title] == expected_value


# --- Series Name and Entry Validation Tests -----------------------------------
def test_series_name_and_entry_validation() -> None:
    """Test validation for seriesName and seriesEntry fields."""

    required_attrs = {
        "title": "",
        "authorName": "",
        "numberOfPages": 1,
        "dateRead": date(
            2025,
            8,
            20,
        ),
        "userRating": 0,
    }
    # Case 1: Both seriesName and seriesEntry are provided (valid case)
    model = Book(**required_attrs, seriesName="Series A", seriesEntry="1")  # type: ignore
    assert model is not None

    # Case 2: Only seriesName is provided (invalid case)
    with raises(
        ValueError,
        match="seriesName and seriesEntry must be provided together.",
    ):
        Book(**required_attrs, seriesName="Series A", seriesEntry=None)  # type: ignore

    # Case 3: Only seriesEntry is provided (invalid case)
    with raises(
        ValueError,
        match="seriesName and seriesEntry must be provided together.",
    ):
        Book(**required_attrs, seriesName=None, seriesEntry="1")  # type: ignore

    # Case 4: Neither seriesName nor seriesEntry is provided (valid case)
    model = Book(**required_attrs, seriesName=None, seriesEntry=None)  # type: ignore
    assert model is not None

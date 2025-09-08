"""Tests for the _http module."""

from collections.abc import Generator

from httpx import Client, HTTPStatusError
from pytest import fixture, raises

from pyreads._http import _fetch_books_page, _fetch_html, _format_goodreads_url
from pyreads.models import Book

# --- Fixtures -----------------------------------------------------------------


@fixture
def mock_client() -> Generator[Client, None, None]:
    """Create a mock HTTPX client."""
    with Client() as client:
        yield client


# --- _format_goodreads_url Tests ---------------------------------------------


def test_format_goodreads_url() -> None:
    """Test URL formatting for Goodreads shelf."""
    user_id = 12345
    page = 2
    expected_url = (
        "https://www.goodreads.com/review/list/12345?page=2&shelf=read"
    )
    assert _format_goodreads_url(user_id, page) == expected_url


# --- _fetch_html Tests -------------------------------------------------------


def test_fetch_html_success(mock_client: Client) -> None:
    """Test successful HTML fetch."""
    url = "https://example.com"
    resp = _fetch_html(mock_client, url)
    assert resp


def test_fetch_html_failure(mock_client: Client) -> None:
    """Test successful HTML fetch."""
    url = "https://example.com/bad"

    with raises(HTTPStatusError, match=f"404 Error: {url}"):
        _fetch_html(mock_client, url)


# --- _fetch_books_page Tests -------------------------------------------------


def test_fetch_books_page(mock_client: Client) -> None:
    """Test fetching and parsing books from a Goodreads page."""
    user_id = 12345
    page = 1

    books = _fetch_books_page(mock_client, user_id, page)
    assert isinstance(books, list)
    assert all(isinstance(book, Book) for book in books)

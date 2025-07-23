"""Core functionality for PyReads, which includes fetching a user's library."""

import concurrent.futures
import re
from os import cpu_count
from typing import Any

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag
from pydantic import ValidationError

from pyreads._models import Book, Library
from pyreads._parser import (
    _PARSERS,
)

# --------------------
# Internal HTTP Helpers
# --------------------


def _format_goodreads_url(user_id: int, page: int = 1) -> str:
    return f"https://www.goodreads.com/review/list/{user_id}?page={page}&shelf=read"


def _get_goodreads_html(client: httpx.Client, url: str) -> str:
    """
    Internal: Sends a GET request and returns the response text, or raises ValueError on error.
    """
    response = client.get(url)
    if response.status_code == 200:
        return response.text
    raise ValueError(f"{response.status_code} Error: {response.url}")


def _fetch_page(client: httpx.Client, user_id: int, page: int) -> list[Book]:
    """
    Internal: Fetches a single Goodreads page and parses books from HTML.
    """
    url = _format_goodreads_url(user_id, page)
    html = _get_goodreads_html(client, url)
    return _parse_goodreads_html(html)


# --------------------
# Internal HTML Parsing
# --------------------
def _parse_goodreads_html(html: str) -> list[Book]:
    """
    Internal: Parses Goodreads shelf HTML and returns a list of Book objects.
    """

    soup = BeautifulSoup(html, "html.parser")
    review_trs = soup.find_all("tr", id=re.compile(r"^review_"))
    books = []

    for tr in review_trs:
        assert isinstance(tr, Tag)
        attributes: dict[str, Any] = {}
        for attribute, parser in _PARSERS.items():
            value = parser.parse(tr)
            attributes[attribute] = value

        try:
            book = Book(**attributes)
        except ValidationError:
            continue
        else:
            books.append(book)

    return books


# --------------------
# Public API
# --------------------
def get_library(user_id: int) -> Library:
    """
    Fetches the complete Goodreads library for a user.

    Args:
        user_id: The Goodreads user ID.

    Returns:
        Library: A Library object containing all books read by the user.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    books = []
    with httpx.Client(headers=headers, follow_redirects=True, timeout=10) as client:
        # Fetch first page
        first_url = _format_goodreads_url(user_id, 1)
        first_html = _get_goodreads_html(client, first_url)
        books += _parse_goodreads_html(first_html)

        # Determine total number of pages
        soup = BeautifulSoup(first_html, "html.parser")
        pagination_div = soup.find("div", id="reviewPagination")
        page_links = pagination_div.find_all("a") if pagination_div else []
        page_numbers = [int(a.text) for a in page_links if a.text.isdigit()]
        total_pages = max(page_numbers) if page_numbers else 1

        # Fetch remaining pages concurrently
        cpus = cpu_count() or 1
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(32, cpus * 5)
        ) as executor:
            futures = [
                executor.submit(_fetch_page, client, user_id, page)
                for page in range(2, total_pages + 1)
            ]
            for future in concurrent.futures.as_completed(futures):
                books += future.result()

    return Library(owner=user_id, books=books)

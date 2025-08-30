"""Internal HTML helpers for PyReads"""

from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

from ._http import _fetch_html, _format_goodreads_url
from ._parser import _parse_row
from .models import Book


def _parse_books_from_html(html: str) -> list[Book]:
    """
    Parses Goodreads shelf HTML and returns a list of Book objects.
    """
    soup = BeautifulSoup(html, "html.parser")
    review_trs = soup.find_all("tr", id=re.compile(r"^review_"))
    books = []
    for tr in review_trs:
        assert isinstance(tr, Tag)
        attributes = _parse_row(tr)
        if attributes["dateRead"] is not None:
            book = Book.model_validate(attributes)
            books.append(book)
    return books


def _fetch_books_page(client: httpx.Client, user_id: int, page: int) -> list[Book]:
    """
    Fetches a single Goodreads page and parses books from HTML.
    """
    url = _format_goodreads_url(user_id, page)
    html = _fetch_html(client, url)
    return _parse_books_from_html(html)

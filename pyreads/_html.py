"""Internal HTML helpers for PyReads"""

from __future__ import annotations

import re
from warnings import warn

from bs4 import BeautifulSoup
from bs4.element import Tag
from httpx import Client
from pydantic import ValidationError

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
        try:
            book = Book.model_validate(attributes)
        except ValidationError as exc:
            warn(str(exc), stacklevel=1)
        else:
            books.append(book)
    return books


def _fetch_books_page(client: Client, user_id: int, page: int) -> list[Book]:
    """
    Fetches a single Goodreads page and parses books from HTML.
    """
    url = _format_goodreads_url(user_id, page)
    html = _fetch_html(client, url)
    return _parse_books_from_html(html)

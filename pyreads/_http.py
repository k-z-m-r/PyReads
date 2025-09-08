"""Internal HTTP utilities for PyReads."""

from httpx import Client, HTTPStatusError

from ._parser import _parse_books_from_html
from .models import Book


def _format_goodreads_url(user_id: int, page: int = 1) -> str:
    """
    Returns the Goodreads shelf URL for a given user and page.
    """
    return f"https://www.goodreads.com/review/list/{user_id}?page={page}&shelf=read"


def _fetch_html(client: Client, url: str) -> str:
    """
    Sends a GET request and returns the response text
    """
    response = client.get(url)
    if response.status_code == 200:
        return response.text

    err = f"{response.status_code} Error: {response.url}"
    raise HTTPStatusError(
        message=err, request=response.request, response=response
    )


def _fetch_books_page(client: Client, user_id: int, page: int) -> list[Book]:
    """
    Fetches a single Goodreads page and parses books from HTML.
    """
    url = _format_goodreads_url(user_id, page)
    html = _fetch_html(client, url)
    return _parse_books_from_html(html)

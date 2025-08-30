"""Core functionality for PyReads, which includes fetching a user's library."""

import concurrent.futures
from os import cpu_count

from bs4 import BeautifulSoup
from httpx import Client

from ._html import _fetch_books_page, _parse_books_from_html
from ._http import _fetch_html, _format_goodreads_url
from .models import Library


def fetch_goodreads_library(user_id: int) -> Library:
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
    with Client(headers=headers, follow_redirects=True, timeout=10) as client:
        # Fetch first page
        first_url = _format_goodreads_url(user_id, 1)
        first_html = _fetch_html(client, first_url)
        books += _parse_books_from_html(first_html)

        soup = BeautifulSoup(first_html, "html.parser")
        pagination_div = soup.find("div", id="reviewPagination")
        page_links = (
            pagination_div.find_all("a")
            if pagination_div and hasattr(pagination_div, "find_all")
            else []
        )
        page_numbers = [int(a.text) for a in page_links if a.text.isdigit()]
        total_pages = max(page_numbers) if page_numbers else 1

        # Fetch remaining pages concurrently
        cpus = cpu_count() or 1
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(32, cpus * 5)
        ) as executor:
            futures = [
                executor.submit(_fetch_books_page, client, user_id, page)
                for page in range(2, total_pages + 1)
            ]
            for future in concurrent.futures.as_completed(futures):
                books += future.result()

    return Library(owner=user_id, books=books)

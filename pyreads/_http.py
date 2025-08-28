"""Internal HTTP utilities for PyReads."""

import httpx


def _format_goodreads_url(user_id: int, page: int = 1) -> str:
    """
    Returns the Goodreads shelf URL for a given user and page.
    """
    return f"https://www.goodreads.com/review/list/{user_id}?page={page}&shelf=read"


def _fetch_html(client: httpx.Client, url: str) -> str:
    """
    Sends a GET request and returns the response text, or raises ValueError on error.
    """
    response = client.get(url)
    if response.status_code == 200:
        return response.text
    raise ValueError(f"{response.status_code} Error: {response.url}")

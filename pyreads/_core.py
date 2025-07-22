"""Core functionality for PyReads, which includes fetching a user's library."""

import concurrent.futures
import re
from os import cpu_count

import httpx
from bs4 import BeautifulSoup

from ._utilities import STRING_TO_RATING, Rating, format_url, parse_date
from .models import Book, Library


def get_response(client: httpx.Client, url: str) -> str:
    response = client.get(url)
    if response.status_code == 200:
        return response.text
    elif response.status_code == 404:
        raise ValueError(f"404 Not Found: {response.url}")
    else:
        raise ValueError(f"Unexpected status: {response.status_code}")


def extract_books_from_html(html: str) -> list[Book]:
    soup = BeautifulSoup(html, "html.parser")
    review_trs = soup.find_all("tr", id=re.compile(r"^review_"))
    data = []
    for tr in review_trs:
        date_span = tr.find("span", class_="date_read_value")
        date_str = date_span.get_text(strip=True) if date_span else None
        date_read = parse_date(date_str) if date_str else None

        review_span = tr.find("span", id=re.compile(r"^freeTextContainerreview"))
        review_text = review_span.get_text(strip=True) if review_span else None

        author_td = tr.find("td", class_="field author")
        author_a = author_td.find("a") if author_td else None
        author_name = author_a.get_text(strip=True) if author_a else None

        title_td = tr.find("td", class_="field title")
        title_a = title_td.find("a") if title_td else None
        series = None
        series_number = None
        title = None
        if title_a:
            title_text = (
                title_a.contents[0].strip()
                if title_a.contents
                else title_a.get_text(strip=True)
            )
            series_span = title_a.find("span", class_="darkGreyText")
            if series_span:
                series_info = series_span.get_text(strip=True)
                match = re.match(r"\((.*),\s*#(\d+)\)", series_info)
                if match:
                    series = match.group(1)
                    series_number = int(match.group(2))
            title = title_text

        rating_td = tr.find("td", class_="field rating")
        rating_span = (
            rating_td.find("span", class_="staticStars") if rating_td else None
        )
        rating_text = (
            rating_span.get("title")
            if rating_span and rating_span.has_attr("title")
            else None
        )
        rating = STRING_TO_RATING.get(rating_text, Rating.NO_RATING)

        if author_name and title and date_read is not None:
            book = Book(
                authorName=author_name,
                title=title,
                dateRead=date_read,
                userRating=rating,
                review=review_text,
                series=series,
                seriesNumber=series_number,
            )
            data.append(book)
    return data


def fetch_page(client: httpx.Client, user_id: int, page: int) -> list[Book]:
    url = format_url(user_id, page)
    html = get_response(client, url)
    return extract_books_from_html(html)


def get_library(user_id: int) -> Library:
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
        first_url = format_url(user_id, 1)
        first_html = get_response(client, first_url)
        books += extract_books_from_html(first_html)

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
                executor.submit(fetch_page, client, user_id, page)
                for page in range(2, total_pages + 1)
            ]
            for future in concurrent.futures.as_completed(futures):
                books += future.result()

    return Library(owner=user_id, books=books)

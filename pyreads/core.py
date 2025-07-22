"""Core functionality for PyReads, which includes fetching a user's library."""

import re
from calendar import monthrange
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .models import Book
from .utilities import STRING_TO_RATING


def parse_date(date_str):
    for fmt in ("%b %d, %Y", "%b %Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            if fmt == "%b %Y":
                # Set to last day of the month
                last_day = monthrange(dt.year, dt.month)[1]
                dt = dt.replace(day=last_day)
            return dt
        except Exception:
            continue
    return None


def format_url(user_id: int, page: int = 1):
    url = f"https://www.goodreads.com/review/list/{user_id}?page={page}&shelf=read"
    return url


def get_response(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        response = client.get(url)
        if response.status_code == 200:
            return response.text
        elif response.status_code == 404:
            raise ValueError(f"404 Not Found: {response.url}")
        else:
            raise ValueError(f"Unexpected status: {response.status_code}")


def extract_books_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    review_trs = soup.find_all("tr", id=re.compile(r"^review_"))
    data = []
    for tr in review_trs:
        # Date extraction
        date_span = tr.find("span", class_="date_read_value")
        date_str = date_span.get_text(strip=True) if date_span else None
        date_read = parse_date(date_str) if date_str else None

        # Review extraction
        review_span = tr.find("span", id=re.compile(r"^freeTextContainerreview"))
        review_text = review_span.get_text(strip=True) if review_span else None

        # Author extraction
        author_td = tr.find("td", class_="field author")
        author_a = author_td.find("a") if author_td else None
        author_name = author_a.get_text(strip=True) if author_a else None

        # Title and Series extraction
        title_td = tr.find("td", class_="field title")
        title_a = title_td.find("a") if title_td else None
        series = None
        series_number = None
        title = None
        if title_a:
            # Extract title text (excluding series)
            title_text = (
                title_a.contents[0].strip()
                if title_a.contents
                else title_a.get_text(strip=True)
            )
            # Extract series if present
            series_span = title_a.find("span", class_="darkGreyText")
            if series_span:
                series_info = series_span.get_text(strip=True)
                # Example: "(The Stormlight Archive, #1)"
                match = re.match(r"\((.*),\s*#(\d+)\)", series_info)
                if match:
                    series = match.group(1)
                    series_number = int(match.group(2))
            title = title_text

        # Rating extraction
        rating_td = tr.find("td", class_="field rating")
        rating_span = (
            rating_td.find("span", class_="staticStars") if rating_td else None
        )
        rating_text = (
            rating_span.get("title")
            if rating_span and rating_span.has_attr("title")
            else None
        )
        rating = STRING_TO_RATING.get(rating_text, 0)

        # Only add if required fields are present
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


def get_library(user_id: int) -> list[Book]:
    url = format_url(user_id)
    html = get_response(url)
    soup = BeautifulSoup(html, "html.parser")
    pagination_div = soup.find("div", id="reviewPagination")
    page_links = pagination_div.find_all("a") if pagination_div else []
    page_numbers = [int(a.text) for a in page_links if a.text.isdigit()]
    total_pages = max(page_numbers) if page_numbers else 1
    books = extract_books_from_html(html)
    for page in range(2, total_pages + 1):
        next_url = format_url(user_id, page)
        html = get_response(next_url)
        books += extract_books_from_html(html)
    return books

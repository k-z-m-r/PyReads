"""Parsers extract information from Goodreads HTML review rows."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, override
from warnings import warn

from bs4 import BeautifulSoup
from bs4.element import PageElement, Tag
from pydantic import ValidationError

from .models import Book, _Series

# --- Constants ----------------------------------------------------------------

_REVIEW_ID_PATTERN = re.compile(r"^freeTextContainerreview")
_PAGE_NUMBER_PATTERN = re.compile(r"(\d{1,6})(?=\D|$)")
_SERIES_PATTERN = re.compile(r"\((.*?)(?:,\s*|\s+)#(\d+)\)")
_SERIES_FALLBACK_PATTERN = re.compile(r"^(.*?)(?:,)?\s*Vol\.\s*(\d+)\b")
_SERIES_PATTERNS = [_SERIES_PATTERN, _SERIES_FALLBACK_PATTERN]

_DATE_FORMATS = ("%b %d, %Y", "%b %Y")

_STRING_TO_RATING = {
    "did not like it": 1,
    "it was ok": 2,
    "liked it": 3,
    "really liked it": 4,
    "it was amazing": 5,
}

# --- Helpers ------------------------------------------------------------------


def _safe_find_text(
    element: Tag | PageElement | None, strip: bool = True
) -> str | None:
    """
    Safely extract text from an element, returning None if element is
    None/empty.
    """
    return element.get_text(strip=strip) or None if element else None


def _get_field_cell(row: Tag, field_name: str) -> Tag | None:
    """
    Return the <td class='field {field_name}'> cell, or None if not present.
    """
    el = row.find("td", class_=f"field {field_name}")
    return el if isinstance(el, Tag) else None


def _extract_number(text: str | None, pattern: re.Pattern[str]) -> int | None:
    """
    Extract the first integer using `pattern` from `text`; return None on
    failure.
    """
    if not text:
        return None
    m = pattern.search(text)
    return int(m.group(1)) if m else None


# --- Parser base --------------------------------------------------------------


class _Parser(ABC):
    """
    Abstract base class for all field parsers.
    """

    @staticmethod
    @abstractmethod
    def parse(row: Tag) -> Any | None:
        """Extract a value from a Goodreads review table row.

        Args:
            row: The BS4 Tag to extract information from.

        Returns:
            Value from the tag, or None if no value found.
        """
        raise NotImplementedError


# --- Concrete parsers ---------------------------------------------------------


class _AuthorParser(_Parser):
    """
    Extract author name from review row.
    """

    @override
    @staticmethod
    def parse(row: Tag) -> str | None:
        cell = _get_field_cell(row, "author")
        if not cell:
            return None
        link = cell.find("a")
        return _safe_find_text(link)


class _DateParser(_Parser):
    """
    Extract and parse date read from review row.
    """

    @override
    @staticmethod
    def parse(row: Tag) -> datetime | None:
        cell = _get_field_cell(row, "date_read")
        if not cell:
            return None

        # Prefer explicit "date_read_value"; fall back to any <span title="...">
        span = cell.find("span", class_="date_read_value") or cell.find(
            "span", title=True
        )
        date_string = _safe_find_text(span)
        if not date_string:
            return None

        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(date_string, fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
        return None


class _PageNumberParser(_Parser):
    """
    Extract number of pages from review row.
    """

    @override
    @staticmethod
    def parse(row: Tag) -> int | None:
        cell = _get_field_cell(row, "num_pages")
        if not cell:
            return None
        nobr = cell.find("nobr")
        text = _safe_find_text(nobr, strip=True)
        return _extract_number(text, _PAGE_NUMBER_PATTERN)


class _RatingParser(_Parser):
    """
    Extract user rating from review row.
    """

    @override
    @staticmethod
    def parse(row: Tag) -> int:
        cell = _get_field_cell(row, "rating")
        if not cell:
            return 0
        span = cell.find("span", class_="staticStars")
        title = span.get("title") if isinstance(span, Tag) else None
        if not isinstance(title, str):
            return 0
        return int(_STRING_TO_RATING.get(title.lower(), 0))


class _ReviewParser(_Parser):
    """
    Extract review text from review row.
    """

    @override
    @staticmethod
    def parse(row: Tag) -> str | None:
        span = row.find("span", {"id": _REVIEW_ID_PATTERN})
        return _safe_find_text(span)


class _SeriesParser(_Parser):
    """
    Extract series information from review row.
    """

    @override
    @staticmethod
    def parse(row: Tag) -> _Series | None:
        cell = _get_field_cell(row, "title")
        if not cell:
            return None

        link = cell.find("a")
        if not isinstance(link, Tag):
            return None

        # Prefer explicit series span inside the title link
        series_span = link.find("span", class_="darkGreyText")
        series_text = (
            _safe_find_text(series_span, strip=True) if series_span else None
        )

        # Check patterns against the series span text
        if series_text:
            for pattern in _SERIES_PATTERNS:
                match = pattern.match(series_text)
                if match:
                    return _Series(
                        name=match.group(1).strip(),
                        entry=match.group(2),
                    )
        return None


class _TitleParser(_Parser):
    """
    Extract book title from review row.
    """

    @override
    @staticmethod
    def parse(row: Tag) -> str:
        cell = _get_field_cell(row, "title")
        if not cell:
            return ""

        link = cell.find("a")
        if not isinstance(link, Tag):
            return ""

        # Prefer the direct text node (avoids series span text)
        if link.contents and isinstance(link.contents[0], str):
            return link.contents[0].strip()

        return link.get_text(strip=True) or ""


def _parse_row(row: Tag) -> dict[str, Any]:
    """
    Helper function which parses row into attribute dictionary.

    Args:
        row: The row which contains the data.

    Returns:
        Dictionary mapping attribute name to value.
    """

    parsers: dict[str, type[_Parser]] = {
        "authorName": _AuthorParser,
        "dateRead": _DateParser,
        "numberOfPages": _PageNumberParser,
        "userRating": _RatingParser,
        "userReview": _ReviewParser,
        "title": _TitleParser,
        "series": _SeriesParser,
    }

    attributes: dict[str, Any] = {}

    for attribute, parser in parsers.items():
        value = parser.parse(row)
        if attribute == "series" and value:
            assert isinstance(value, _Series)
            attributes["seriesName"] = value.name
            attributes["seriesEntry"] = value.entry
        attributes[attribute] = value

    return attributes


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

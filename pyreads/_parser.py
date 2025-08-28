"""Parsers extract information from Goodreads HTML review rows."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from bs4.element import PageElement, Tag
from typing_extensions import override

from .models import Series

# --- Constants ----------------------------------------------------------------

_REVIEW_ID_PATTERN = re.compile(r"^freeTextContainerreview")
_PAGE_NUMBER_PATTERN = re.compile(r"(\d{1,6})(?=\D|$)")
_SERIES_PATTERN = re.compile(r"\((.*?)(?:,\s*|\s+)#(\d+)\)")
_SERIES_FALLBACK_PATTERN = re.compile(r"^(.*?)(?:,)?\s*Vol\.\s*(\d+)\b")

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
    """Safely extract text from an element, returning None if element is None/empty."""
    return element.get_text(strip=strip) or None if element else None


def _get_field_cell(row: Tag, field_name: str) -> Tag | None:
    """Return the <td class='field {field_name}'> cell, or None if not present."""
    el = row.find("td", class_=f"field {field_name}")
    return el if isinstance(el, Tag) else None


def _extract_number(text: str | None, pattern: re.Pattern[str]) -> int | None:
    """Extract the first integer using `pattern` from `text`; return None on failure."""
    if not text:
        return None
    m = pattern.search(text)
    return int(m.group(1)) if m else None


# --- Parser base --------------------------------------------------------------


class _Parser(ABC):
    """Abstract base class for all field parsers."""

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
    """Extract author name from review row."""

    @override
    @staticmethod
    def parse(row: Tag) -> str | None:
        cell = _get_field_cell(row, "author")
        if not cell:
            return None
        link = cell.find("a")
        return _safe_find_text(link)


class _DateParser(_Parser):
    """Extract and parse date read from review row."""

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
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        return None


class _PageNumberParser(_Parser):
    """Extract number of pages from review row."""

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
    """Extract user rating from review row."""

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
    """Extract review text from review row."""

    @override
    @staticmethod
    def parse(row: Tag) -> str | None:
        span = row.find("span", {"id": _REVIEW_ID_PATTERN})
        return _safe_find_text(span)


class _SeriesParser(_Parser):
    """Extract series information from review row."""

    @override
    @staticmethod
    def parse(row: Tag) -> Series | None:
        cell = _get_field_cell(row, "title")
        if not cell:
            return None

        link = cell.find("a")
        if not isinstance(link, Tag):
            return None

        # Prefer explicit series span inside the title link
        series_span = link.find("span", class_="darkGreyText")
        if isinstance(series_span, Tag):
            series_text = _safe_find_text(series_span, strip=True)
            if series_text:
                m = _SERIES_PATTERN.match(series_text)
                if m:
                    return Series(name=m.group(1).strip(), number=int(m.group(2)))

        # Fallback: detect "Vol. N" in the raw title text
        raw_title = _safe_find_text(link)
        if raw_title:
            m2 = _SERIES_FALLBACK_PATTERN.match(raw_title)
            if m2:
                return Series(name=m2.group(1).strip(), number=int(m2.group(2)))

        return None


class _TitleParser(_Parser):
    """Extract book title from review row."""

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
    """Helper function which parses row into attribute dictionary.

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
        attributes[attribute] = value

    return attributes

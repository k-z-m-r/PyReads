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

_SERIES_PATTERNS = [
    re.compile(r"\((.*?)(?:,\s*|\s+)#(\d+(?:\.\d+)?)\)"),
    re.compile(r"^(.*?)(?:,)?\s*Vol\.\s*(\d+(?:\.\d+)?)\b"),
    re.compile(r"\((.*?)\s+Book\s+(\d+(?:\.\d+)?)\)"),
]

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

    @classmethod
    def parse(cls, row: Tag) -> Any | None:
        """Extract a value from a Goodreads review table row.

        Args:
            row: The BS4 Tag to extract information from.

        Returns:
            Value from the tag, or None if no value found.
        """
        # Step 1: Extract HTML element
        element = cls._extract_element(row)
        if element is None:
            return None

        # Step 2: Extract raw data from element
        data = cls._extract_data(element)
        if data is None:
            return None

        # Step 3: Transform data into final form
        return cls._transform_data(data)

    @staticmethod
    @abstractmethod
    def _extract_element(row: Tag) -> Tag | None:
        """Extract the relevant HTML element(s) from the row.

        Args:
            row: The BS4 Tag to extract elements from.

        Returns:
            The extracted element(s) as Tag or None if not found.
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def _extract_data(element: Tag) -> str | None:
        """Extract raw data from the element(s).

        Args:
            element: The element to extract data from (always a Tag).

        Returns:
            The extracted raw data as string or None if not found.
        """
        raise NotImplementedError

    @staticmethod
    def _transform_data(data: str) -> Any:
        """Transform the raw data into the final form.

        Args:
            data: The raw data to transform (always a string).

        Returns:
            The transformed data in the appropriate type.
        """

        return data


# --- Concrete parsers ---------------------------------------------------------


class _AuthorParser(_Parser):
    """
    Extract author name from review row.
    """

    @staticmethod
    @override
    def _extract_element(row: Tag) -> Tag | None:
        return _get_field_cell(row, "author")

    @staticmethod
    @override
    def _extract_data(element: Tag) -> str | None:
        link = element.find("a")
        return _safe_find_text(link) if link else None


class _DateParser(_Parser):
    """
    Extract and parse date read from review row.
    """

    @staticmethod
    @override
    def _extract_element(row: Tag) -> Tag | None:
        return _get_field_cell(row, "date_read")

    @staticmethod
    @override
    def _extract_data(element: Tag) -> str | None:
        span = element.find("span", class_="date_read_value") or element.find(
            "span", title=True
        )
        return _safe_find_text(span)

    @staticmethod
    @override
    def _transform_data(data: str) -> Any:
        for fmt in _DATE_FORMATS:
            try:
                dt = datetime.strptime(data, fmt).replace(tzinfo=UTC)
                return dt.date()
            except ValueError:
                continue
        return None


class _PageNumberParser(_Parser):
    """
    Extract number of pages from review row.
    """

    @staticmethod
    @override
    def _extract_element(row: Tag) -> Tag | None:
        return _get_field_cell(row, "num_pages")

    @staticmethod
    @override
    def _extract_data(element: Tag) -> str | None:
        nobr = element.find("nobr")
        return _safe_find_text(nobr, strip=True)

    @staticmethod
    @override
    def _transform_data(data: str) -> Any:
        return _extract_number(data, _PAGE_NUMBER_PATTERN)


class _RatingParser(_Parser):
    """
    Extract user rating from review row.
    """

    @staticmethod
    @override
    def _extract_element(row: Tag) -> Tag | None:
        return _get_field_cell(row, "rating")

    @staticmethod
    @override
    def _extract_data(element: Tag) -> str | None:
        span = element.find("span", class_="staticStars")
        title = span.get("title") if isinstance(span, Tag) else None
        return title if isinstance(title, str) else None

    @staticmethod
    @override
    def _transform_data(data: str) -> Any:
        rating = _STRING_TO_RATING.get(data.lower())
        return int(rating) if rating is not None else None


class _ReviewParser(_Parser):
    """
    Extract review text from review row.
    """

    @staticmethod
    @override
    def _extract_element(row: Tag) -> Tag | None:
        element = row.find("span", {"id": _REVIEW_ID_PATTERN})
        return element if isinstance(element, Tag) else None

    @staticmethod
    @override
    def _extract_data(element: Tag) -> str | None:
        return _safe_find_text(element)


class _SeriesParser(_Parser):
    """
    Extract series information from review row.
    """

    @staticmethod
    @override
    def _extract_element(row: Tag) -> Tag | None:
        cell = _get_field_cell(row, "title")
        if not cell:
            return None

        link = cell.find("a")
        if not isinstance(link, Tag):
            return None

        return link

    @staticmethod
    @override
    def _extract_data(element: Tag) -> str | None:
        series_span = element.find("span", class_="darkGreyText")
        return _safe_find_text(series_span, strip=True)

    @staticmethod
    @override
    def _transform_data(data: str) -> Any:
        for pattern in _SERIES_PATTERNS:
            if match := pattern.match(data):
                return _Series(
                    name=match.group(1).strip(),
                    entry=match.group(2),
                )
        return None


class _TitleParser(_Parser):
    """
    Extract book title from review row.
    """

    @staticmethod
    @override
    def _extract_element(row: Tag) -> Tag | None:
        cell = _get_field_cell(row, "title")
        if not cell:
            return None

        link = cell.find("a")
        if not isinstance(link, Tag):
            return None

        return link

    @staticmethod
    @override
    def _extract_data(element: Tag) -> str | None:
        if element.contents and isinstance(element.contents[0], str):
            return element.contents[0].strip()
        return element.get_text(strip=True) or None


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

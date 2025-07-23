"""Parsers extract information from HTML elements."""

import re
from abc import ABC, abstractmethod
from calendar import monthrange
from datetime import datetime
from typing import Any

from bs4.element import Tag

from pyreads._models import Series
from pyreads._utilities import STRING_TO_RATING


class Parser(ABC):
    @staticmethod
    @abstractmethod
    def parse(row: Tag) -> Any:
        pass


class AuthorParser(Parser):
    @staticmethod
    def parse(row: Tag) -> str | None:
        author_cell = row.find("td", class_="field author")
        author_link = author_cell.find("a") if author_cell else None
        return author_link.get_text(strip=True) if author_link else None


class DateParser(Parser):
    @staticmethod
    def parse(row: Tag) -> datetime | None:
        date_span = row.find("span", class_="date_read_value")
        date_string = date_span.get_text(strip=True) if date_span else None
        if not date_string:
            return None

        for format_pattern in ("%b %d, %Y", "%b %Y"):
            try:
                parsed_date = datetime.strptime(date_string, format_pattern)
                if format_pattern == "%b %Y":
                    last_day = monthrange(parsed_date.year, parsed_date.month)[1]
                    parsed_date = parsed_date.replace(day=last_day)
                return parsed_date
            except ValueError:
                continue
        return None


class PageNumberParser(Parser):
    @staticmethod
    def parse(row: Tag) -> int | None:
        num_pages_cell = row.find("td", class_="field num_pages")
        if not num_pages_cell:
            return None

        value_container = num_pages_cell.find("div", class_="value")
        if not value_container:
            return None

        page_info = value_container.find("nobr")
        if not page_info or not page_info.contents:
            return None

        for element in page_info.contents:
            if isinstance(element, str) and element.strip().isdigit():
                return int(element.strip())

        return None


class RatingParser(Parser):
    @staticmethod
    def parse(row: Tag) -> int:
        rating_cell = row.find("td", class_="field rating")
        rating_span = (
            rating_cell.find("span", class_="staticStars") if rating_cell else None
        )
        tooltip_text = (
            rating_span.get("title")
            if rating_span and rating_span.has_attr("title")
            else None
        )
        return STRING_TO_RATING.get(tooltip_text, 0)


class ReviewParser(Parser):
    @staticmethod
    def parse(row: Tag) -> str | None:
        review_span = row.find("span", {"id": re.compile(r"^freeTextContainerreview")})
        return review_span.get_text(strip=True) if review_span else None


class SeriesParser(Parser):
    @staticmethod
    def parse(row: Tag) -> Series | None:
        title_cell = row.find("td", class_="field title")
        title_link = title_cell.find("a") if title_cell else None
        if not title_link:
            return None

        # Try series span first
        series_span = title_link.find("span", class_="darkGreyText")
        if series_span:
            series_text = series_span.get_text(strip=True)
            match = re.match(r"\((.*?)(?:,\s*|\s+)#(\d+)\)", series_text)
            if match:
                return Series(name=match.group(1).strip(), number=int(match.group(2)))

        # If no span, fallback to inline Vol. in title text
        raw_title = (
            title_link.contents[0].strip()
            if title_link.contents
            else title_link.get_text(strip=True)
        )
        fallback_match = re.match(r"^(.*?)(?:,)?\s*Vol\.\s*(\d+)\b", raw_title)
        if fallback_match:
            return Series(
                name=fallback_match.group(1).strip(),
                number=int(fallback_match.group(2)),
            )

        return None


class TitleParser(Parser):
    @staticmethod
    def parse(row: Tag) -> str | None:
        title_cell = row.find("td", class_="field title")
        title_link = title_cell.find("a") if title_cell else None
        if not title_link:
            return None

        raw_title = (
            title_link.contents[0].strip()
            if title_link.contents
            else title_link.get_text(strip=True)
        )
        return raw_title


# TODO: add helper function which compiles values into model dict?
PARSERS = [
    AuthorParser,
    DateParser,
    PageNumberParser,
    RatingParser,
    ReviewParser,
    TitleParser,
]

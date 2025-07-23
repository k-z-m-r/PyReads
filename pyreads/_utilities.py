"""Utilities to support core functionality."""

import re
from abc import ABC, abstractmethod
from calendar import monthrange
from datetime import datetime
from enum import IntEnum, unique
from typing import Any

from bs4.element import Tag


@unique
class Rating(IntEnum):
    NO_RATING = 0
    DID_NOT_LIKE_IT = 1
    IT_WAS_OK = 2
    LIKED_IT = 3
    REALLY_LIKED_IT = 4
    IT_WAS_AMAZING = 5


STRING_TO_RATING = {
    "did not like it": Rating.DID_NOT_LIKE_IT,
    "it was ok": Rating.IT_WAS_OK,
    "liked it": Rating.LIKED_IT,
    "really liked it": Rating.REALLY_LIKED_IT,
    "it was amazing": Rating.IT_WAS_AMAZING,
}


# Abstract base class for all parsers
class Parser(ABC):
    @staticmethod
    @abstractmethod
    def parse(tr: Tag) -> Any:
        pass


class ReviewParser(Parser):
    @staticmethod
    def parse(tr: Tag) -> str | None:
        span = tr.find("span", {"id": re.compile(r"^freeTextContainerreview")})
        return span.get_text(strip=True) if span else None


class AuthorParser(Parser):
    @staticmethod
    def parse(tr: Tag) -> str | None:
        td = tr.find("td", class_="field author")
        a = td.find("a") if td else None
        return a.get_text(strip=True) if a else None


class TitleParser(Parser):
    @staticmethod
    def parse(tr: Tag) -> tuple[str | None, str | None, int | None]:
        td = tr.find("td", class_="field title")
        a = td.find("a") if td else None
        if not a:
            return None, None, None
        title_text = a.contents[0].strip() if a.contents else a.get_text(strip=True)
        series, series_number = None, None
        series_span = a.find("span", class_="darkGreyText")
        if series_span:
            series_info = series_span.get_text(strip=True)
            match = re.match(r"\((.*),\s*#(\d+)\)", series_info)
            if match:
                series = match.group(1)
                series_number = int(match.group(2))
        return title_text, series, series_number


class RatingParser(Parser):
    @staticmethod
    def parse(tr: Tag, string_to_rating: dict[str, int] = STRING_TO_RATING) -> int:
        td = tr.find("td", class_="field rating")
        span = td.find("span", class_="staticStars") if td else None
        rating_text = span.get("title") if span and span.has_attr("title") else None
        return string_to_rating.get(rating_text, 0)


class DateParser(Parser):
    @staticmethod
    def parse_review_date(date_str: str) -> datetime | None:
        """
        Parse a Goodreads review date string into a datetime object.
        Handles formats like 'Jan 01, 2020' and 'Jan 2020'.
        """
        for fmt in ("%b %d, %Y", "%b %Y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                if fmt == "%b %Y":
                    dt = dt.replace(day=monthrange(dt.year, dt.month)[1])
                return dt
            except ValueError:
                continue
        return None

    @staticmethod
    def parse(tr: Tag) -> datetime | None:
        span = tr.find("span", class_="date_read_value")
        date_str = span.get_text(strip=True) if span else None
        return DateParser.parse_review_date(date_str) if date_str else None


def format_url(user_id: int, page: int = 1) -> str:
    return f"https://www.goodreads.com/review/list/{user_id}?page={page}&shelf=read"

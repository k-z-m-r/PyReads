"""Parsers extract information from HTML elements."""

import re
from abc import ABC, abstractmethod
from calendar import monthrange
from datetime import datetime
from typing import Any

from bs4.element import Tag

from pyreads._utilities import STRING_TO_RATING


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
        assert td
        a = td.find("a")
        return a.get_text(strip=True)


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
    def parse(tr: Tag) -> int:
        td = tr.find("td", class_="field rating")
        span = td.find("span", class_="staticStars") if td else None
        rating_text = span.get("title") if span and span.has_attr("title") else None
        return STRING_TO_RATING.get(rating_text, 0)


class DateParser(Parser):
    @staticmethod
    def parse(tr: Tag) -> datetime | None:
        span = tr.find("span", class_="date_read_value")
        date_str = span.get_text(strip=True) if span else None
        if not date_str:
            return None
        for fmt in ("%b %d, %Y", "%b %Y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                if fmt == "%b %Y":
                    dt = dt.replace(day=monthrange(dt.year, dt.month)[1])
                return dt
            except ValueError:
                continue
        return None

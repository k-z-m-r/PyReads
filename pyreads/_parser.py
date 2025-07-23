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


class RatingParser(Parser):
    @staticmethod
    def parse(row: Tag) -> int | None:
        rating_cell = row.find("td", class_="field rating")
        rating_span = (
            rating_cell.find("span", class_="staticStars") if rating_cell else None
        )
        tooltip_text = (
            rating_span.get("title")
            if rating_span and rating_span.has_attr("title")
            else None
        )
        return STRING_TO_RATING.get(tooltip_text)


class ReviewParser(Parser):
    @staticmethod
    def parse(row: Tag) -> str | None:
        review_span = row.find("span", {"id": re.compile(r"^freeTextContainerreview")})
        return review_span.get_text(strip=True) if review_span else None


class TitleParser(Parser):
    @staticmethod
    def parse(row: Tag) -> tuple[str | None, str | None, int | None]:
        title_cell = row.find("td", class_="field title")
        title_link = title_cell.find("a") if title_cell else None
        if not title_link:
            return None, None, None

        raw_title = (
            title_link.contents[0].strip()
            if title_link.contents
            else title_link.get_text(strip=True)
        )

        series_name, series_number = None, None
        series_span = title_link.find("span", class_="darkGreyText")
        if series_span:
            series_text = series_span.get_text(strip=True)
            match = re.match(r"\((.*),\s*#(\d+)\)", series_text)
            if match:
                series_name = match.group(1)
                series_number = int(match.group(2))

        return raw_title, series_name, series_number

"""Utilities to support core functionality."""

from calendar import monthrange
from datetime import datetime
from enum import IntEnum, unique


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


def parse_date(date: str) -> datetime | None:
    for fmt in ("%b %d, %Y", "%b %Y"):
        try:
            dt = datetime.strptime(date, fmt)
            if fmt == "%b %Y":
                dt = dt.replace(day=monthrange(dt.year, dt.month)[1])
            return dt
        except ValueError:
            pass
    return None


def format_url(user_id: int, page: int = 1) -> str:
    return f"https://www.goodreads.com/review/list/{user_id}?page={page}&shelf=read"

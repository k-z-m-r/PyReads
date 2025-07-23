"""Utilities to support core functionality."""

from enum import IntEnum


class Rating(IntEnum):
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

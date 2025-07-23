"""Pydantic data models."""

from datetime import datetime
from typing import Self

from pandas import DataFrame
from pydantic import BaseModel, model_validator


class Book(BaseModel):
    title: str
    series: str | None = None
    seriesNumber: int | None = None
    authorName: str
    numberOfPages: int | None
    dateRead: datetime
    userRating: int
    review: str | None = None

    @property
    def full_title(self) -> str:
        title = f"{self.title} "

        if self.series:
            title += f"({self.series}, #{self.seriesNumber}) "

        title += f"by {self.authorName}"

        return title

    @model_validator(mode="after")
    def validate_series(self) -> Self:
        if (self.series is not None) != (self.seriesNumber is not None):
            raise ValueError(
                "Both series and seriesNumber must be set together or both be None."
            )
        return self


class Library(BaseModel):
    owner: int
    books: list[Book]

    @property
    def dataframe(self) -> DataFrame:
        return DataFrame([book.model_dump() for book in self.books])

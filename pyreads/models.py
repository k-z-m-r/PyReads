"""Pydantic data models."""

from datetime import datetime

from pandas import DataFrame
from pydantic import BaseModel, PrivateAttr


class Series(BaseModel):
    name: str
    number: int

    def __str__(self) -> str:
        return f"({self.name}, #{self.number})"


class Book(BaseModel):
    title: str
    authorName: str
    numberOfPages: int | None
    dateRead: datetime
    userRating: int
    review: str | None = None
    series: Series | None = None

    @property
    def full_title(self) -> str:
        title = f"{self.title} "
        if self.series:
            title += f"{self.series} "
        title += f"by {self.authorName}"
        return title


class Library(BaseModel):
    owner: int
    books: list[Book]

    _dataframe: DataFrame = PrivateAttr()

    def model_post_init(self, __context: dict[object, object]) -> None:
        del __context

        self._dataframe = DataFrame([book.model_dump() for book in self.books])

    @property
    def dataframe(self) -> DataFrame:
        return self._dataframe

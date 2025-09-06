"""Pydantic data models."""

from datetime import date
from functools import cached_property
from typing import Literal

from pandas import DataFrame
from pydantic import BaseModel, Field


class Series(BaseModel):
    name: str = Field(title="Name", description="The name of the series.")
    entry: str = Field(
        title="Series Entry",
        description="The entry of the book in that series.",
        examples=["1", "2", "2.5"],
    )

    def __str__(self) -> str:
        return f"({self.name}, #{self.entry})"


class Book(BaseModel):
    title: str = Field(title="Title", description="The title of the book.")
    authorName: str = Field(
        title="Author Name", description="The name of the author."
    )
    numberOfPages: int = Field(
        title="Number of Pages",
        description="The total number of pages in the book.",
        ge=1,
    )
    dateRead: date = Field(
        title="Date Read",
        description="The date that the user finished the book.",
    )
    userRating: Literal[0, 1, 2, 3, 4, 5] = Field(
        title="User Rating",
        description="The rating that the user gave the book.",
    )
    userReview: str | None = Field(
        title="User Review",
        description="The optional review of the book from the user.",
        default=None,
    )
    series: Series | None = Field(
        title="Series",
        description="The optional series for which the book belongs to.",
        default=None,
    )

    @property
    def full_title(self) -> str:
        """
        Formats title, series, and authorName to a complete title.

        Returns:
            (title) (series) by (authorName)
        """
        title = f"{self.title} "
        if self.series:
            title += f"{self.series} "
        title += f"by {self.authorName}"
        return title


class Library(BaseModel):
    userId: int = Field(
        title="User ID", description="The Goodreads user ID for the library."
    )
    books: list[Book] = Field(
        title="Books", description="The collection of books."
    )

    @cached_property
    def dataframe(self) -> DataFrame:
        """
        Creates a Pandas dataframe from the library.

        Returns:
            Pandas dataframe where the headers correspond to the field titles.
        """
        field_titles = {
            name: field.title for name, field in Book.model_fields.items()
        }

        records = []
        for book in self.books:
            raw = book.model_dump()
            records.append({field_titles[k]: v for k, v in raw.items()})

        return DataFrame(records)

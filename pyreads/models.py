"""Pydantic data models."""

from datetime import date
from functools import cached_property
from typing import Literal, Self

from pandas import DataFrame
from pydantic import BaseModel, Field, model_validator


class _Series(BaseModel):
    name: str = Field(title="Name", description="The name of the series.")
    entry: float = Field(
        title="Series Entry",
        description="The entry of the book in that series.",
        examples=[1, 2, 2.5],
    )


class Book(BaseModel):
    title: str = Field(title="Title", description="The title of the book.")
    authorName: str = Field(
        title="Author Name", description="The name of the author."
    )
    numberOfPages: int | None = Field(
        title="Number of Pages",
        description="The total number of pages in the book.",
        default=None,
    )
    dateRead: date | None = Field(
        title="Date Read",
        description="The date that the user finished the book.",
        default=None,
    )
    userRating: Literal[1, 2, 3, 4, 5] | None = Field(
        title="User Rating",
        description="The rating that the user gave the book.",
        default=None,
    )
    userReview: str | None = Field(
        title="User Review",
        description="The optional review of the book from the user.",
        default=None,
    )
    seriesName: str | None = Field(
        title="Series Name",
        description="The name of the series the book belongs to (if any).",
        default=None,
    )
    seriesEntry: float | None = Field(
        title="Series Entry",
        description="The book's position in the series.",
        default=None,
        examples=[1, 1.5],
    )

    @model_validator(mode="after")
    def validate_series(self) -> Self:
        """
        Validates that if a seriesName exists, a seriesEntry must also exist.
        """

        if bool(self.seriesName) != bool(self.seriesEntry):
            err = "seriesName and seriesEntry must be provided together."
            raise ValueError(err)
        return self

    @cached_property
    def full_title(self) -> str:
        """
        Formats title, series, and authorName to a complete title.

        Returns:
            (title) (series) by (authorName)
        """
        title = f"{self.title} "
        if self.seriesName and self.seriesEntry:
            series_entry = (
                int(self.seriesEntry)
                if self.seriesEntry.is_integer()
                else self.seriesEntry
            )
            title += f"({self.seriesName}, #{series_entry}) "
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

        return DataFrame(records).replace({float("nan"): None})

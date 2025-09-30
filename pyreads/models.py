"""Pydantic data models."""

from datetime import date
from functools import cached_property
from types import UnionType
from typing import (
    Any,
    Literal,
    Self,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from polars import (
    DataFrame,
    DataType,
    Date,
    Float32,
    Int16,
    Object,
    Utf8,
)
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

    def create_row(self) -> list[object]:
        """Return a list of values for the book in the canonical column order.

        Use Pydantic's model_dump() to get the field values and return
        them in the same order as the model fields that have a `title`.
        """
        data = self.model_dump()

        title_to_name = {
            field.title: name
            for name, field in type(self).model_fields.items()
            if field.title is not None
        }

        headers = self.get_column_headers()
        return [data[title_to_name[title]] for title in headers]

    @classmethod
    def get_column_headers(cls) -> list[str]:
        """Return the list of column header titles in canonical order.

        The canonical order follows the order of `model_fields` and
        includes only fields with a non-None `title`.
        """
        return [
            field.title
            for field in cls.model_fields.values()
            if field.title is not None
        ]

    @classmethod
    def get_polars_schema(cls) -> dict[str, Any]:
        """Get Polars schema from Pydantic model for Book."""

        def _convert_annotation_to_polars_datatype(
            annotation: Any,
        ) -> type[DataType]:
            """Map a Python/typing annotation to a Polars DataType."""
            origin = get_origin(annotation)

            if origin in (Union, UnionType):
                args = [a for a in get_args(annotation) if a is not type(None)]
                annotation = args[0] if args else None
                origin = (
                    get_origin(annotation) if annotation is not None else None
                )
            if origin is Literal:
                literal = get_args(annotation)
                annotation = type(literal[0])

            if annotation is int:
                return Int16
            if annotation is float:
                return Float32
            if annotation is str:
                return Utf8
            if annotation is date:
                return Date
            return Object

        type_hints = get_type_hints(cls)
        annotations = {
            field_name: type_hints[field_name]
            for field_name in cls.model_fields
        }
        field_titles = {
            name: field.title
            for name, field in Book.model_fields.items()
            if field.title is not None
        }
        return {
            field_titles[name]: _convert_annotation_to_polars_datatype(
                annotation
            )
            for name, annotation in annotations.items()
            if name in field_titles
        }


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

        headers = Book.get_column_headers()
        schema = Book.get_polars_schema()

        rows = [book.create_row() for book in self.books]

        columns: dict[str, list[object]] = {
            header: [row[i] for row in rows] for i, header in enumerate(headers)
        }

        return DataFrame(columns, schema=schema)

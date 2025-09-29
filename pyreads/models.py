"""Pydantic data models."""

from datetime import date, datetime, time
from functools import cached_property
from types import UnionType
from typing import (
    Annotated,
    Any,
    Literal,
    Self,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from polars import (
    Boolean,
    DataFrame,
    DataType,
    Date,
    Datetime,
    Float32,
    Int16,
    Object,
    Time,
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

    @classmethod
    def _get_field_annotations(cls) -> dict[str, Any]:
        annotations = get_type_hints(cls)
        return {
            field_name: annotations[field_name]
            for field_name in cls.model_fields
        }

    @classmethod
    def get_polars_schema(cls) -> dict[str, Any]:
        """Map a Python/typing annotation to a Polars DataType."""

        def _convert_annotation_to_polars_datatype(
            annotation: Any,
        ) -> type[DataType]:
            """Map a Python/typing annotation to a Polars DataType."""
            if get_origin(annotation) is Annotated:
                annotation = get_args(annotation)[0]

            origin = get_origin(annotation)

            if origin in (Union, UnionType):
                args = [a for a in get_args(annotation) if a is not type(None)]
                annotation = args[0] if args else None
                origin = (
                    get_origin(annotation) if annotation is not None else None
                )

            if origin is Literal:
                lit = get_args(annotation)
                if not lit:
                    return Object
                annotation = type(lit[0])

            if annotation is int:
                return Int16
            if annotation is float:
                return Float32
            if annotation is str:
                return Utf8
            if annotation is bool:
                return Boolean
            if annotation is date:
                return Date
            if annotation is datetime:
                return Datetime
            if annotation is time:
                return Time
            return Object

        headers = {
            name: field.title
            for name, field in Book.model_fields.items()
            if field.title is not None
        }
        return {
            headers[name]: _convert_annotation_to_polars_datatype(annotation)
            for name, annotation in cls._get_field_annotations().items()
            if name in headers
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

        headers = {
            name: field.title
            for name, field in Book.model_fields.items()
            if field.title is not None
        }
        schema = Book.get_polars_schema()
        columns: dict[str, list[object]] = {
            header: [getattr(book, name) for book in self.books]
            for name, header in headers.items()
        }

        return DataFrame(columns, schema=schema)

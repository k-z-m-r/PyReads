"""Pydantic data models."""

from datetime import datetime

from pydantic import BaseModel, model_validator


class Book(BaseModel):
    title: str
    series: str | None = None
    seriesNumber: int | None = None
    authorName: str
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
    def check_series_fields(self) -> "Book":
        if (self.series is not None) != (self.seriesNumber is not None):
            raise ValueError(
                "Both series and seriesNumber must be set together or both be None."
            )
        return self

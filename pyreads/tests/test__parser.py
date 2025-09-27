"""Tests for the _parser module using real Goodreads HTML data."""

from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from pytest import fixture, warns

from pyreads._parser import (
    _AuthorParser,
    _DateParser,
    _PageNumberParser,
    _parse_books_from_html,
    _parse_row,
    _RatingParser,
    _ReviewParser,
    _SeriesParser,
    _TitleParser,
)

# --- Fixtures -----------------------------------------------------------------


@fixture
def sample_row() -> Tag:
    """Create a BeautifulSoup Tag from the Watchmen sample row HTML."""
    html_path = Path(__file__).parent / "test_inputs" / "input.html"
    html_content: str = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")

    row = soup.find("tr")
    assert row is not None
    assert isinstance(row, Tag)

    return row


@fixture
def input_html() -> str:
    """Return the raw HTML from test_inputs/input.html."""
    html_path = Path(__file__).parent / "test_inputs" / "input.html"
    return html_path.read_text(encoding="utf-8")


# --- AuthorParser Tests ------------------------------------------------------


def test_author_parser_success(sample_row: Tag) -> None:
    assert _AuthorParser.parse(sample_row) == "Moore, Alan"


def test_author_parser_missing_cell() -> None:
    row: Tag = BeautifulSoup("<tr></tr>", "html.parser").find("tr")  # type: ignore
    assert _AuthorParser.parse(row) is None


def test_author_parser_missing_link() -> None:
    tag = (
        '<tr><td class="field author">'
        '<div class="value">No Link</div></td></tr>'
    )
    row: Tag = BeautifulSoup(
        tag,
        "html.parser",
    ).find("tr")  # type: ignore
    assert _AuthorParser.parse(row) is None


# --- TitleParser Tests -------------------------------------------------------


def test_title_parser_success(sample_row: Tag) -> None:
    assert _TitleParser.parse(sample_row) == "Watchmen"


def test_title_parser_missing_cell() -> None:
    row: Tag = BeautifulSoup("<tr></tr>", "html.parser").find("tr")  # type: ignore
    assert _TitleParser.parse(row) is None


def test_title_parser_missing_link() -> None:
    tag = (
        '<tr><td class="field title"><div class="value">No Link</div></td></tr>'
    )
    row: Tag = BeautifulSoup(
        tag,
        "html.parser",
    ).find("tr")  # type: ignore
    assert _TitleParser.parse(row) is None


def test_title_parser_empty_link() -> None:
    html = """
    <tr>
        <td class="field title">
            <div class="value">
                <a href=""></a>
            </div>
        </td>
    </tr>
    """
    row: Tag = BeautifulSoup(html, "html.parser").find("tr")  # type: ignore
    assert _TitleParser.parse(row) is None


# --- PageNumberParser Tests --------------------------------------------------


def test_page_number_parser_success(sample_row: Tag) -> None:
    assert _PageNumberParser.parse(sample_row) == 416


def test_page_number_parser_missing_cell() -> None:
    row: Tag = BeautifulSoup("<tr></tr>", "html.parser").find("tr")  # type: ignore
    assert _PageNumberParser.parse(row) is None


def test_page_number_parser_missing_value() -> None:
    row: Tag = BeautifulSoup(
        '<tr><td class="field num_pages"></td></tr>', "html.parser"
    ).find("tr")  # type: ignore
    assert _PageNumberParser.parse(row) is None


# --- RatingParser Tests ------------------------------------------------------


def test_rating_parser_success(sample_row: Tag) -> None:
    # "it was amazing" → 5 stars
    assert _RatingParser.parse(sample_row) == 5


def test_rating_parser_missing_cell() -> None:
    row: Tag = BeautifulSoup("<tr></tr>", "html.parser").find("tr")  # type: ignore
    assert _RatingParser.parse(row) is None


def test_rating_parser_no_stars() -> None:
    tag = (
        '<tr><td class="field rating">'
        '<div class="value">No stars</div></td></tr>'
    )
    row: Tag = BeautifulSoup(
        tag,
        "html.parser",
    ).find("tr")  # type: ignore
    assert _RatingParser.parse(row) is None


# --- ReviewParser Tests ------------------------------------------------------


def test_review_parser_success(sample_row: Tag) -> None:
    text: str | None = _ReviewParser.parse(sample_row)
    assert text is not None
    assert "Too many characters to keep track of" in text


def test_review_parser_missing_span() -> None:
    row: Tag = BeautifulSoup("<tr></tr>", "html.parser").find("tr")  # type: ignore
    assert _ReviewParser.parse(row) is None


# --- DateParser Tests --------------------------------------------------------


def test_date_parser_success(sample_row: Tag) -> None:
    result: datetime | None = _DateParser.parse(sample_row)
    assert result is not None
    assert result.year == 2009
    assert result.month == 12


def test_date_parser_missing_cell() -> None:
    row: Tag = BeautifulSoup("<tr></tr>", "html.parser").find("tr")  # type: ignore
    assert _DateParser.parse(row) is None


def test_date_parser_invalid_format() -> None:
    html: str = """
    <tr>
        <td class="field date_read">
            <div class="value">
                <span title="Invalid Date">Invalid Date</span>
            </div>
        </td>
    </tr>
    """
    row: Tag = BeautifulSoup(html, "html.parser").find("tr")  # type: ignore
    assert _DateParser.parse(row) is None


def test_date_parser_no_date() -> None:
    html = """
    <tr>
        <td class="field date_read">
            <div class="value">
                <span title=""></span>
            </div>
        </td>
    </tr>
    """
    row: Tag = BeautifulSoup(html, "html.parser").find("tr")  # type: ignore
    assert _DateParser.parse(row) is None


# --- SeriesParser Tests ------------------------------------------------------


def test_series_parser_none_in_sample(sample_row: Tag) -> None:
    assert _SeriesParser.parse(sample_row) is None


def test_series_parser_dark_grey_text() -> None:
    html: str = """
    <tr>
        <td class="field title">
            <div class="value">
                <a href="/book/show/123">
                    Title
                    <span class="darkGreyText">(Series Name, #1)</span>
                </a>
            </div>
        </td>
    </tr>
    """
    row: Tag = BeautifulSoup(html, "html.parser").find("tr")  # type: ignore
    result = _SeriesParser.parse(row)
    assert result is not None
    assert result.name == "Series Name"
    assert result.entry == "1"


def test_series_parser_vol_pattern() -> None:
    html: str = """
    <tr>
        <td class="field title">
            <div class="value">
                <a href="/book/show/123">
                    Title
                    <span class="darkGreyText">Series Name, Vol. 2</span>
                </a>
            </div>
        </td>
    </tr>
    """
    row: Tag = BeautifulSoup(html, "html.parser").find("tr")  # type: ignore
    result = _SeriesParser.parse(row)
    assert result is not None
    assert result.name == "Series Name"
    assert result.entry == "2"


def test_series_parser_missing_title_cell() -> None:
    row: Tag = BeautifulSoup("<tr></tr>", "html.parser").find("tr")  # type: ignore
    assert _SeriesParser.parse(row) is None


def test_series_parser_no_link() -> None:
    html = """
    <tr>
        <td class="field title">
            <div class="value">
                <span class="darkGreyText">
                    (Series Name, #1)
                </span>
            </div>
        </td>
    </tr>
    """
    row: Tag = BeautifulSoup(html, "html.parser").find("tr")  # type: ignore
    assert _SeriesParser.parse(row) is None


# --- Integration Tests -------------------------------------------------------


def test_all_parsers_work_with_sample(sample_row: Tag) -> None:
    results = _parse_row(sample_row)
    assert results["authorName"] == "Moore, Alan"
    assert results["title"] == "Watchmen"
    assert results["numberOfPages"] == 416
    assert results["userRating"] == 5
    assert isinstance(results["userReview"], str)
    assert isinstance(results["dateRead"], date)
    assert results["series"] is None


def test_parse_row_series_attribute() -> None:
    html = """
    <tr>
        <td class="field title">
            <div class="value">
                <a href="/book/show/123">
                    Title
                    <span class="darkGreyText">
                        (Series Name, #1)
                    </span>
                </a>
            </div>
        </td>
    </tr>
    """
    row: Tag = BeautifulSoup(html, "html.parser").find("tr")  # type: ignore
    result = _parse_row(row)
    assert result["seriesName"] == "Series Name"
    assert result["seriesEntry"] == "1"


# --- _parse_books_from_html Tests --------------------------------------------


def test_parse_books_from_html(input_html: str) -> None:
    books = _parse_books_from_html(input_html)
    assert len(books) == 1

    # Accessing attributes of the Book object directly
    book = books[0]
    assert book.title == "Watchmen"
    assert book.seriesName is None
    assert book.seriesEntry is None


def test_parse_books_from_html_missing_title() -> None:
    html = """
    <html>
        <body>
            <table>
                <tr id="review_81002456" class="bookalike review">
                    <td class="field author">
                        <div class="value">
                            <a href="/author/show/3961.Alan_Moore">
                                Moore, Alan
                            </a>
                        </div>
                    </td>
                    <td class="field avg_rating">
                        <div class="value">4.39</div>
                    </td>
                    <td class="field num_pages">
                        <div class="value">416</div>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """
    with warns(UserWarning):
        books = _parse_books_from_html(html)
        assert len(books) == 0

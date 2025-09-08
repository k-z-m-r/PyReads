"""Integration test for the core module."""

from pyreads.core import fetch_library


def test_fetch_library_integration() -> None:
    """Integration test for fetch_library using an arbitrary user ID."""
    user_id = 110430434

    # Call the function
    library = fetch_library(user_id)

    # Validate the result
    assert library.userId == user_id
    assert isinstance(library.books, list)  # Ensure books is a list
    assert len(library.books) > 0  # Ensure the library contains books

    # Validate the structure of the first book
    for book in library.books:
        assert isinstance(book.title, str)
        assert isinstance(book.authorName, str)
        assert isinstance(book.numberOfPages, int)
        assert isinstance(book.userRating, int)
        assert book.userRating >= 0
        assert book.userRating <= 5

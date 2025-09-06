"""PyReads package."""

from .core import fetch_goodreads_library
from .models import Book, Library

__version__ = "0.2.5"
__author__ = "Jeremy Kazimer"
__all__ = ["Book", "Library", "fetch_goodreads_library"]

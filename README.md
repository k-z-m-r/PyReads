# PyReads

PyReads is a Python package designed to process and analyze data from Goodreads. It allows users to fetch their Goodreads library, parse book details, and work with the data programmatically.

## Installation

To install PyReads, use `pip`:

```bash
pip install pyreads
```

## Requirements

- Python >= 3.10
- Dependencies:
  - `httpx==0.28.1`
  - `bs4==0.0.2`
  - `lxml==6.0.0`
  - `pandas==2.3.1`
  - `pydantic==2.11.7`
  - `tqdm==4.67.1`

## Usage

### Fetching Your Goodreads Library

Here’s an example of how to use PyReads to fetch your Goodreads library:

```python
from pyreads import fetch_library

# Replace with your Goodreads user ID
user_id = 110430434

# Fetch the library
library = fetch_library(user_id)

# Print the books in your library
for book in library.books:
    print(book.full_title)
```

### Example Output

```plaintext
Bear and the Three Goldilocks by Horne, Patrick
The Starving Saints by Starling, Caitlin
Straight by Tingle, Chuck
Brave New World by Huxley, Aldous
The Hellbound Heart by Barker, Clive
```

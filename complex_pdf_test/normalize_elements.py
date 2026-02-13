"""Normalize raw text: clean whitespace, strip noise, optional truncation."""

import re

LOG_PREFIX = "[normalize]"


def normalize_text(text: str) -> str:
    """Clean extracted text for chunking and indexing."""
    if not text or not text.strip():
        print(f"{LOG_PREFIX} Empty input, skipping.")
        return ""
    in_len = len(text)
    # Collapse multiple newlines and spaces
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()
    print(f"{LOG_PREFIX} {in_len} → {len(text)} chars (whitespace normalized)")
    return text

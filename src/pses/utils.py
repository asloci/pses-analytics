"""
utils.py
~~~~~~~~
Shared utilities for the pses package.
"""

from __future__ import annotations

import tempfile

import httpx


def fetch_with_bom_strip(url: str) -> str:
    """Fetch a BOM-prefixed CSV from a URL, strip the BOM, write to temp file, return path."""
    response = httpx.get(url, timeout=60, follow_redirects=True)
    response.raise_for_status()
    content = response.content
    # Strip UTF-8 BOM if present
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
    # Decode as latin-1 (accepts all bytes), re-encode as clean UTF-8
    text = content.decode('latin-1')
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', encoding='utf-8')
    tmp.write(text)
    tmp.close()
    return tmp.name

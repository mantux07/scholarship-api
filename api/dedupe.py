#!/usr/bin/env python3
"""
Author: Tim Smith
Note: All Code owned by Tim

Duplicate detection for scholarship / research listings.

The same program can arrive under slightly different names ("Barry Goldwater
Scholarship" vs "The Barry M. Goldwater Scholarship"), either from two catalog
methods or from Claude suggestions, so exact string matching isn't enough.
"""

import re
from urllib.parse import urlparse

# Words that don't distinguish one program from another.
_FILLER = {
    'the', 'a', 'an', 'of', 'for', 'and', 'in', 'to',
    'scholarship', 'scholarships', 'program', 'programs', 'award', 'awards',
}


def name_tokens(name: str) -> frozenset:
    """Significant lowercase tokens of a listing name (parentheticals dropped)."""
    text = re.sub(r'\(.*?\)', ' ', (name or '').lower()).replace('&', ' and ')
    words = re.findall(r'[a-z0-9]+', text)
    return frozenset(w for w in words if w not in _FILLER and len(w) > 1)


def name_key(name: str) -> str:
    """Canonical key: two names with the same key are the same listing."""
    return ' '.join(sorted(name_tokens(name)))


def url_key(url: str) -> str:
    """host+path of an application URL, or '' when it can't identify a listing
    (blank, placeholder, or a generic Google search link)."""
    if not url or url == '#':
        return ''
    parsed = urlparse(url.strip().lower())
    host = parsed.netloc.removeprefix('www.')
    if not host or host.startswith('google.'):
        return ''
    return host + parsed.path.rstrip('/')


class DuplicateFilter:
    """Tracks seen listings; `is_duplicate` is True when a name/URL was seen.

    Names match when their keys are equal, or when one name's tokens are a
    subset of the other's and the smaller set has at least two tokens (so
    'Goldwater Scholarship' alone won't swallow unrelated listings, but
    'Barry Goldwater' matches 'Barry M. Goldwater Excellence in Education')."""

    def __init__(self):
        self._token_sets = []
        self._urls = set()

    def is_duplicate(self, name: str, url: str = '') -> bool:
        tokens = name_tokens(name)
        u = url_key(url)
        if u and u in self._urls:
            return True
        for seen in self._token_sets:
            if tokens == seen:
                return True
            small, large = (tokens, seen) if len(tokens) <= len(seen) else (seen, tokens)
            if len(small) >= 2 and small <= large:
                return True
        return False

    def add(self, name: str, url: str = ''):
        self._token_sets.append(name_tokens(name))
        u = url_key(url)
        if u:
            self._urls.add(u)

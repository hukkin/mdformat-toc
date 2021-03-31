from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import NamedTuple


class Heading(NamedTuple):
    level: int
    text: str
    slug: str
    markdown: str


class HeadingTree:
    _parents: Mapping[Heading, Heading | None]

    def __init__(self, headings: Iterable[Heading]):
        self.headings = tuple(headings)

    @property
    def headings(self) -> tuple[Heading, ...]:
        return self._headings

    @headings.setter
    def headings(self, headings: tuple[Heading, ...]) -> None:
        self._headings = headings
        self._parents = {
            heading: self._get_parent(i) for i, heading in enumerate(headings)
        }

    def _get_parent(self, child_idx: int) -> Heading | None:
        child = self.headings[child_idx]
        for heading in reversed(self.headings[:child_idx]):
            if heading.level < child.level:
                return heading
        return None

    def get_indentation_level(self, heading: Heading) -> int:
        level = 0
        ancestor = self._parents[heading]
        while ancestor is not None:
            level += 1
            ancestor = self._parents[ancestor]
        return level

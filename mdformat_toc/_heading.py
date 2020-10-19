from typing import Iterable, Mapping, NamedTuple, Optional, Tuple


class Heading(NamedTuple):
    level: int
    text: str
    slug: str
    markdown: str


class HeadingTree:
    def __init__(self, headings: Iterable[Heading]):
        self._parents: Mapping[Heading, Optional[Heading]] = {}
        self.headings = tuple(headings)

    @property
    def headings(self) -> Tuple[Heading, ...]:
        return self._headings

    @headings.setter
    def headings(self, headings: Tuple[Heading, ...]) -> None:
        self._headings = headings
        self._set_parents()

    def _set_parents(self) -> None:
        self._parents = {}
        for i, heading in enumerate(self.headings):
            self._parents[heading] = self._get_parent(i)

    def _get_parent(self, child_idx: int) -> Optional[Heading]:
        child = self.headings[child_idx]
        for i in reversed(range(child_idx)):
            if self.headings[i].level < child.level:
                return self.headings[i]
        return None

    def get_indentation_level(self, heading: Heading) -> int:
        level = 0
        ancestor = self._parents[heading]
        while ancestor is not None:
            level += 1
            ancestor = self._parents[ancestor]
        return level

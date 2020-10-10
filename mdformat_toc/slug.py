import collections
import re
from typing import Callable, Counter, Mapping
import urllib.parse


def get_unique_slugify(slug_func: Callable[[str, int], str]) -> Callable[[str], str]:
    title_counts: Counter[str] = collections.Counter()

    def unique_slugify(title: str) -> str:
        slug = slug_func(title, title_counts[title])
        title_counts[title] += 1
        return slug

    return unique_slugify


def slugify_github(title: str, repetition: int) -> str:
    title = title.strip().lower()

    title = title.replace(" ", "-")

    # Remove hex codes (e.g. "%9f")
    title = re.sub("%[A-Fa-f0-9]{2}", "", title)

    # Remove a set of single characters
    title = re.sub("[/?!:\\[\\]`.,()*\"';{}+=<>~$|#&@\\t]", "", title)

    title = urllib.parse.quote_plus(title)
    if repetition:
        title += f"-{repetition}"
    return title


def slugify_gitlab(title: str, repetition: int) -> str:
    """Create a slug like Gitlab would.

    See https://github.com/gitlabhq/gitlabhq/blob/master/doc/user/markdown.md#header-ids-and-links  # noqa: E501
    """
    title = title.strip().lower()

    title = title.replace(" ", "-")

    # Remove everything except:
    #   - Unicode word characters
    #   - Chinese characters
    #   - Hyphen (-)
    title = re.sub(r"[^\w\u4e00-\u9fff\-]", "", title)

    # Convert two or more hyphens in a row to one
    title = re.sub("-{2,}", "-", title)

    title = urllib.parse.quote_plus(title)
    if repetition:
        title += f"-{repetition}"
    return title


SLUG_FUNCS: Mapping[str, Callable[[str, int], str]] = {
    "github": slugify_github,
    "gitlab": slugify_gitlab,
}

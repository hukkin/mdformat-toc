import re
from typing import Callable, Iterable, Optional, Set

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token


def anchors_plugin(
    md: MarkdownIt,
    min_level: int = 1,
    max_level: int = 2,
    slug_func: Optional[Callable[[str], str]] = None,
    permalinkSymbol: str = "",
) -> None:
    """Plugin for adding header anchors, based on.

    <https://github.com/valeriangalliat/markdown-it-anchor>.
    """
    selected_levels = range(min_level, max_level + 1)
    md.core.ruler.push(
        "anchor",
        _make_anchors_func(
            selected_levels,
            slug_func or slugify,
            permalinkSymbol,
        ),
    )


def _make_anchors_func(  # noqa: C901
    selected_levels: Iterable[int],
    slug_func: Callable[[str], str],
    permalinkSymbol: str,
) -> Callable[[StateCore], None]:
    slugs: Set[str] = set()

    def _anchor_func(state: StateCore) -> None:
        for (idx, token) in enumerate(state.tokens):
            if token.type != "heading_open":
                continue
            level = int(token.tag[1])
            if level not in selected_levels:
                continue
            title = "".join(
                child.content
                for child in state.tokens[idx + 1].children
                if child.type in ["text", "code_inline"]
            )
            slug = unique_slug(slug_func(title), slugs)

            # Remove possible existing anchor
            anchor_start_idx = None
            anchor_end_idx = None
            for inline_idx, inline_token in enumerate(state.tokens[idx + 1].children):
                if inline_token.type != "html_inline":
                    continue
                if re.match(r"<a\s", inline_token.content):
                    anchor_start_idx = inline_idx
                    anchor_end_idx = inline_idx
                if anchor_start_idx is not None and inline_token.content == "</a>":
                    anchor_end_idx = inline_idx
            if anchor_start_idx is not None:
                assert anchor_end_idx is not None
                state.tokens[idx + 1].children = (
                    state.tokens[idx + 1].children[:anchor_start_idx]
                    + state.tokens[idx + 1].children[anchor_end_idx + 1 :]
                )
                # Remove the trailing whitespace from the heading
                if (
                    anchor_start_idx != 0
                    and state.tokens[idx + 1].children[anchor_start_idx - 1].type
                    == "text"
                ):
                    state.tokens[idx + 1].children[anchor_start_idx - 1].content = (
                        state.tokens[idx + 1]
                        .children[anchor_start_idx - 1]
                        .content.rstrip()
                    )

            # Add the type of anchor we want
            link_tokens = [
                Token("html_inline", "", 0, content=f'<a name="#{slug}">'),
                Token("text", "", 0, content=permalinkSymbol),
                Token("html_inline", "", 0, content="</a>"),
            ]
            state.tokens[idx + 1].children += link_tokens

    return _anchor_func


def slugify(title: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff\- ]", "", title.strip().lower().replace(" ", "-"))


def unique_slug(slug: str, slugs: set) -> str:
    uniq = slug
    i = 1
    while uniq in slugs:
        uniq = f"{slug}-{i}"
        i += 1
    slugs.add(uniq)
    return uniq

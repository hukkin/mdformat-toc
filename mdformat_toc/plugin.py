import itertools
import re
from typing import Any, Mapping, Optional, Sequence, Tuple

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdformat.renderer import LOGGER, MDRenderer

import mdformat_toc
from mdformat_toc._heading import Heading, HeadingTree
from mdformat_toc._options import Opts
from mdformat_toc._tokens import (
    copy_block_tokens,
    find_toc_end_token,
    find_toc_start_token,
    index_closing_token,
    is_toc_start,
)
from mdformat_toc.slug import SLUG_FUNCS, get_unique_slugify

CHANGES_AST = True


def update_mdit(_mdit: MarkdownIt) -> None:
    pass


def render_token(
    renderer: MDRenderer,
    tokens: Sequence[Token],
    index: int,
    options: Mapping[str, Any],
    env: dict,
) -> Optional[Tuple[str, int]]:
    first_pass = "mdformat-toc" not in env
    if first_pass:
        env["mdformat-toc"] = {"rendered_headings": 0, "opts": None}

        # Load ToC options
        toc_start_index = find_toc_start_token(tokens)
        if toc_start_index is None:
            return None
        second_toc_start_index = find_toc_start_token(
            tokens, start_from=toc_start_index + 1
        )
        if second_toc_start_index is not None:
            LOGGER.warning(
                "Mdformat-toc found more than one ToC indicator lines. "
                "Only one is supported by the plugin. "
                "Mdformat-toc disabled."
            )
            return None
        env["mdformat-toc"]["opts"] = Opts.from_start_token(tokens[toc_start_index])

        # Load heading structure
        toc_end_index = find_toc_end_token(tokens, toc_start_index)
        if toc_end_index is None:
            no_toc_tokens: Sequence[Token] = tokens
        else:
            no_toc_tokens = tuple(
                itertools.chain(tokens[:toc_start_index], tokens[toc_end_index + 1 :])
            )
        env["mdformat-toc"]["headings"] = _load_headings(
            renderer, no_toc_tokens, options, env
        )

    opts = env["mdformat-toc"]["opts"]
    if not opts:
        return None

    token = tokens[index]

    if is_toc_start(token):
        text = f"<!-- mdformat-toc start {opts} -->\n\n"
        toc_end_index = find_toc_end_token(tokens, index)
        last_consumed_index = toc_end_index if toc_end_index is not None else index

        text += _render_toc(
            env["mdformat-toc"]["headings"],
            minlevel=opts.minlevel,
            maxlevel=opts.maxlevel,
        )
        text += "\n<!-- mdformat-toc end -->\n\n"

        return text, last_consumed_index
    if token.type == "heading_open":
        heading_idx = env["mdformat-toc"]["rendered_headings"]
        heading = env["mdformat-toc"]["headings"].headings[heading_idx]
        env["mdformat-toc"]["rendered_headings"] += 1
        return heading.markdown, index_closing_token(tokens, index)
    return None


def _render_toc(
    heading_tree: HeadingTree,
    *,
    minlevel: int,
    maxlevel: int,
) -> str:
    toc = ""

    # Filter unwanted heading levels
    heading_tree = HeadingTree(
        h for h in heading_tree.headings if minlevel <= h.level <= maxlevel
    )

    for heading in heading_tree.headings:
        indentation = "  " * heading_tree.get_indentation_level(heading)
        toc += f"{indentation}- [{heading.text}](<#{heading.slug}>)\n"

    return toc


def _load_headings(
    renderer: MDRenderer, tokens: Sequence[Token], options: Mapping[str, Any], env: dict
) -> HeadingTree:
    toc_opts = env["mdformat-toc"]["opts"]
    unique_slugify = get_unique_slugify(SLUG_FUNCS[toc_opts.slug_style])
    headings = []
    for i, tkn in enumerate(tokens):
        if tkn.type != "heading_open":
            continue
        level = int(tkn.tag[1:])

        # Copy heading tokens so we can safely mutate them
        heading_tokens = copy_block_tokens(tokens, i)
        if (
            env["mdformat-toc"]["opts"].anchors
            and toc_opts.minlevel <= level <= toc_opts.maxlevel
        ):
            _ensure_anchors_in_place(heading_tokens)

        # Collect heading text from the children of the inline token
        heading_text = ""
        for child in heading_tokens[1].children:
            if child.type == "text":
                heading_text += child.content
            elif child.type == "code_inline":
                heading_text += "`" + child.content + "`"
        # There can be newlines in setext headers. Convert newlines to spaces.
        heading_text = heading_text.replace("\n", " ").rstrip()

        slug = unique_slugify(heading_text)

        # Place the correct slug in tokens so that it is included in
        # the rendered Markdown
        for child in heading_tokens[1].children:
            if child.type == "html_inline" and child.content == '<a name="{slug}">':
                child.content = child.content.format(slug=slug)

        # Render heading Markdown (with mdformat-toc disabled)
        options["parser_extension"].remove(mdformat_toc.plugin)
        heading_md = renderer.render(heading_tokens, options, env, finalize=False)
        options["parser_extension"].append(mdformat_toc.plugin)

        headings.append(
            Heading(
                level=level,
                text=heading_text,
                slug=slug,
                markdown=heading_md,
            )
        )

    return HeadingTree(headings)


def _ensure_anchors_in_place(heading_tokens: Sequence[Token]) -> None:
    """Mutate heading tokens so that HTML anchors are in place.

    Add HTML anchor to heading token sequence if it is not already
    there. Don't add the slug value, we don't know it yet. The slug
    value will have to be inserted after calling this.
    """
    # Remove possible existing anchor
    anchor_start_idx = None
    anchor_end_idx = None
    inline_root = heading_tokens[1]
    for child_idx, child_tkn in enumerate(inline_root.children):
        if child_tkn.type != "html_inline":
            continue
        if re.match(r"<a\s", child_tkn.content):
            anchor_start_idx = child_idx
            anchor_end_idx = child_idx
        if anchor_start_idx is not None and child_tkn.content == "</a>":
            anchor_end_idx = child_idx
    if anchor_start_idx is not None:
        assert anchor_end_idx is not None
        inline_root.children = (
            inline_root.children[:anchor_start_idx]
            + inline_root.children[anchor_end_idx + 1 :]
        )
        # Remove trailing whitespace from the heading
        if (
            anchor_start_idx != 0
            and inline_root.children[anchor_start_idx - 1].type == "text"
        ):
            inline_root.children[anchor_start_idx - 1].content = inline_root.children[
                anchor_start_idx - 1
            ].content.rstrip()

    # Add the type of anchor we want
    anchor_text = ""
    link_tokens = [
        Token("html_inline", "", 0, content='<a name="{slug}">'),
        Token("text", "", 0, content=anchor_text),
        Token("html_inline", "", 0, content="</a>"),
    ]
    inline_root.children += link_tokens

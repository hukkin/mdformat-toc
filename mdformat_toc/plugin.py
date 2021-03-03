from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
import itertools
import re
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdformat.renderer import DEFAULT_RENDERER_FUNCS, LOGGER, RenderTreeNode
from mdformat.renderer.typing import RendererFunc

from mdformat_toc._heading import Heading, HeadingTree
from mdformat_toc._options import Opts
from mdformat_toc._tokens import (
    copy_block_tokens,
    find_toc_end_sibling,
    find_toc_end_token,
    find_toc_start_nodes,
    find_toc_start_token,
    is_toc_start_node,
)
from mdformat_toc.slug import SLUG_FUNCS, get_unique_slugify

CHANGES_AST = True


def update_mdit(_mdit: MarkdownIt) -> None:
    pass


def _init_toc(
    root: RenderTreeNode,
    renderer_funcs: Mapping[str, RendererFunc],
    options: Mapping[str, Any],
    env: MutableMapping,
) -> bool:
    """Initialize ToC plugin.

    Store ToC options and heading structure in `env` if valid ToC
    options found. Returns `True` if valid ToC options were found, else
    returns `False`.
    """
    env["mdformat-toc"] = {"rendered_headings": 0, "opts": None}

    tokens = root.to_tokens()

    # Load ToC options
    toc_start_index = find_toc_start_token(tokens)
    if toc_start_index is None:
        return False
    second_toc_start_index = find_toc_start_token(
        tokens, start_from=toc_start_index + 1
    )
    if second_toc_start_index is not None:
        LOGGER.warning(
            "Mdformat-toc found more than one ToC indicator lines. "
            "Only one is supported by the plugin. "
            "Mdformat-toc disabled."
        )
        return False
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
        renderer_funcs, no_toc_tokens, options, env
    )
    return True


def _toc_enabled(env: MutableMapping) -> bool:
    opts = env["mdformat-toc"]["opts"]
    return bool(opts)


def _render_root(
    node: RenderTreeNode,
    renderer_funcs: Mapping[str, RendererFunc],
    options: Mapping[str, Any],
    env: MutableMapping,
) -> str:
    toc_enabled = _init_toc(node, renderer_funcs, options, env)
    if toc_enabled:
        (toc_start_node,) = find_toc_start_nodes(node)
        assert toc_start_node.parent is not None, "toc start cant be root"
        toc_end_node = find_toc_end_sibling(toc_start_node)
        if toc_end_node:
            toc_start_index = toc_start_node.siblings.index(toc_start_node)
            toc_end_index = toc_start_node.siblings.index(toc_end_node)
            toc_start_node.parent.children = (
                toc_start_node.parent.children[: toc_start_index + 1]
                + toc_start_node.parent.children[toc_end_index + 1 :]
            )
    return DEFAULT_RENDERER_FUNCS["root"](node, renderer_funcs, options, env)


def _render_heading(
    node: RenderTreeNode,
    renderer_funcs: Mapping[str, RendererFunc],
    options: Mapping[str, Any],
    env: MutableMapping,
) -> str:
    if not _toc_enabled(env):
        DEFAULT_RENDERER_FUNCS["heading"](node, renderer_funcs, options, env)

    heading_idx = env["mdformat-toc"]["rendered_headings"]
    heading = env["mdformat-toc"]["headings"].headings[heading_idx]
    env["mdformat-toc"]["rendered_headings"] += 1
    return heading.markdown


def _render_html_block(
    node: RenderTreeNode,
    renderer_funcs: Mapping[str, RendererFunc],
    options: Mapping[str, Any],
    env: MutableMapping,
) -> str:
    if not _toc_enabled(env) or not is_toc_start_node(node):
        DEFAULT_RENDERER_FUNCS["html_block"](node, renderer_funcs, options, env)

    opts = env["mdformat-toc"]["opts"]
    text = f"<!-- mdformat-toc start {opts} -->\n\n"
    # toc_end_index = find_toc_end_token(tokens, index)
    # last_consumed_index = toc_end_index if toc_end_index is not None else index

    text += _render_toc(
        env["mdformat-toc"]["headings"],
        minlevel=opts.minlevel,
        maxlevel=opts.maxlevel,
    )
    text += "\n<!-- mdformat-toc end -->"

    return text


RENDERER_FUNCS = {
    "root": _render_root,
    "html_block": _render_html_block,
    "heading": _render_heading,
}


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
    renderer_funcs: Mapping[str, RendererFunc],
    tokens: Sequence[Token],
    options: Mapping[str, Any],
    env: MutableMapping,
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
        inline_token = heading_tokens[1]
        assert (
            inline_token.children is not None
        ), "inline token's children must not be None"
        heading_text = ""
        for child in inline_token.children:
            if child.type == "text":
                heading_text += child.content
            elif child.type == "code_inline":
                heading_text += "`" + child.content + "`"
        # There can be newlines in setext headers. Convert newlines to spaces.
        heading_text = heading_text.replace("\n", " ").rstrip()

        slug = unique_slugify(heading_text)

        # Place the correct slug in tokens so that it is included in
        # the rendered Markdown
        for child in inline_token.children:
            if child.type == "html_inline" and child.content == '<a name="{slug}">':
                child.content = child.content.format(slug=slug)

        # Render heading Markdown (with mdformat-toc disabled)
        toc_disabled_renderer_funcs = {
            **renderer_funcs,
            "heading": DEFAULT_RENDERER_FUNCS["heading"],
            "html_block": DEFAULT_RENDERER_FUNCS["html_block"],
            "root": DEFAULT_RENDERER_FUNCS["root"],
        }
        heading_md = RenderTreeNode(heading_tokens).render(
            toc_disabled_renderer_funcs, options, env
        )

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
    assert inline_root.children is not None, "inline token's children must not be None"
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

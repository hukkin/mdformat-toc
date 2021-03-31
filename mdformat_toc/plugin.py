from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
import re
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdformat import codepoints
from mdformat.renderer import DEFAULT_RENDERER_FUNCS, LOGGER, RenderTreeNode
from mdformat.renderer.typing import RendererFunc

from mdformat_toc._heading import Heading, HeadingTree
from mdformat_toc._options import Opts
from mdformat_toc._tokens import (
    copy_block_tokens,
    find_toc_end_sibling,
    find_toc_start_nodes,
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
) -> None:
    """Initialize ToC plugin.

    Store ToC options and heading structure in `env` if valid ToC
    options found.
    """
    assert root.type == "root"
    env["mdformat-toc"] = {"rendered_headings": 0, "opts": None}

    # Load ToC options
    toc_start_nodes = find_toc_start_nodes(root)
    if not toc_start_nodes:
        return
    if len(toc_start_nodes) > 1:
        LOGGER.warning(
            "Mdformat-toc found more than one ToC indicator lines. "
            "Only one is supported by the plugin. "
            "Mdformat-toc disabled."
        )
        return
    (toc_start_node,) = toc_start_nodes
    env["mdformat-toc"]["opts"] = Opts.from_start_node(toc_start_node)

    # Remove ToC related nodes (besides ToC start node) from the tree.
    # We regenerate and render an up-to-date ToC every time, so if the
    # old nodes are there, the ToC will be rendered twice.
    assert toc_start_node.parent is not None, "toc start cant be root"
    toc_end_node = find_toc_end_sibling(toc_start_node)
    if toc_end_node:
        siblings = toc_start_node.parent.children
        toc_start_index = siblings.index(toc_start_node)
        toc_end_index = siblings.index(toc_end_node)
        toc_start_node.parent.children = (
            siblings[: toc_start_index + 1] + siblings[toc_end_index + 1 :]
        )

    # Load heading structure
    env["mdformat-toc"]["headings"] = _load_headings(renderer_funcs, root, options, env)


def _toc_enabled(env: MutableMapping) -> bool:
    """Is there a valid ToC definition in the Markdown?"""
    opts = env["mdformat-toc"]["opts"]
    return bool(opts)


def _render_root(
    node: RenderTreeNode,
    renderer_funcs: Mapping[str, RendererFunc],
    options: Mapping[str, Any],
    env: MutableMapping,
) -> str:
    _init_toc(node, renderer_funcs, options, env)
    return DEFAULT_RENDERER_FUNCS["root"](node, renderer_funcs, options, env)


def _render_heading(
    node: RenderTreeNode,
    renderer_funcs: Mapping[str, RendererFunc],
    options: Mapping[str, Any],
    env: MutableMapping,
) -> str:
    if not _toc_enabled(env):
        return DEFAULT_RENDERER_FUNCS["heading"](node, renderer_funcs, options, env)

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
        return DEFAULT_RENDERER_FUNCS["html_block"](node, renderer_funcs, options, env)

    opts = env["mdformat-toc"]["opts"]
    text = f"<!-- mdformat-toc start {opts} -->\n\n"

    toc = _render_toc(
        env["mdformat-toc"]["headings"],
        minlevel=opts.minlevel,
        maxlevel=opts.maxlevel,
    )
    if toc:
        text += toc + "\n"

    text += "<!-- mdformat-toc end -->"

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
        uri = _maybe_add_link_brackets("#" + heading.slug)
        toc += f"{indentation}- [{heading.text}]({uri})\n"

    return toc


def _load_headings(
    renderer_funcs: Mapping[str, RendererFunc],
    root: RenderTreeNode,
    options: Mapping[str, Any],
    env: MutableMapping,
) -> HeadingTree:
    tokens = root.to_tokens()
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
            name: DEFAULT_RENDERER_FUNCS[name] if name in RENDERER_FUNCS else func
            for name, func in renderer_funcs.items()
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


def _maybe_add_link_brackets(link: str) -> str:
    """Surround URI with brackets if required by the CommonMark spec."""
    if not link or (
        codepoints.ASCII_CTRL | codepoints.ASCII_WHITESPACE | {"(", ")"}
    ).intersection(link):
        return "<" + link + ">"
    return link

from __future__ import annotations

import copy
import itertools
import re
from typing import Any, Iterable, List, Mapping, NamedTuple, Optional, Sequence, Tuple

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdformat.renderer import MDRenderer

import mdformat_toc
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
        env["mdformat-toc"] = {"rendered_headings": 0}

        # Load ToC options
        toc_start_tkn_index = _find_toc_start_token(tokens)
        if toc_start_tkn_index is None:
            env["mdformat-toc"]["opts"] = None
            return None
        env["mdformat-toc"]["opts"] = _Args.from_start_token(
            tokens[toc_start_tkn_index]
        )

        # Load heading structure
        toc_end_tkn_index = _find_toc_end_token(tokens, toc_start_tkn_index)
        if toc_end_tkn_index is None:
            no_toc_tokens: Sequence[Token] = tokens
        else:
            no_toc_tokens = tuple(
                itertools.chain(
                    tokens[:toc_start_tkn_index], tokens[toc_end_tkn_index + 1 :]
                )
            )
        env["mdformat-toc"]["headings"] = _load_headings(
            renderer, no_toc_tokens, options, env
        )

    opts = env["mdformat-toc"]["opts"]
    if not opts:
        return None

    token = tokens[index]

    if _is_toc_start(token):
        text = f"<!-- mdformat-toc start {opts} -->\n\n"
        toc_end_tkn_index = _find_toc_end_token(tokens, index)
        last_consumed_index = (
            toc_end_tkn_index if toc_end_tkn_index is not None else index
        )

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
        return heading.markdown, _index_closing_token(tokens, index)
    return None


class _HeadingTree:
    def __init__(self, headings: Iterable[_Heading]):
        self._parents: Mapping[_Heading, Optional[_Heading]] = {}
        self.headings = tuple(headings)

    @property
    def headings(self) -> Tuple[_Heading, ...]:
        return self._headings

    @headings.setter
    def headings(self, headings: Tuple[_Heading, ...]) -> None:
        self._headings = headings
        self._set_parents()

    def _set_parents(self) -> None:
        self._parents = {}
        for i, heading in enumerate(self.headings):
            self._parents[heading] = self._get_parent(i)

    def _get_parent(self, child_idx: int) -> Optional[_Heading]:
        child = self.headings[child_idx]
        for i in reversed(range(child_idx)):
            if self.headings[i].level < child.level:
                return self.headings[i]
        return None

    def get_indentation_level(self, heading: _Heading) -> int:
        level = 0
        ancestor = self._parents[heading]
        while ancestor is not None:
            level += 1
            ancestor = self._parents[ancestor]
        return level


class _Heading(NamedTuple):
    level: int
    text: str
    slug: str
    markdown: str


def _render_toc(
    heading_tree: _HeadingTree,
    *,
    minlevel: int,
    maxlevel: int,
) -> str:
    toc = ""

    # Filter unwanted heading levels
    heading_tree = _HeadingTree(
        h for h in heading_tree.headings if minlevel <= h.level <= maxlevel
    )

    for heading in heading_tree.headings:
        indentation = "  " * heading_tree.get_indentation_level(heading)
        toc += f"{indentation}- [{heading.text}](<#{heading.slug}>)\n"

    return toc


def _is_toc_start(token: Token) -> bool:
    if token.type != "html_block":
        return False
    args_seq = _get_args_sequence(token)
    if len(args_seq) < 2:
        return False
    if args_seq[0].lower() != "mdformat-toc" or args_seq[1].lower() != "start":
        return False
    return True


def _find_toc_start_token(tokens: Sequence[Token]) -> Optional[int]:
    for i, tkn in enumerate(tokens):
        if _is_toc_start(tkn):
            return i
    return None


def _find_toc_end_token(tokens: Sequence[Token], start_index: int) -> Optional[int]:
    start_tkn = tokens[start_index]
    for i in range(start_index + 1, len(tokens)):
        tkn = tokens[i]
        if tkn.type != "html_block" or tkn.level != start_tkn.level:
            continue
        args_seq = _get_args_sequence(tkn)
        if (
            len(args_seq) >= 2
            and args_seq[0].lower() == "mdformat-toc"
            and args_seq[1].lower() == "end"
        ):
            return i
    return None


def _get_args_sequence(token: Token) -> List[str]:
    assert token.type == "html_block"
    args_str = token.content.rstrip("\n")
    if args_str.startswith("<!--"):
        args_str = args_str[4:]
    if args_str.endswith("-->"):
        args_str = args_str[:-3]
    return args_str.split()


class _Args:
    """Arg parser for the TOC.

    Parse TOC args from a sequence of strings. Allow setting default
    values.
    """

    def __init__(self, args_seq: Sequence[str]):
        self.minlevel = 1
        self.maxlevel = 6
        self._int_args_names = ("maxlevel", "minlevel")
        for arg in args_seq:
            for int_arg_name in self._int_args_names:
                if arg.startswith(f"--{int_arg_name}="):
                    try:
                        int_value = int(arg[len(f"--{int_arg_name}=") :])
                    except ValueError:
                        continue
                    setattr(self, int_arg_name, int_value)

        self.slug_style = "github"
        for arg in args_seq:
            if arg.startswith("--slug="):
                style = arg[len("--slug=") :]
                if style in SLUG_FUNCS:
                    self.slug_style = style

        self.anchors = "--no-anchors" not in args_seq

    def __str__(self) -> str:
        """Return a string that when str.split() and passed to _Args.__init__,
        will reconstruct an equivalent object."""
        args_str = f"--slug={self.slug_style}"
        if not self.anchors:
            args_str += " --no-anchors"
        int_args_str = " ".join(
            f"--{int_arg_name}={getattr(self, int_arg_name)}"
            for int_arg_name in self._int_args_names
        )
        if int_args_str:
            args_str += " " + int_args_str
        return args_str

    @staticmethod
    def from_start_token(token: Token) -> _Args:
        args_seq = _get_args_sequence(token)
        opts = args_seq[2:]
        return _Args(opts)


def _load_headings(
    renderer: MDRenderer, tokens: Sequence[Token], options: Mapping[str, Any], env: dict
) -> _HeadingTree:
    toc_opts = env["mdformat-toc"]["opts"]
    unique_slugify = get_unique_slugify(SLUG_FUNCS[toc_opts.slug_style])
    headings = []
    for i, tkn in enumerate(tokens):
        if tkn.type != "heading_open":
            continue
        level = int(tkn.tag[1:])

        # Copy heading tokens so we can safely mutate them
        heading_tokens = _copy_heading_tokens(tokens, i)
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
            _Heading(
                level=level,
                text=heading_text,
                slug=slug,
                markdown=heading_md,
            )
        )

    return _HeadingTree(headings)


def _copy_heading_tokens(
    tokens: Sequence[Token], opening_index: int
) -> Sequence[Token]:
    closing_index = _index_closing_token(tokens, opening_index)
    return copy.deepcopy(tokens[opening_index : closing_index + 1])


def _index_closing_token(tokens: Sequence[Token], opening_index: int) -> int:
    opening_token = tokens[opening_index]
    assert opening_token.nesting == 1, "Cant find closing token for non opening token"
    for i in range(opening_index + 1, len(tokens)):
        closing_candidate = tokens[i]
        if closing_candidate.level == opening_token.level:
            return i
    raise ValueError("Invalid token list. Closing token not found.")


def _ensure_anchors_in_place(heading_tokens: Sequence[Token]) -> None:
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

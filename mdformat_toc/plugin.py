from __future__ import annotations

import itertools
from typing import Any, Iterable, List, Mapping, NamedTuple, Optional, Sequence, Tuple

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdformat.renderer import MDRenderer

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
        env["mdformat-toc"] = {}

        toc_start_tkn_index = _find_toc_start_token(tokens)
        if toc_start_tkn_index is None:
            env["mdformat-toc"]["opts"] = None
            return None
        env["mdformat-toc"]["opts"] = _Args.from_start_token(
            tokens[toc_start_tkn_index]
        )

        toc_end_tkn_index = _find_toc_end_token(tokens, toc_start_tkn_index)
        if toc_end_tkn_index is None:
            no_toc_tokens: Sequence[Token] = tokens
        else:
            no_toc_tokens = tuple(
                itertools.chain(
                    tokens[:toc_start_tkn_index], tokens[toc_end_tkn_index + 1 :]
                )
            )
        env["mdformat-toc"]["headings"] = load_headings(
            no_toc_tokens, slug_style=env["mdformat-toc"]["opts"].slug_style
        )

    if not env["mdformat-toc"]["opts"]:
        return None

    token = tokens[index]

    if _is_toc_start(token):
        opts = env["mdformat-toc"]["opts"]

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
        # TODO: render heading with anchor here
        return None
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


def _render_toc(
    heading_tree: _HeadingTree,
    *,
    minlevel: int,
    maxlevel: int,
) -> str:
    toc = ""

    # Filter unwanted heading levels
    headings = _HeadingTree(
        h for h in heading_tree.headings if minlevel <= h.level <= maxlevel
    )

    for heading in headings.headings:
        indentation = "  " * headings.get_indentation_level(heading)
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

    def __str__(self) -> str:
        """Return a string that when str.split() and passed to _Args.__init__,
        will reconstruct an equivalent object."""
        return f"--slug={self.slug_style} " + " ".join(
            f"--{int_arg_name}={getattr(self, int_arg_name)}"
            for int_arg_name in self._int_args_names
        )

    @staticmethod
    def from_start_token(token: Token) -> _Args:
        args_seq = _get_args_sequence(token)
        opts = args_seq[2:]
        return _Args(opts)


def load_headings(tokens: Sequence[Token], *, slug_style: str) -> _HeadingTree:
    unique_slugify = get_unique_slugify(SLUG_FUNCS[slug_style])
    headings = []
    for i, tkn in enumerate(tokens):
        if tkn.type != "heading_open":
            continue

        # Collect heading text from the children of the inline token
        heading_text = ""
        for child in tokens[i + 1].children:
            if child.type == "text":
                heading_text += child.content
            elif child.type == "code_inline":
                heading_text += "`" + child.content + "`"
        # There can be newlines in setext headers. Convert newlines to spaces.
        heading_text = heading_text.replace("\n", " ").rstrip()

        headings.append(
            _Heading(
                level=int(tkn.tag[1:]),
                text=heading_text,
                slug=unique_slugify(heading_text),
            )
        )

    return _HeadingTree(headings)

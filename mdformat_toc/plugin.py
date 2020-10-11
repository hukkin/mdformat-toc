import itertools
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdformat.renderer import MDRenderer

from mdformat_toc.markdown_it_extension import anchors_plugin
from mdformat_toc.slug import SLUG_FUNCS, get_unique_slugify

CHANGES_AST = True


def update_mdit(mdit: MarkdownIt) -> None:
    mdit.use(anchors_plugin, min_level=1, max_level=6)


def render_token(
    renderer: MDRenderer,
    tokens: Sequence[Token],
    index: int,
    options: Mapping[str, Any],
    env: dict,
) -> Optional[Tuple[str, int]]:
    token = tokens[index]
    if token.type != "html_block":
        return None
    args_seq = _get_args_sequence(token)
    if len(args_seq) < 2:
        return None
    if args_seq[0].lower() != "mdformat-toc" or args_seq[1].lower() != "start":
        return None
    opts = args_seq[2:]
    parsed_opts = _Args(opts)

    text = f"<!-- mdformat-toc start {parsed_opts} -->\n\n"
    toc_end_tkn_index = _find_toc_end_token(tokens, index)
    if toc_end_tkn_index is None:
        last_consumed_index = index
        parse_headings_tokens: Sequence[Token] = tokens
    else:
        last_consumed_index = toc_end_tkn_index
        parse_headings_tokens = tuple(
            itertools.chain(tokens[:index], tokens[toc_end_tkn_index + 1 :])
        )

    text += _render_toc(
        renderer,
        parse_headings_tokens,
        options,
        env,
        minlevel=parsed_opts.minlevel,
        maxlevel=parsed_opts.maxlevel,
        slug_style=parsed_opts.slug_style,
    )
    text += "\n<!-- mdformat-toc end -->\n\n"

    return text, last_consumed_index


class _Heading:
    def __init__(self, level: int, text: str):
        self.level = level
        self.text = text
        self.parent: Optional[_Heading] = None

    def set_parent(self, heading_sequence: Sequence, self_index: int) -> None:
        for i in reversed(range(self_index)):
            if heading_sequence[i].level < self.level:
                self.parent = heading_sequence[i]
                return
        self.parent = None

    def get_indentation_level(self) -> int:
        level = 0
        ancestor = self.parent
        while ancestor is not None:
            level += 1
            ancestor = ancestor.parent
        return level


def _render_toc(
    renderer: MDRenderer,
    tokens: Sequence[Token],
    options: Mapping[str, Any],
    env: dict,
    *,
    minlevel: int,
    maxlevel: int,
    slug_style: str,
) -> str:
    toc = ""

    # Make a List[_Heading] of all the headings.
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
        headings.append(_Heading(level=int(tkn.tag[1:]), text=heading_text))

    # Filter unwanted heading levels
    headings = [h for h in headings if minlevel <= h.level <= maxlevel]

    # Set parent headings
    for i, heading in enumerate(headings):
        heading.set_parent(headings, i)

    unique_slugify = get_unique_slugify(SLUG_FUNCS[slug_style])
    for heading in headings:
        indentation = "  " * heading.get_indentation_level()
        slug = unique_slugify(heading.text)
        toc += f"{indentation}- [{heading.text}](<#{slug}>)\n"

    return toc


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

import itertools
import re
from typing import Any, List, Mapping, Optional, Sequence, Set, Tuple
import urllib.parse

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdformat.renderer import MDRenderer

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
) -> str:
    toc = ""

    # Make a List[_Heading] of all the headings.
    headings = []
    for i, tkn in enumerate(tokens):
        if tkn.type != "heading_open":
            continue
        closing_tkn_idx = _index_closing_token(tokens, i)
        heading_text = renderer.render(
            tokens[i + 1 : closing_tkn_idx], options, env, finalize=False
        )
        # There can be newlines in setext headers. Convert newlines to spaces.
        heading_text = heading_text.replace("\n", " ").rstrip()
        headings.append(_Heading(level=int(tkn.tag[1:]), text=heading_text))

    # Filter unwanted heading levels
    headings = [h for h in headings if minlevel <= h.level <= maxlevel]

    # Set parent headings
    for i, heading in enumerate(headings):
        heading.set_parent(headings, i)

    used_slugs: Set[str] = set()
    for heading in headings:
        indentation = "  " * heading.get_indentation_level()
        slug = _unique_slug(_slugify(heading.text), used_slugs)
        toc += f"{indentation}- [{heading.text}](<#{slug}>)\n"

    return toc


def _index_closing_token(tokens: Sequence[Token], opening_token_idx: int) -> int:
    opening_tkn = tokens[opening_token_idx]
    assert opening_tkn.nesting == 1, "Cant find closing token for non opening token"
    for i in range(opening_token_idx + 1, len(tokens)):
        closing_tkn_candidate = tokens[i]
        if closing_tkn_candidate.level == opening_tkn.level:
            return i
    raise ValueError("Invalid token list. Closing token not found.")


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

    def __str__(self) -> str:
        return " ".join(
            f"--{int_arg_name}={getattr(self, int_arg_name)}"
            for int_arg_name in self._int_args_names
        )


def _unique_slug(slug: str, used_slugs: Set[str]) -> str:
    unique = slug
    i = 1
    while unique in used_slugs:
        unique = f"{slug}-{i}"
        i += 1
    used_slugs.add(unique)
    return unique


def _slugify(title: str) -> str:
    title = title.strip().lower()
    title = re.sub(r"\s", "-", title)
    # Remove everything except:
    #   - Unicode word characters
    #   - Chinese characters
    #   - Hyphen (-)
    title = re.sub(r"[^\w\u4e00-\u9fff\-]", "", title)
    return urllib.parse.quote_plus(title)

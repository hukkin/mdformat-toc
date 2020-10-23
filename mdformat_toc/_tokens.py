"""A namespace for functions that process tokens (i.e. markdown_it.token.Token)
and token streams."""
import copy
from typing import List, Optional, Sequence

from markdown_it.token import Token


def get_args_sequence(token: Token) -> List[str]:
    assert token.type == "html_block"
    args_str = token.content.rstrip("\n")
    if args_str.startswith("<!--"):
        args_str = args_str[4:]
    if args_str.endswith("-->"):
        args_str = args_str[:-3]
    return args_str.split()


def is_toc_start(token: Token) -> bool:
    if token.type != "html_block":
        return False
    args_seq = get_args_sequence(token)
    if len(args_seq) < 2:
        return False
    if args_seq[0].lower() != "mdformat-toc" or args_seq[1].lower() != "start":
        return False
    return True


def find_toc_start_token(
    tokens: Sequence[Token], *, start_from: int = 0
) -> Optional[int]:
    for i, tkn in enumerate(tokens[start_from:], start=start_from):
        if is_toc_start(tkn):
            return i
    return None


def find_toc_end_token(tokens: Sequence[Token], start_index: int) -> Optional[int]:
    start_tkn = tokens[start_index]
    for i in range(start_index + 1, len(tokens)):
        tkn = tokens[i]
        if tkn.type != "html_block" or tkn.level != start_tkn.level:
            continue
        args_seq = get_args_sequence(tkn)
        if (
            len(args_seq) >= 2
            and args_seq[0].lower() == "mdformat-toc"
            and args_seq[1].lower() == "end"
        ):
            return i
    return None


def copy_block_tokens(tokens: Sequence[Token], opening_index: int) -> Sequence[Token]:
    closing_index = index_closing_token(tokens, opening_index)
    return copy.deepcopy(tokens[opening_index : closing_index + 1])


def index_closing_token(tokens: Sequence[Token], opening_index: int) -> int:
    opening_token = tokens[opening_index]
    assert opening_token.nesting == 1, "Cant find closing token for non opening token"
    for i in range(opening_index + 1, len(tokens)):
        closing_candidate = tokens[i]
        if closing_candidate.level == opening_token.level:
            return i
    raise ValueError("Invalid token list. Closing token not found.")

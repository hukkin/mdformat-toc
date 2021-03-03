"""A namespace for functions that process tokens (i.e. markdown_it.token.Token)
and token streams."""
from __future__ import annotations

from collections.abc import Callable, Sequence
import copy

from markdown_it.token import Token
from mdformat.renderer import RenderTreeNode


def get_args_sequence(node: RenderTreeNode) -> list[str]:
    assert node.type == "html_block"
    args_str = node.content.rstrip("\n")
    if args_str.startswith("<!--"):
        args_str = args_str[4:]
    if args_str.endswith("-->"):
        args_str = args_str[:-3]
    return args_str.split()


def is_toc_start_node(node: RenderTreeNode) -> bool:
    if node.type != "html_block":
        return False
    args_seq = get_args_sequence(node)
    if len(args_seq) < 2:
        return False
    if args_seq[0].lower() != "mdformat-toc" or args_seq[1].lower() != "start":
        return False
    return True


def find_toc_start_nodes(node: RenderTreeNode) -> list[RenderTreeNode]:
    start_nodes = []

    def append_toc_start(node: RenderTreeNode) -> None:
        if is_toc_start_node(node):
            start_nodes.append(node)

    for_all_nodes(node, append_toc_start)
    return start_nodes


def for_all_nodes(
    node: RenderTreeNode, action: Callable[[RenderTreeNode], None]
) -> None:
    action(node)
    for child in node.children:
        for_all_nodes(child, action)


def find_toc_end_sibling(node: RenderTreeNode) -> RenderTreeNode | None:
    sibling = node.next_sibling
    while sibling:
        if sibling.type == "html_block":
            args_seq = get_args_sequence(sibling)
            if (
                len(args_seq) >= 2
                and args_seq[0].lower() == "mdformat-toc"
                and args_seq[1].lower() == "end"
            ):
                return sibling
        sibling = sibling.next_sibling
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

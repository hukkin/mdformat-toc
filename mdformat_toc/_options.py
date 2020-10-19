from __future__ import annotations

from typing import Sequence

from markdown_it.token import Token

from mdformat_toc._tokens import get_args_sequence
from mdformat_toc.slug import SLUG_FUNCS


class Opts:
    """Option parser for the TOC.

    Parse TOC opts from a sequence of args. Allow setting default
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
        """Return a string that when str.split() and passed to Opts.__init__,
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
    def from_start_token(token: Token) -> Opts:
        args_seq = get_args_sequence(token)
        opts = args_seq[2:]
        return Opts(opts)

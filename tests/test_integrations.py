from pathlib import Path
import pytest

from markdown_it.utils import read_fixture_file
import mdformat

_TEST_CASES = read_fixture_file(
    Path(__file__).parent / "data" / "integration_fixtures.md"
)
_PLUGINS = {"toc", "mkdocs"}


@pytest.mark.parametrize(
    "line,title,text,expected", _TEST_CASES, ids=[f[1] for f in _TEST_CASES]
)
def test_integration_fixtures(line, title, text, expected):
    """Test fixtures in tests/data/integration_fixtures.md."""
    md_new = mdformat.text(text, extensions=_PLUGINS)
    if md_new != expected:
        print("Formatted (unexpected) Markdown below:")
        print(md_new)
    assert md_new == expected

import mdformat


def test_missing_heading_levels():
    unformatted_md = """<!-- mdformat-toc start -->

Level 1
=======

### Level  zwei

## Level 2 ., Azwei

## Level 2 .+ Az//&w_äöe-i

# Level 1
"""
    formatted_md = r"""<!-- mdformat-toc start --maxlevel=6 --minlevel=1 -->

- [Level 1](<#level-1>)
  - [Level  zwei](<#level--zwei>)
  - [Level 2 ., Azwei](<#level-2--azwei>)
  - [Level 2 .+ Az//&w\_äöe-i](<#level-2--azw_%C3%A4%C3%B6e-i>)
- [Level 1](<#level-1-1>)

<!-- mdformat-toc end -->

# Level 1

### Level  zwei

## Level 2 ., Azwei

## Level 2 .+ Az//&w\_äöe-i

# Level 1
"""
    assert mdformat.text(unformatted_md, extensions={"toc"}) == formatted_md


def test_empty_toc():
    unformatted_md = """<!-- mdformat-toc start -->

No headers.
No TOC in this file.
"""
    formatted_md = r"""<!-- mdformat-toc start --maxlevel=6 --minlevel=1 -->


<!-- mdformat-toc end -->

No headers.
No TOC in this file.
"""
    assert mdformat.text(unformatted_md, extensions={"toc"}) == formatted_md


def test_level_restrictions():
    unformatted_md = """<!-- mdformat-toc start --minlevel=2 --maxlevel=3 -->

# Level 1
## Level 2
### Level 3
#### Level 4
"""
    formatted_md = r"""<!-- mdformat-toc start --maxlevel=3 --minlevel=2 -->

- [Level 2](<#level-2>)
  - [Level 3](<#level-3>)

<!-- mdformat-toc end -->

# Level 1

## Level 2

### Level 3

#### Level 4
"""
    assert mdformat.text(unformatted_md, extensions={"toc"}) == formatted_md


def test_duplicate_title():
    unformatted_md = """<!-- mdformat-toc start -->
# Same name
# Same name
## Same name
### Same name
"""
    formatted_md = r"""<!-- mdformat-toc start --maxlevel=6 --minlevel=1 -->

- [Same name](<#same-name>)
- [Same name](<#same-name-1>)
  - [Same name](<#same-name-2>)
    - [Same name](<#same-name-3>)

<!-- mdformat-toc end -->

# Same name

# Same name

## Same name

### Same name
"""
    assert mdformat.text(unformatted_md, extensions={"toc"}) == formatted_md

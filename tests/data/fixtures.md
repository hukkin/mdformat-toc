HTML in heading
.
<!-- mdformat-toc start --no-anchors -->
# HTML here `<h1>lol</h1>`
.
<!-- mdformat-toc start --slug=github --no-anchors --maxlevel=6 --minlevel=1 -->

- [HTML here `<h1>lol</h1>`](<#html-here-h1lolh1>)

<!-- mdformat-toc end -->

# HTML here `<h1>lol</h1>`
.

Duplicate title
.
<!-- mdformat-toc start --no-anchors -->
# Same name
# Same name
## Same name
### Same name
.
<!-- mdformat-toc start --slug=github --no-anchors --maxlevel=6 --minlevel=1 -->

- [Same name](<#same-name>)
- [Same name](<#same-name-1>)
  - [Same name](<#same-name-2>)
    - [Same name](<#same-name-3>)

<!-- mdformat-toc end -->

# Same name

# Same name

## Same name

### Same name
.

Level restrictions
.
<!-- mdformat-toc start --no-anchors --minlevel=2 --maxlevel=3 -->

# Level 1
## Level 2
### Level 3
#### Level 4
.
<!-- mdformat-toc start --slug=github --no-anchors --maxlevel=3 --minlevel=2 -->

- [Level 2](<#level-2>)
  - [Level 3](<#level-3>)

<!-- mdformat-toc end -->

# Level 1

## Level 2

### Level 3

#### Level 4
.

Empty ToC
.
<!-- mdformat-toc start -->

No headers.
No TOC in this file.
.
<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->


<!-- mdformat-toc end -->

No headers.
No TOC in this file.
.

Missing heading levels
.
<!-- mdformat-toc start --no-anchors -->

Level 1
=======

### Level  zwei

## Level 2 ., Azwei

## Level 2 .+ Az//&w_äöe-i

# Level 1
.
<!-- mdformat-toc start --slug=github --no-anchors --maxlevel=6 --minlevel=1 -->

- [Level 1](<#level-1>)
  - [Level  zwei](<#level--zwei>)
  - [Level 2 ., Azwei](<#level-2--azwei>)
  - [Level 2 .+ Az//&w_äöe-i](<#level-2--azw_%C3%A4%C3%B6e-i>)
- [Level 1](<#level-1-1>)

<!-- mdformat-toc end -->

# Level 1

### Level  zwei

## Level 2 ., Azwei

## Level 2 .+ Az//&w\_äöe-i

# Level 1
.

Gitlab slug
.
<!-- mdformat-toc start --slug=gitlab --no-anchors -->

# Gitlab slug reduces-------hyphens
.
<!-- mdformat-toc start --slug=gitlab --no-anchors --maxlevel=6 --minlevel=1 -->

- [Gitlab slug reduces-------hyphens](<#gitlab-slug-reduces-hyphens>)

<!-- mdformat-toc end -->

# Gitlab slug reduces\-\-\-\-\-\--hyphens
.

Add anchors
.
<!-- mdformat-toc start -->

## This title has an anchor
# This title too
.
<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [This title has an anchor](<#this-title-has-an-anchor>)
- [This title too](<#this-title-too>)

<!-- mdformat-toc end -->

## This title has an anchor<a name="this-title-has-an-anchor"></a>

# This title too<a name="this-title-too"></a>
.

Anchors already in place
.
<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [This title has an anchor](<#this-title-has-an-anchor>)
- [This title too](<#this-title-too>)

<!-- mdformat-toc end -->

## This title has an anchor<a name="this-title-has-an-anchor"></a>

# This title too<a name="this-title-too"></a>
.
<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [This title has an anchor](<#this-title-has-an-anchor>)
- [This title too](<#this-title-too>)

<!-- mdformat-toc end -->

## This title has an anchor<a name="this-title-has-an-anchor"></a>

# This title too<a name="this-title-too"></a>
.

Anchors only on ToC levels
.
<!-- mdformat-toc start --maxlevel=3 --minlevel=2 -->

# Title
## Anchor pls
### Title
#### No more anchors
.
<!-- mdformat-toc start --slug=github --maxlevel=3 --minlevel=2 -->

- [Anchor pls](<#anchor-pls>)
  - [Title](<#title-1>)

<!-- mdformat-toc end -->

# Title

## Anchor pls<a name="anchor-pls"></a>

### Title<a name="title-1"></a>

#### No more anchors
.

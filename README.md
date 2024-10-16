[![Build Status](https://github.com/hukkin/mdformat-toc/actions/workflows/tests.yaml/badge.svg?branch=master)](https://github.com/hukkin/mdformat-toc/actions?query=workflow%3ATests+branch%3Amaster+event%3Apush)
[![PyPI version](https://img.shields.io/pypi/v/mdformat-toc)](https://pypi.org/project/mdformat-toc)

# mdformat-toc

> Mdformat plugin to generate a table of contents

**Table of Contents**  *generated with [mdformat-toc](https://github.com/hukkin/mdformat-toc)*

<!-- mdformat-toc start --slug=github --no-anchors --maxlevel=6 --minlevel=2 -->

- [Description](#description)
- [Install](#install)
- [Usage](#usage)
  - [Configuration](#configuration)
    - [Minimum and maximum heading levels](#minimum-and-maximum-heading-levels)
    - [Disabling anchor generation](#disabling-anchor-generation)
    - [Changing the slug function](#changing-the-slug-function)

<!-- mdformat-toc end -->

## Description

Mdformat-toc is an [mdformat](https://github.com/executablebooks/mdformat) plugin
that adds mdformat the capability to auto-generate a table of contents (ToC).
The ToC is generated in a user-specified location in the Markdown file.

Mdformat-toc, by default, creates an HTML anchor for each heading listed in the ToC.
ToC links should therefore be compatible with any well-behaved Markdown renderer (including GitLab's renderer).

HTML anchor generation can be disabled, in which case a user should configure a slug function that is compatible with the Markdown renderer used (GitHub and GitLab slug functions are currently supported).

## Install

```bash
pip install mdformat-toc
```

## Usage

Add the following line to your Markdown file.
A ToC will be generated in the location indicated by it.

```markdown
<!-- mdformat-toc start -->
```

After adding the indicator line, simply run

```bash
mdformat <filename>
```

and mdformat will generate a ToC.

### Configuration

Arguments can be added to the indicator line to alter how the ToC is generated.
An indicator line with the default options would look like:

```markdown
<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->
```

Placing more than one indicator lines in a document is currently not supported.

#### Minimum and maximum heading levels

A user can configure a range of heading levels to be included in the ToC (and to be "anchored").
For instance, the following configuration will only list 2nd, 3rd and 4th level headings in the ToC:

```markdown
<!-- mdformat-toc start --minlevel=2 --maxlevel=4 -->
```

#### Disabling anchor generation

By default, an HTML anchor is appended to each heading.
For instance, the following heading

```markdown
# Some title
```

might be formatted as

```markdown
# Some title<a name="some-title"></a>
```

This ensures that ToC links do not rely on a Markdown renderer to create HTML anchors,
and makes the links universally compatible.

ToC links are by default compatible with the anchors generated by GitHub's Markdown renderer.
If your Markdown is only hosted on GitHub, you can disable mdformat-toc's HTML anchor generation:

```markdown
<!-- mdformat-toc start --no-anchors -->
```

#### Changing the slug function

Mdformat-toc defaults to using GitHub's slug function.

If your Markdown is not hosted on GitHub you may want to use GitLab's slug function instead:

```markdown
<!-- mdformat-toc start --slug=gitlab --no-anchors -->
```

**NOTE:** Unlike GitLab, GitHub requires using its own slug function in order for ToC links to work expectedly.
Creating HTML anchors and using a non-GitHub slug function is not GitHub compatible
because GitHub's Markdown renderer modifies the HTML anchors mdformat-toc creates.
The default configuration
(GitHub slug function and anchor generation)
is the only configuration cross-compatible with GitHub and GitLab.

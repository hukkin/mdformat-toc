[![Build Status](https://github.com/hukkinj1/mdformat-toc/workflows/Tests/badge.svg?branch=master)](<https://github.com/hukkinj1/mdformat-toc/actions?query=workflow%3ATests+branch%3Amaster+event%3Apush>)
[![PyPI version](<https://img.shields.io/pypi/v/mdformat-toc>)](<https://pypi.org/project/mdformat-toc>)

# mdformat-toc

> Mdformat plugin to generate a table of contents

## Description
Mdformat-toc is an [mdformat](https://github.com/executablebooks/mdformat) plugin
that adds mdformat the capability to auto-generate a table of contents (ToC).
The ToC is generated in a user-specified location in the Markdown file.
The generated ToC links are, by default, GitHub compatible. GitLab compatibility is configurable.

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

#### Minimum and maximum heading levels
TODO: document

#### GitLab compatible links

By default, the ToC links are GitHub compatible.
If you are using GitLab instead, you will want to add a `--slug=gitlab` argument in the ToC indicator line:
```markdown
<!-- mdformat-toc start --slug=gitlab -->
```

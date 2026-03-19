# smidir

ODT/PDF generator using Markdown, Libreoffice, Pandoc & MermaidJS.

`smidir` is a command-line tool designed to streamline the generation of documents from Markdown sources using Pandoc and LibreOffice for high-quality ODT and PDF output. It is designed to be generic and can be used for any document structure that follows its simple conventions.

## Features

- **Markdown-driven**: Write your content in simple Markdown.
- **Templating**: Advanced preprocessing using **Jinja2**.
- **Flexible Variables**: Supports global variables via `vars.yml` and per-document variables via YAML frontmatter.
- **Legacy Support**: Maintains compatibility with `${VAR}` style placeholders.
- **ODT & PDF Output**: Generates LibreOffice Writer (ODT) documents using reference documents for consistent styling, and can convert them to PDF.
- **Extensible**: Supports Pandoc Lua filters and custom filters.
- **Smart Resource Management**: Comes with built-in default templates and filters, but allows full customization.

## Requirements

To use `smidir`, you need the following tools installed on your system:

- **Python 3.13+**
- **Pandoc**: Used for converting Markdown to ODT.
- **LibreOffice**: Used for ODT to PDF conversion (headless mode).
- **Python Packages**: `jinja2`, `PyYAML` (installed automatically via `uv` or `pip`).

## Installation

### Local Installation

It is recommended to use `uv` for managing the environment and running the tool:

```bash
uv sync
```

Or install it in your environment:

```bash
pip install .
```

A pre-built image is available at `ghcr.io/kagesenshi/smidir:latest`. This image includes all necessary system dependencies (Pandoc, LibreOffice, Mermaid CLI).

#### Using Docker

```bash
docker run --rm \
  -u $(id -u):$(id -g) \
  -v $(pwd):/data \
  -w /data \
  ghcr.io/kagesenshi/smidir:latest [arguments]
```

#### Using Podman (Rootless)

```bash
podman run --rm \
  --userns keep-id \
  --user ${UID} \
  -v $(pwd):/data \
  -w /data \
  ghcr.io/kagesenshi/smidir:latest [arguments]
```

## Project Structure

`smidir` is designed to be flexible. It looks for resources in the following order:

1.  **Local Directory**: Files provided via CLI or located in the current working directory.
2.  **Internal Resources**: Default resources bundled with the tool (templates and filters).

### Internal Resources
- `resources/templates/blank.odt`: The default reference document for styling.
- `resources/filters/pagebreak.lua`: A default filter enabled by default.

## Usage

### Listing Available Resources

To see which templates are available in the internal resources:

```bash
# List available documents in the current directory
smidir --list

# List internal templates
smidir --list-templates
```

### Generating a Document

To generate a document, provide the path to the directory containing a `content.md` file:

```bash
# Generate a document from the 'my-docs' directory
smidir my-docs

# Generate a PDF document
smidir my-docs --format pdf

# Specify a custom template (searches locally first, then internal resources)
smidir my-docs -t my-template.odt

# Specify a custom output name
smidir my-docs -o final_report.odt

# Apply additional filters
smidir my-docs --filter custom-filter.lua
```

### Document Folder Structure

A typical document folder should look like this:

```
my-docs/
├── content.md      # Main content file (required)
├── image1.png      # Assets referenced in content.md
└── vars.yml        # (Optional) Local variables
```

### Template Preprocessing

`smidir` uses Jinja2 to preprocess the `content.md` file.

Example `content.md`:

```markdown
---
title: Project Report
version: 1.2
default_template: blank.odt
---

# {{ title }}

This report was generated on {{ date }}.

{% if detailed %}
## Technical Details
...
{% endif %}
```

## Configuration

- **Frontmatter**: Variables defined in the `content.md` frontmatter are available during preprocessing.
- **Global Variables**: Defined in `vars.yml` (default location in CWD or specified via `-f`).
- **Precedence**: Global variables (`-f`) override frontmatter variables.

## License

MIT License - Copyright 2026 Mohd Izhar Firdaus Bin Ismail

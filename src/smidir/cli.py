#!/usr/bin/env python

# Copyright 2026. Mohd Izhar Firdaus Bin Ismail
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import subprocess
import sys
import yaml
import re
import tempfile
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def get_base_dir() -> Path:
    return Path(__file__).parent.resolve()


def get_resource_dir(resource_type: str) -> Path:
    """Returns the path to a resource directory within the package."""
    return get_base_dir() / "resources" / resource_type


def list_documents(search_dir: Path):
    if not search_dir.exists():
        print(f"Directory not found: {search_dir}")
        return
    print(f"Available documents in {search_dir}:")
    for item in sorted(search_dir.iterdir()):
        if item.is_dir():
            # Check if it has content.md
            if (item / "content.md").exists():
                print(f"  - {item.name}")
            else:
                # If we are in generic mode, maybe any .md file?
                # User says "find content.md and generation starts from there"
                pass


def list_agreements():
    # Backward compatibility or just remove? User says "we no longer have default agreements folder"
    # I'll repurpose this to list in current directory
    list_documents(Path.cwd())


def list_templates():
    templates_dir = get_resource_dir("templates")
    if not templates_dir.exists():
        print(f"Directory not found: {templates_dir}")
        return
    print("Available templates:")
    for item in sorted(templates_dir.iterdir()):
        if item.is_file() and not item.name.startswith("."):
            print(f"  - {item.name}")


def parse_frontmatter(content_file: Path):
    """
    Parses YAML frontmatter from a markdown file.
    Returns a tuple of (metadata_dict, body_content).
    """
    metadata = {}
    content = ""
    try:
        with open(content_file, "r", encoding="utf-8") as f:
            content = f.read()

        if content.startswith("---"):
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if match:
                frontmatter = match.group(1)
                body = match.group(2)
                metadata = yaml.safe_load(frontmatter) or {}
                return metadata, body
    except Exception as e:
        print(f"Warning: Failed to parse frontmatter: {e}")

    return metadata, content


def main():
    parser = argparse.ArgumentParser(
        description="Generate ODT/PDF document using pandoc"
    )

    # Listing options
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List possible documents in current directory",
    )
    parser.add_argument(
        "-T",
        "--list-templates",
        action="store_true",
        help="List possible templates in resources",
    )

    # Generation options
    parser.add_argument(
        "document_dir", nargs="?", help="Directory containing content.md"
    )
    parser.add_argument(
        "-t",
        "--template",
        default="blank.odt",
        help="Template name (if doesn't exist in current dir, lookup in resources/templates dir)",
    )
    parser.add_argument(
        "-f",
        "--vars-file",
        default="vars.yml",
        help="Location of vars.yml metadata file (default: vars.yml)",
    )
    parser.add_argument(
        "--format",
        nargs="?",
        const="pdf",
        help="Output format (e.g. pdf, odt) to use when output filename is not provided (defaults to pdf if flag is provided without value)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file name (default: {dirname}-v{version}.odt, or .{format})",
    )
    parser.add_argument(
        "--filter",
        action="append",
        help="Additional Pandoc filters to apply",
    )

    args = parser.parse_args()

    if args.list:
        list_agreements()
        sys.exit(0)

    if args.list_templates:
        list_templates()
        sys.exit(0)

    if not args.document_dir:
        parser.error(
            "The document_dir argument is required unless using listing flags (-l or -T)"
        )

    base_dir = get_base_dir()

    # Resolve document content.md
    doc_dir = Path(args.document_dir).resolve()
    content_file = doc_dir / "content.md"
    if not content_file.exists():
        print(
            f"Error: Content file not found at {content_file}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load variables from vars.yml
    vars_file = Path(args.vars_file)
    if not vars_file.exists():
        print(f"Error: Variables file not found at {vars_file}", file=sys.stderr)
        sys.exit(1)

    with open(vars_file, "r", encoding="utf-8") as f:
        global_vars = yaml.safe_load(f) or {}

    # Parse frontmatter and body
    metadata, body = parse_frontmatter(content_file)

    if args.format and args.output:
        parser.error("Argument --format cannot be used together with --output")

    # Resolve output filename
    if not args.output:
        version = metadata.get("version", "1")
        fmt = args.format.lstrip(".") if args.format else "odt"
        args.output = f"{doc_dir.name}-v{version}.{fmt}"

    # Merge variables (CLI/metadata file overrides frontmatter)
    # Also uppercase keys for compatibility with ${VAR} style in lua if needed,
    # but we will use Jinja2.
    all_vars = {**metadata, **global_vars}

    # Uppercase versions for ${VAR} legacy support
    legacy_vars = {k.upper(): v for k, v in all_vars.items() if isinstance(k, str)}
    all_vars.update(legacy_vars)

    # Resolve template
    if not args.template:
        args.template = metadata.get("default_template", "blank.odt")

    template_file = Path(args.template)
    if not template_file.exists():
        # Lookup in resources/templates dir
        template_file = get_resource_dir("templates") / args.template
        if not template_file.exists():
            print(f"Error: Template file not found: {args.template}", file=sys.stderr)
            sys.exit(1)

    # Preprocess body using Jinja2
    env = Environment(loader=FileSystemLoader(str(doc_dir)))

    # We want to support both Jinja2 tags and ${VAR} style replacements.
    # We can use Jinja2 for the tags, then a simple regex/replace for ${VAR}.
    try:
        jinja_template = env.from_string(body)
        rendered_body = jinja_template.render(**all_vars)

        # Legacy support for ${VAR}
        def legacy_replace(match):
            name = match.group(1).upper()
            return str(all_vars.get(name, match.group(0)))

        rendered_body = re.sub(r"\$\{(.*?)\}", legacy_replace, rendered_body)

    except Exception as e:
        print(f"Error during template preprocessing: {e}", file=sys.stderr)
        sys.exit(1)

    # Write rendered content to a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
        # Re-add metadata as YAML frontmatter for pandoc if needed (e.g. for title)
        tmp.write("---\n")
        yaml.dump(metadata, tmp)
        tmp.write("---\n\n")
        tmp.write(rendered_body)
        tmp_path = tmp.name

    try:
        # Check if output is PDF
        is_pdf = args.output.lower().endswith(".pdf")
        pandoc_output = args.output
        if is_pdf:
            # Generate intermediate ODT first
            pandoc_output = str(Path(args.output).with_suffix(".odt").resolve())

        # Construct pandoc command
        cmd = [
            "pandoc",
            "--reference-doc",
            str(template_file),
            tmp_path,
            "-o",
            "--metadata-file",
            str(vars_file),
            "--resource-path",
            f".:{doc_dir}",
        ]

        # Add default filters from resources/filters
        filters_dir = get_resource_dir("filters")
        if filters_dir.exists() and filters_dir.is_dir():
            for lua_filter in sorted(filters_dir.glob("*.lua")):
                cmd.extend(["--lua-filter", str(lua_filter)])
            for regular_filter in sorted(filters_dir.glob("*.filter")):
                cmd.extend(["--filter", str(regular_filter)])

        # Add user-specified filters
        if args.filter:
            for f in args.filter:
                f_path = Path(f).resolve()
                if f_path.suffix == ".lua":
                    cmd.extend(["--lua-filter", str(f_path)])
                else:
                    cmd.extend(["--filter", str(f_path)])

        print(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        if is_pdf:
            print(f"Converting {pandoc_output} to PDF using LibreOffice...")
            lo_cmd = [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(Path(args.output).parent.resolve()),
                pandoc_output,
            ]
            subprocess.run(lo_cmd, check=True)
            # Remove intermediate ODT
            if Path(pandoc_output).exists():
                Path(pandoc_output).unlink()

        print(f"Success! Document generated: {args.output}")

    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(
            "Error: pandoc command not found. Please ensure pandoc is installed and in your PATH.",
            file=sys.stderr,
        )
        sys.exit(1)
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


if __name__ == "__main__":
    main()

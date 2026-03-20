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
import shutil
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def get_base_dir() -> Path:
    return Path(__file__).parent.resolve()


def check_dependencies():
    """Checks for the existence of required system commands."""
    dependencies = ["pandoc", "libreoffice", "npx", "pdf2svg"]
    missing = []
    for dep in dependencies:
        if shutil.which(dep) is None:
            missing.append(dep)

    if missing:
        print(
            f"Error: Missing required system dependencies: {', '.join(missing)}",
            file=sys.stderr,
        )
        print("Please ensure they are installed and in your PATH.", file=sys.stderr)
        sys.exit(1)


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


def render_markdown(body: str, context: dict, doc_dir: Path) -> str:
    """Renders markdown body using Jinja2 and legacy ${VAR} replacement."""
    env = Environment(loader=FileSystemLoader(str(doc_dir)))
    try:
        jinja_template = env.from_string(body)
        rendered_body = jinja_template.render(**context)

        # Legacy support for ${VAR}
        def legacy_replace(match):
            name = match.group(1).upper()
            return str(context.get(name, match.group(0)))

        rendered_body = re.sub(r"\$\{(.*?)\}", legacy_replace, rendered_body)
        return rendered_body
    except Exception as e:
        print(f"Error during template preprocessing: {e}", file=sys.stderr)
        raise


def resolve_content(doc_dir: Path, inherited_vars: dict = None) -> tuple[dict, str]:
    """
    Recursively resolves directory content.
    Returns (metadata, rendered_body).
    """
    if inherited_vars is None:
        inherited_vars = {}

    local_vars = {}
    # Load vars.yml in doc_dir
    vars_yml = doc_dir / "vars.yml"
    if vars_yml.exists():
        with open(vars_yml, "r", encoding="utf-8") as f:
            local_vars.update(yaml.safe_load(f) or {})

    # Check for content.md or content.yml/yaml
    content_md = doc_dir / "content.md"
    content_yml = doc_dir / "content.yml"
    if not content_yml.exists():
        content_yml = doc_dir / "content.yaml"

    current_context = {**inherited_vars, **local_vars}

    if content_yml.exists():
        with open(content_yml, "r", encoding="utf-8") as f:
            yml_data = yaml.safe_load(f) or {}

        # vars in content.yml are directory defaults
        content_vars = yml_data.get("vars", {})
        # Note: vars in content_yml should be lower priority than vars.yml according to plan
        # We can adjust: inherited_vars <- content_vars <- vars_yml
        current_context = {**inherited_vars, **content_vars, **local_vars}

        if "contents" not in yml_data:
            raise KeyError(f"Missing 'contents' key in {content_yml}")
        contents = yml_data["contents"]
        if not isinstance(contents, list):
            raise ValueError(f"'contents' must be a list in {content_yml}")

        bodies = []
        for item in contents:
            if item == ".":
                # Expand current directory
                items = sorted(doc_dir.iterdir())
                for sub_item in items:
                    if sub_item.name in [
                        "content.yml",
                        "content.yaml",
                        "vars.yml",
                        "content.md",
                        "README.md",
                    ]:
                        continue
                    if sub_item.is_file() and sub_item.suffix == ".md":
                        meta, body = parse_frontmatter(sub_item)
                        file_context = {**current_context, **meta}
                        legacy_vars = {
                            k.upper(): v
                            for k, v in file_context.items()
                            if isinstance(k, str)
                        }
                        file_context.update(legacy_vars)
                        bodies.append(render_markdown(body, file_context, doc_dir))
                    elif sub_item.is_dir():
                        # Only include if it has content.yml/yaml or content.md
                        if (
                            (sub_item / "content.yml").exists()
                            or (sub_item / "content.yaml").exists()
                            or (sub_item / "content.md").exists()
                        ):
                            _, body = resolve_content(sub_item, current_context)
                            bodies.append(body)
                continue

            item_path = doc_dir / item
            if not item_path.exists():
                raise FileNotFoundError(f"Content item not found: {item_path}")

            if item_path.is_file():
                if item_path.suffix != ".md":
                    raise ValueError(f"File {item_path} is not a markdown file")
                meta, body = parse_frontmatter(item_path)
                # For individual files, we use their own frontmatter but current_context as base
                file_context = {**current_context, **meta}
                legacy_vars = {
                    k.upper(): v for k, v in file_context.items() if isinstance(k, str)
                }
                file_context.update(legacy_vars)
                bodies.append(render_markdown(body, file_context, doc_dir))
            elif item_path.is_dir():
                _, body = resolve_content(item_path, current_context)
                bodies.append(body)

        # Metadata from content.yml (everything except 'contents' and 'vars'?)
        # User said "no other keys are supported", but we might have metadata like version/title.
        # Actually, let's treat yml_data as metadata too, excluding contents/vars.
        metadata = {k: v for k, v in yml_data.items() if k not in ["contents", "vars"]}
        return metadata, "\n\n".join(bodies)

    if content_md.exists():
        metadata, body = parse_frontmatter(content_md)
        # Update context with frontmatter for this file
        current_context.update(metadata)
        # Uppercase versions for ${VAR} legacy support
        legacy_vars = {
            k.upper(): v for k, v in current_context.items() if isinstance(k, str)
        }
        current_context.update(legacy_vars)
        rendered_body = render_markdown(body, current_context, doc_dir)
        return metadata, rendered_body

    return {}, ""


def main():
    check_dependencies()
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
        help="Location of vars.yml metadata file (default: {document_dir}/vars.yml)",
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

    # Resolve document content
    doc_dir = Path(args.document_dir).resolve()

    # Load global variables from --vars-file (highest priority)
    global_vars = {}
    if args.vars_file:
        vars_file = Path(args.vars_file)
        if not vars_file.exists():
            print(f"Error: Variables file not found at {vars_file}", file=sys.stderr)
            sys.exit(1)
        with open(vars_file, "r", encoding="utf-8") as f:
            global_vars = yaml.safe_load(f) or {}
    else:
        # If not provided, we will check vars.yml in the document directory
        # but resolve_content will handle directory-level vars.yml too.
        # The top-level vars.yml is still a special case for command line compatibility if it was used before.
        # Actually, let's keep it consistent: CLI overrides directory level.
        vars_file = doc_dir / "vars.yml"
        # We don't exit here anymore if it doesn't exist, as it's optional.

    # Resolve content recursively
    metadata, rendered_body = resolve_content(doc_dir, global_vars)

    if not rendered_body and not metadata:
        print(f"Error: No content found in {doc_dir}", file=sys.stderr)
        sys.exit(1)

    if args.format and args.output:
        parser.error("Argument --format cannot be used together with --output")

    # Merge variables for output filename and template lookup
    # CLI global vars should have highest priority
    all_vars = {**metadata, **global_vars}

    # Resolve output filename
    if not args.output:
        version = all_vars.get("version", "1")
        fmt = args.format.lstrip(".") if args.format else "odt"
        args.output = f"{doc_dir.name}-v{version}.{fmt}"

    # Resolve template
    if not args.template:
        args.template = all_vars.get("default_template", "blank.odt")

    template_file = Path(args.template)
    if not template_file.exists():
        # Lookup in resources/templates dir
        template_file = get_resource_dir("templates") / args.template
        if not template_file.exists():
            print(f"Error: Template file not found: {args.template}", file=sys.stderr)
            sys.exit(1)

    # Write rendered content to a temporary file
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
            # Re-add metadata as YAML frontmatter for pandoc if needed (e.g. for title)
            tmp.write("---\n")
            # Filter metadata to keep it clean
            pandoc_metadata = {
                k: v for k, v in all_vars.items() if not k.isupper()
            }
            yaml.dump(pandoc_metadata, tmp)
            tmp.write("---\n\n")
            tmp.write(rendered_body)
            tmp_path = tmp.name

        # Check if output is PDF or HTML
        is_pdf = args.output.lower().endswith(".pdf")
        is_html = args.output.lower().endswith(".html")
        pandoc_output = args.output
        if is_pdf:
            # Generate intermediate ODT first
            pandoc_output = str(Path(args.output).with_suffix(".odt").resolve())

        # Construct pandoc command
        cmd = [
            "pandoc",
            tmp_path,
            "-o",
            pandoc_output,
            "--resource-path",
            f".:{doc_dir}",
        ]

        if not is_html:
            cmd.extend(["--reference-doc", str(template_file)])
        elif template_file.suffix == ".html":
            cmd.extend(["--template", str(template_file)])

        if vars_file and vars_file.exists():
            cmd.extend(["--metadata-file", str(vars_file)])


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
        if tmp_path and Path(tmp_path).exists():
            Path(tmp_path).unlink()


if __name__ == "__main__":
    main()

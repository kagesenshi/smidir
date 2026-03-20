import pytest
import os
import shutil
from pathlib import Path
from smidir.cli import resolve_content, render_markdown, parse_frontmatter
import subprocess

@pytest.fixture
def test_data_dir(tmp_path):
    """Creates a temporary directory with test data."""
    doc_dir = tmp_path / "test_doc"
    doc_dir.mkdir()
    return doc_dir

def test_resolve_content_simple(test_data_dir):
    content_md = test_data_dir / "content.md"
    content_md.write_text("---\ntitle: Simple\n---\n# {{ title }}", encoding="utf-8")
    
    metadata, body = resolve_content(test_data_dir)
    assert metadata["title"] == "Simple"
    assert "<h1>Simple</h1>" in body or "# Simple" in body
    # resolve_content returns rendered body
    assert "# Simple" in body

def test_resolve_content_yaml_inheritance(test_data_dir):
    # Root content.yml
    (test_data_dir / "content.yml").write_text("vars:\n  title: Main\ncontents:\n  - sub/", encoding="utf-8")
    
    # Sub directory
    sub_dir = test_data_dir / "sub"
    sub_dir.mkdir()
    (sub_dir / "page.md").write_text("# {{ title }} in {{ loc }}", encoding="utf-8")
    (sub_dir / "vars.yml").write_text("loc: sub", encoding="utf-8")
    
    metadata, body = resolve_content(test_data_dir)
    assert "# Main in sub" in body

def test_resolve_content_yaml_override(test_data_dir):
    (test_data_dir / "content.yml").write_text("vars:\n  val: parent\ncontents:\n  - sub/", encoding="utf-8")
    
    sub_dir = test_data_dir / "sub"
    sub_dir.mkdir()
    (sub_dir / "content.yml").write_text("vars:\n  val: child\ncontents:\n  - page.md", encoding="utf-8")
    (sub_dir / "page.md").write_text("Value: {{ val }}", encoding="utf-8")
    
    metadata, body = resolve_content(test_data_dir)
    assert "Value: child" in body

def test_cli_html_output(test_data_dir):
    (test_data_dir / "content.md").write_text("# Hello HTML", encoding="utf-8")
    output_html = test_data_dir / "output.html"
    
    # Run CLI
    cli_path = Path(__file__).parent.parent / "src" / "smidir" / "cli.py"
    cmd = ["python3", str(cli_path), str(test_data_dir), "-o", str(output_html)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0
    assert output_html.exists()
    content = output_html.read_text(encoding="utf-8")
    assert "Hello HTML" in content
    assert "<h1" in content

def test_directory_merging_auto(test_data_dir):
    # No content.yml/md, should merge all .md files
    (test_data_dir / "b.md").write_text("Body B", encoding="utf-8")
    (test_data_dir / "a.md").write_text("Body A", encoding="utf-8")
    
    _, body = resolve_content(test_data_dir)
    # Should be sorted: a.md then b.md
    assert "Body A\n\nBody B" in body

def test_resolve_content_yml_missing_contents(test_data_dir):
    (test_data_dir / "content.yml").write_text("vars:\n  a: b", encoding="utf-8")
    with pytest.raises(KeyError, match="Missing 'contents' key"):
        resolve_content(test_data_dir)

def test_resolve_content_yml_contents_not_list(test_data_dir):
    (test_data_dir / "content.yml").write_text("contents: not-a-list", encoding="utf-8")
    with pytest.raises(ValueError, match="'contents' must be a list"):
        resolve_content(test_data_dir)

def test_resolve_content_yml_item_not_found(test_data_dir):
    (test_data_dir / "content.yml").write_text("contents:\n  - missing.md", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="not found"):
        resolve_content(test_data_dir)

def test_resolve_content_yml_non_markdown_file(test_data_dir):
    (test_data_dir / "content.yml").write_text("contents:\n  - data.txt", encoding="utf-8")
    (test_data_dir / "data.txt").write_text("some data", encoding="utf-8")
    with pytest.raises(ValueError, match="is not a markdown file"):
        resolve_content(test_data_dir)

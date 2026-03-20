import pytest
from pathlib import Path
import yaml
from smidir.cli import resolve_content

@pytest.fixture
def test_data_dir(tmp_path):
    """Creates a temporary directory with test data."""
    doc_dir = tmp_path / "test_doc"
    doc_dir.mkdir()
    return doc_dir

def test_resolve_content_dot_expansion(test_data_dir):
    # content.yml with '.' 
    (test_data_dir / "content.yml").write_text("contents:\n  - '.'", encoding="utf-8")
    
    # Some markdown files
    (test_data_dir / "02-beta.md").write_text("Beta content", encoding="utf-8")
    (test_data_dir / "01-alpha.md").write_text("Alpha content", encoding="utf-8")
    
    # README should be ignored
    (test_data_dir / "README.md").write_text("README content", encoding="utf-8")
    
    metadata, body = resolve_content(test_data_dir)
    
    # Should be sorted: alpha then beta
    assert "Alpha content" in body
    assert "Beta content" in body
    assert body.find("Alpha content") < body.find("Beta content")
    assert "README content" not in body

def test_resolve_content_dot_with_subdirs(test_data_dir):
    (test_data_dir / "content.yml").write_text("contents:\n  - '.'", encoding="utf-8")
    
    # Subdir with content.yml
    sub1 = test_data_dir / "sub1"
    sub1.mkdir()
    (sub1 / "content.yml").write_text("contents:\n  - page.md", encoding="utf-8")
    (sub1 / "page.md").write_text("Sub1 content", encoding="utf-8")
    
    # Subdir with content.md
    sub2 = test_data_dir / "sub2"
    sub2.mkdir()
    (sub2 / "content.md").write_text("Sub2 content", encoding="utf-8")
    
    # Subdir without any content.* (should be ignored)
    sub3 = test_data_dir / "sub3"
    sub3.mkdir()
    (sub3 / "random.md").write_text("Sub3 content", encoding="utf-8")
    
    metadata, body = resolve_content(test_data_dir)
    
    assert "Sub1 content" in body
    assert "Sub2 content" in body
    assert "Sub3 content" not in body

def test_resolve_content_dot_filters_config(test_data_dir):
    (test_data_dir / "content.yml").write_text("contents:\n  - '.'", encoding="utf-8")
    (test_data_dir / "vars.yml").write_text("key: value", encoding="utf-8")
    (test_data_dir / "content.md").write_text("Frontmatter content", encoding="utf-8")
    
    metadata, body = resolve_content(test_data_dir)
    
    # Should not include content of config files
    assert "key: value" not in body
    assert "Frontmatter content" not in body

def test_resolve_content_requires_yml(test_data_dir):
    # No content.yml, only markdown files
    (test_data_dir / "01-alpha.md").write_text("Alpha content", encoding="utf-8")
    
    # According to new requirement, this should NOT automatically merge them.
    # It should probably return empty or raise an error if we enforce content.yml.
    # However, resolve_content currently supports content.md too.
    # Let's see what happens if neither exists.
    
    metadata, body = resolve_content(test_data_dir)
    assert body == ""

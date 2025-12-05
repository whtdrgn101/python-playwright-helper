"""Unit tests for TemplateService."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from rest_api_testing.template import TemplateService, TemplateException
from rest_api_testing.template.template_service import ResourceLoader
from jinja2 import TemplateNotFound


@pytest.fixture
def template_service():
    """Create a fresh TemplateService instance for testing."""
    # Clear the singleton instance
    TemplateService._instance = None
    service = TemplateService.get_instance()
    yield service
    # Clean up after test
    service.clear_cache()


@pytest.fixture
def temp_template_dir():
    """Create a temporary directory with test templates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create a simple template
        simple_template = tmpdir_path / "simple.j2"
        simple_template.write_text("Hello {{ name }}!")
        
        # Create a JSON template
        json_template = tmpdir_path / "user.json.j2"
        json_template.write_text(json.dumps({
            "firstName": "{{ firstName }}",
            "lastName": "{{ lastName }}",
            "email": "{{ email }}",
            "age": "{{ age }}"
        }))
        
        # Create a template with conditionals
        conditional_template = tmpdir_path / "conditional.j2"
        conditional_template.write_text("""{% if include_details %}
Name: {{ name }}
Email: {{ email }}
{% else %}
Name: {{ name }}
{% endif %}""")
        
        # Create a template with loops
        loop_template = tmpdir_path / "loop.j2"
        loop_template.write_text("""Items:
{% for item in items %}
  - {{ item }}
{% endfor %}""")
        
        # Create a CSV file
        csv_file = tmpdir_path / "test-data.csv"
        csv_file.write_text("""firstName,lastName,email,age
John,Doe,john@example.com,30
Jane,Smith,jane@example.com,25
Bob,Johnson,bob@example.com,35""")
        
        yield tmpdir_path


@pytest.fixture
def template_service_with_temp_dir(temp_template_dir):
    """Create a TemplateService with a temporary template directory."""
    TemplateService._instance = None
    
    # Patch the search paths to use temp directory
    with patch.object(TemplateService, '__init__', lambda self: self._init_with_custom_path(str(temp_template_dir))):
        service = TemplateService.__new__(TemplateService)
        from jinja2 import Environment
        from rest_api_testing.template.template_service import ResourceLoader
        
        service._env = Environment(
            loader=ResourceLoader([str(temp_template_dir)]),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        service._template_cache = {}
        
        yield service
        service.clear_cache()


class TestTemplateServiceBasics:
    """Test basic TemplateService functionality."""

    def test_singleton_pattern(self):
        """Test that TemplateService uses singleton pattern."""
        TemplateService._instance = None
        service1 = TemplateService.get_instance()
        service2 = TemplateService.get_instance()
        assert service1 is service2

    def test_initialization(self, template_service):
        """Test TemplateService initialization."""
        assert template_service is not None
        assert template_service._env is not None
        assert isinstance(template_service._template_cache, dict)

    def test_cache_size(self, template_service):
        """Test cache size tracking."""
        assert template_service.get_cache_size() == 0


class TestTemplateRendering:
    """Test template rendering functionality."""

    def test_render_simple_template(self, template_service_with_temp_dir):
        """Test rendering a simple template."""
        result = template_service_with_temp_dir.render("simple.j2", {"name": "World"})
        assert result == "Hello World!"

    def test_render_json_template(self, template_service_with_temp_dir):
        """Test rendering a JSON template."""
        context = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "age": "30"
        }
        result = template_service_with_temp_dir.render("user.json.j2", context)
        data = json.loads(result)
        assert data["firstName"] == "John"
        assert data["lastName"] == "Doe"
        assert data["email"] == "john@example.com"
        assert data["age"] == "30"

    def test_render_with_conditionals(self, template_service_with_temp_dir):
        """Test rendering templates with conditional logic."""
        # With details
        result = template_service_with_temp_dir.render(
            "conditional.j2",
            {"name": "Alice", "email": "alice@example.com", "include_details": True}
        )
        assert "Email: alice@example.com" in result
        assert "Name: Alice" in result

        # Without details
        result = template_service_with_temp_dir.render(
            "conditional.j2",
            {"name": "Bob", "include_details": False}
        )
        assert "Email:" not in result
        assert "Name: Bob" in result

    def test_render_with_loops(self, template_service_with_temp_dir):
        """Test rendering templates with loops."""
        result = template_service_with_temp_dir.render(
            "loop.j2",
            {"items": ["apple", "banana", "cherry"]}
        )
        assert "apple" in result
        assert "banana" in result
        assert "cherry" in result

    def test_render_with_empty_context(self, template_service_with_temp_dir):
        """Test rendering with no context."""
        result = template_service_with_temp_dir.render("simple.j2", {})
        assert result == "Hello !"

    def test_render_with_none_context(self, template_service_with_temp_dir):
        """Test rendering with None context."""
        result = template_service_with_temp_dir.render("simple.j2", None)
        assert result == "Hello !"

    def test_render_template_not_found(self, template_service_with_temp_dir):
        """Test rendering a non-existent template."""
        with pytest.raises(TemplateException) as exc_info:
            template_service_with_temp_dir.render("nonexistent.j2", {})
        assert "not found" in str(exc_info.value).lower() or "Failed to render" in str(exc_info.value)

    def test_render_empty_path(self, template_service_with_temp_dir):
        """Test rendering with empty template path."""
        with pytest.raises(TemplateException) as exc_info:
            template_service_with_temp_dir.render("", {})
        assert "cannot be null or empty" in str(exc_info.value)

    def test_render_none_path(self, template_service_with_temp_dir):
        """Test rendering with None template path."""
        with pytest.raises(TemplateException) as exc_info:
            template_service_with_temp_dir.render(None, {})
        assert "cannot be null or empty" in str(exc_info.value)


class TestTemplateCache:
    """Test template caching functionality."""

    def test_template_cached_after_first_load(self, template_service_with_temp_dir):
        """Test that templates are cached after first load."""
        assert template_service_with_temp_dir.get_cache_size() == 0
        
        # First render
        template_service_with_temp_dir.render("simple.j2", {"name": "Test"})
        assert template_service_with_temp_dir.get_cache_size() == 1
        
        # Second render should use cache
        template_service_with_temp_dir.render("simple.j2", {"name": "Test2"})
        assert template_service_with_temp_dir.get_cache_size() == 1

    def test_clear_specific_template_cache(self, template_service_with_temp_dir):
        """Test clearing cache for specific template."""
        template_service_with_temp_dir.render("simple.j2", {"name": "Test"})
        template_service_with_temp_dir.render("conditional.j2", {"name": "Test"})
        assert template_service_with_temp_dir.get_cache_size() == 2
        
        # Clear specific template
        template_service_with_temp_dir.clear_cache("simple.j2")
        assert template_service_with_temp_dir.get_cache_size() == 1

    def test_clear_all_cache(self, template_service_with_temp_dir):
        """Test clearing all cached templates."""
        template_service_with_temp_dir.render("simple.j2", {"name": "Test"})
        template_service_with_temp_dir.render("conditional.j2", {"name": "Test"})
        assert template_service_with_temp_dir.get_cache_size() == 2
        
        # Clear all
        template_service_with_temp_dir.clear_cache()
        assert template_service_with_temp_dir.get_cache_size() == 0

    def test_clear_nonexistent_template_from_cache(self, template_service_with_temp_dir):
        """Test clearing cache for template that's not cached."""
        template_service_with_temp_dir.render("simple.j2", {"name": "Test"})
        assert template_service_with_temp_dir.get_cache_size() == 1
        
        # Clear non-existent
        template_service_with_temp_dir.clear_cache("nonexistent.j2")
        assert template_service_with_temp_dir.get_cache_size() == 1


class TestCSVLoading:
    """Test CSV loading and parsing functionality."""

    def test_load_csv_as_list(self, template_service_with_temp_dir, temp_template_dir):
        """Test loading CSV file as list of dictionaries."""
        rows = template_service_with_temp_dir.load_csv_as_list(str(temp_template_dir / "test-data.csv"))
        
        assert len(rows) == 3
        assert rows[0]["firstName"] == "John"
        assert rows[0]["lastName"] == "Doe"
        assert rows[1]["firstName"] == "Jane"
        assert rows[2]["email"] == "bob@example.com"

    def test_load_csv_as_dict_first_row(self, template_service_with_temp_dir, temp_template_dir):
        """Test loading first CSV row as dictionary."""
        row = template_service_with_temp_dir.load_csv_as_dict(str(temp_template_dir / "test-data.csv"), 0)
        
        assert row["firstName"] == "John"
        assert row["lastName"] == "Doe"
        assert row["email"] == "john@example.com"
        assert row["age"] == "30"

    def test_load_csv_as_dict_middle_row(self, template_service_with_temp_dir, temp_template_dir):
        """Test loading middle CSV row as dictionary."""
        row = template_service_with_temp_dir.load_csv_as_dict(str(temp_template_dir / "test-data.csv"), 1)
        
        assert row["firstName"] == "Jane"
        assert row["email"] == "jane@example.com"

    def test_load_csv_as_dict_last_row(self, template_service_with_temp_dir, temp_template_dir):
        """Test loading last CSV row as dictionary."""
        row = template_service_with_temp_dir.load_csv_as_dict(str(temp_template_dir / "test-data.csv"), 2)
        
        assert row["firstName"] == "Bob"
        assert row["lastName"] == "Johnson"

    def test_load_csv_invalid_row_index(self, template_service_with_temp_dir, temp_template_dir):
        """Test loading CSV with invalid row index."""
        with pytest.raises(TemplateException) as exc_info:
            template_service_with_temp_dir.load_csv_as_dict(str(temp_template_dir / "test-data.csv"), 10)
        assert "out of bounds" in str(exc_info.value)

    def test_load_csv_negative_row_index(self, template_service_with_temp_dir, temp_template_dir):
        """Test loading CSV with negative row index."""
        with pytest.raises(TemplateException) as exc_info:
            template_service_with_temp_dir.load_csv_as_dict(str(temp_template_dir / "test-data.csv"), -1)
        assert "out of bounds" in str(exc_info.value)

    def test_load_csv_file_not_found(self, template_service_with_temp_dir):
        """Test loading non-existent CSV file."""
        with pytest.raises(TemplateException) as exc_info:
            template_service_with_temp_dir.load_csv_as_list("nonexistent.csv")
        assert "not found" in str(exc_info.value).lower()

    def test_load_csv_empty_path(self, template_service_with_temp_dir):
        """Test loading CSV with empty path."""
        with pytest.raises(TemplateException) as exc_info:
            template_service_with_temp_dir.load_csv_as_list("")
        assert "cannot be null or empty" in str(exc_info.value)

    def test_load_csv_none_path(self, template_service_with_temp_dir):
        """Test loading CSV with None path."""
        with pytest.raises(TemplateException) as exc_info:
            template_service_with_temp_dir.load_csv_as_list(None)
        assert "cannot be null or empty" in str(exc_info.value)


class TestRenderWithCSV:
    """Test rendering templates with CSV data."""

    def test_render_with_csv_first_row(self, template_service_with_temp_dir, temp_template_dir):
        """Test rendering template with CSV data from first row."""
        result = template_service_with_temp_dir.render_with_csv(
            "user.json.j2",
            str(temp_template_dir / "test-data.csv"),
            row_index=0
        )
        
        data = json.loads(result)
        assert data["firstName"] == "John"
        assert data["lastName"] == "Doe"

    def test_render_with_csv_specific_row(self, template_service_with_temp_dir, temp_template_dir):
        """Test rendering template with CSV data from specific row."""
        result = template_service_with_temp_dir.render_with_csv(
            "user.json.j2",
            str(temp_template_dir / "test-data.csv"),
            row_index=1
        )
        
        data = json.loads(result)
        assert data["firstName"] == "Jane"
        assert data["email"] == "jane@example.com"

    def test_render_with_csv_and_additional_context(self, template_service_with_temp_dir, temp_template_dir):
        """Test rendering with CSV data and additional context."""
        result = template_service_with_temp_dir.render_with_csv(
            "user.json.j2",
            str(temp_template_dir / "test-data.csv"),
            row_index=0,
            additional_context={"firstName": "Override"}
        )
        
        data = json.loads(result)
        # Additional context should override CSV data
        assert data["firstName"] == "Override"
        # But other fields should still come from CSV
        assert data["lastName"] == "Doe"

    def test_render_with_csv_invalid_row_index(self, template_service_with_temp_dir, temp_template_dir):
        """Test rendering with invalid CSV row index."""
        with pytest.raises(TemplateException):
            template_service_with_temp_dir.render_with_csv(
                "user.json.j2",
                str(temp_template_dir / "test-data.csv"),
                row_index=999
            )

    def test_render_with_csv_file_not_found(self, template_service_with_temp_dir):
        """Test rendering with non-existent CSV file."""
        with pytest.raises(TemplateException) as exc_info:
            template_service_with_temp_dir.render_with_csv(
                "user.json.j2",
                "nonexistent.csv"
            )
        assert "not found" in str(exc_info.value).lower() or "Failed" in str(exc_info.value)


class TestResourceLoader:
    """Test ResourceLoader functionality."""

    def test_resource_loader_initialization(self):
        """Test ResourceLoader initialization."""
        search_paths = ["templates", "test_templates"]
        loader = ResourceLoader(search_paths)
        assert loader.search_paths == search_paths

    def test_resource_loader_get_source_file_exists(self, temp_template_dir):
        """Test ResourceLoader finding a template file."""
        loader = ResourceLoader([str(temp_template_dir)])
        source, path, _ = loader.get_source(None, "simple.j2")
        
        assert "Hello" in source
        assert "simple.j2" in path

    def test_resource_loader_template_not_found(self):
        """Test ResourceLoader with non-existent template."""
        loader = ResourceLoader(["nonexistent_path"])
        
        with pytest.raises(TemplateNotFound):
            loader.get_source(None, "missing.j2")

    def test_resource_loader_multiple_search_paths(self, temp_template_dir):
        """Test ResourceLoader with multiple search paths."""
        loader = ResourceLoader(["nonexistent", str(temp_template_dir)])
        source, path, _ = loader.get_source(None, "simple.j2")
        
        assert "Hello" in source


class TestTemplateServiceErrorHandling:
    """Test error handling in TemplateService."""

    def test_template_exception_creation(self):
        """Test TemplateException can be raised and caught."""
        with pytest.raises(TemplateException) as exc_info:
            raise TemplateException("Test error")
        assert "Test error" in str(exc_info.value)

    def test_render_invalid_template_syntax(self, template_service_with_temp_dir):
        """Test rendering template with invalid Jinja2 syntax."""
        # Create a template with invalid syntax
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_template = Path(tmpdir) / "bad.j2"
            bad_template.write_text("{% if incomplete %}")
            
            # This should raise an error during template loading/rendering
            with pytest.raises(TemplateException):
                template_service_with_temp_dir.render(str(bad_template), {})

"""Service for generating JSON messages from Jinja2 templates."""

import csv
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import Lock
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
from jinja2.loaders import BaseLoader

logger = logging.getLogger(__name__)


class TemplateException(Exception):
    """Exception raised when template operations fail."""

    pass


class ResourceLoader(BaseLoader):
    """Jinja2 loader that loads templates from Python package resources."""

    def __init__(self, search_paths: List[str]):
        """Initialize the resource loader with search paths."""
        self.search_paths = search_paths

    def get_source(self, environment, template):
        """Load template source from package resources."""
        for search_path in self.search_paths:
            # Try as file path first
            template_path = Path(search_path) / template
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    source = f.read()
                return source, template_path.as_posix(), lambda: True

            # Try as resource path
            try:
                import importlib.resources as pkg_resources

                # Try to load from package
                parts = search_path.split("/")
                if len(parts) > 0:
                    package_name = ".".join(parts[:-1]) if len(parts) > 1 else ""
                    resource_path = parts[-1] if len(parts) > 1 else search_path
                    full_path = f"{resource_path}/{template}" if resource_path else template

                    try:
                        if package_name:
                            source = pkg_resources.files(package_name).joinpath(
                                full_path
                            ).read_text(encoding="utf-8")
                        else:
                            # Try current directory
                            file_path = Path(full_path)
                            if file_path.exists():
                                source = file_path.read_text(encoding="utf-8")
                            else:
                                continue
                        return source, full_path, lambda: True
                    except (FileNotFoundError, ModuleNotFoundError):
                        continue
            except Exception:
                continue

        raise TemplateNotFound(template)


class TemplateService:
    """Service for generating JSON messages from Jinja2 templates."""

    _instance: Optional["TemplateService"] = None
    _lock: Lock = Lock()

    def __init__(self):
        """Initialize the template service."""
        # Default search paths
        search_paths = [
            "templates",
            "src/main/resources/templates",
            "src/test/resources/templates",
        ]

        # Add current working directory templates
        cwd_templates = Path.cwd() / "templates"
        if cwd_templates.exists():
            search_paths.insert(0, str(cwd_templates))

        # Create Jinja2 environment with resource loader
        self._env = Environment(
            loader=ResourceLoader(search_paths),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._template_cache: Dict[str, Template] = {}
        logger.info("TemplateService initialized")

    @classmethod
    def get_instance(cls) -> "TemplateService":
        """Get singleton instance of TemplateService."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def render(
        self, template_path: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render a Jinja2 template with the provided context variables.

        Args:
            template_path: Path to the template file (e.g., "templates/user-create.json.j2")
            context: Dictionary of variables to use in the template

        Returns:
            Rendered template as a string (typically JSON)

        Raises:
            TemplateException: If template cannot be loaded or rendered
        """
        if not template_path or not template_path.strip():
            raise TemplateException("Template path cannot be null or empty")

        context = context or {}

        try:
            template = self._get_template(template_path)
            result = template.render(**context)
            logger.debug("Successfully rendered template: %s", template_path)
            return result
        except TemplateNotFound as e:
            logger.error("Template not found: %s", template_path)
            raise TemplateException(f"Template not found: {template_path}") from e
        except Exception as e:
            logger.error("Error rendering template: %s", template_path, exc_info=True)
            raise TemplateException(
                f"Failed to render template: {template_path}"
            ) from e

    def render_with_csv(
        self,
        template_path: str,
        csv_file_path: str,
        row_index: int = 0,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render a Jinja2 template using data loaded from a CSV file.

        Args:
            template_path: Path to the template file
            csv_file_path: Path to the CSV data file
            row_index: Zero-based index of the data row to use (0 = first data row after header)
            additional_context: Optional dictionary of additional variables to merge with CSV data

        Returns:
            Rendered template as a string

        Raises:
            TemplateException: If template or CSV file cannot be loaded
        """
        csv_data = self.load_csv_as_dict(csv_file_path, row_index)

        # Merge with additional context (additional_context takes precedence)
        merged_context = {**csv_data}
        if additional_context:
            merged_context.update(additional_context)

        return self.render(template_path, merged_context)

    def _get_template(self, template_path: str) -> Template:
        """
        Get a template, loading it from cache if available.

        Args:
            template_path: Path to the template file

        Returns:
            Jinja2 Template instance
        """
        if template_path not in self._template_cache:
            try:
                logger.debug("Loading template: %s", template_path)
                template = self._env.get_template(template_path)
                self._template_cache[template_path] = template
                logger.debug("Template loaded successfully: %s", template_path)
            except TemplateNotFound as e:
                logger.error("Failed to load template: %s", template_path)
                raise TemplateException(
                    f"Template not found or cannot be loaded: {template_path}"
                ) from e
        return self._template_cache[template_path]

    def clear_cache(self, template_path: Optional[str] = None) -> None:
        """
        Clear the template cache.

        Args:
            template_path: Optional specific template path to clear. If None, clears all.
        """
        if template_path:
            if template_path in self._template_cache:
                del self._template_cache[template_path]
                logger.debug("Removed template from cache: %s", template_path)
        else:
            logger.info("Clearing template cache")
            self._template_cache.clear()

    def get_cache_size(self) -> int:
        """Get the number of templates currently cached."""
        return len(self._template_cache)

    def load_csv_as_dict(
        self, csv_file_path: str, row_index: int = 0
    ) -> Dict[str, str]:
        """
        Load a CSV file and parse it into a dictionary.

        The first row is treated as headers (column names), and the specified data row
        is parsed into a dictionary with header names as keys.

        Args:
            csv_file_path: Path to the CSV file (e.g., "templates/user-data.csv")
            row_index: Zero-based index of the data row to parse (0 = first data row after header)

        Returns:
            Dictionary with column headers as keys and row values as values

        Raises:
            TemplateException: If CSV file cannot be loaded or parsed
        """
        if not csv_file_path or not csv_file_path.strip():
            raise TemplateException("CSV file path cannot be null or empty")

        try:
            logger.debug("Loading CSV file: %s", csv_file_path)
            all_rows = self.load_csv_as_list(csv_file_path)

            if not all_rows:
                raise TemplateException(f"CSV file is empty: {csv_file_path}")

            if row_index < 0 or row_index >= len(all_rows):
                raise TemplateException(
                    f"Row index {row_index} is out of bounds. "
                    f"CSV has {len(all_rows)} data row(s)"
                )

            logger.debug(
                "Successfully loaded CSV row %d from %s", row_index, csv_file_path
            )
            return all_rows[row_index]
        except TemplateException:
            raise
        except Exception as e:
            logger.error("Failed to load or parse CSV file: %s", csv_file_path, exc_info=True)
            raise TemplateException(
                f"Failed to load or parse CSV file: {csv_file_path}"
            ) from e

    def load_csv_as_list(self, csv_file_path: str) -> List[Dict[str, str]]:
        """
        Load a CSV file and parse all data rows into a list of dictionaries.

        Args:
            csv_file_path: Path to the CSV file (e.g., "templates/user-data.csv")

        Returns:
            List of dictionaries, where each dictionary represents a data row with headers as keys

        Raises:
            TemplateException: If CSV file cannot be loaded or parsed
        """
        if not csv_file_path or not csv_file_path.strip():
            raise TemplateException("CSV file path cannot be null or empty")

        try:
            logger.debug("Loading CSV file: %s", csv_file_path)

            # Try to find the CSV file
            csv_path = None
            # Try as file path first
            if Path(csv_file_path).exists():
                csv_path = Path(csv_file_path)
            else:
                # Try in templates directory
                for search_path in ["templates", "src/main/resources/templates", "src/test/resources/templates"]:
                    potential_path = Path(search_path) / csv_file_path
                    if potential_path.exists():
                        csv_path = potential_path
                        break

            if csv_path is None:
                raise TemplateException(f"CSV file not found: {csv_file_path}")

            rows = []
            with open(csv_path, "r", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    # Convert all values to strings and strip whitespace
                    cleaned_row = {k: v.strip() if v else "" for k, v in row.items()}
                    rows.append(cleaned_row)

            logger.debug(
                "Successfully loaded %d row(s) from CSV file: %s",
                len(rows),
                csv_file_path,
            )
            return rows
        except TemplateException:
            raise
        except Exception as e:
            logger.error("Failed to load or parse CSV file: %s", csv_file_path, exc_info=True)
            raise TemplateException(
                f"Failed to load or parse CSV file: {csv_file_path}"
            ) from e


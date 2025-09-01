"""Utility functions."""

import logging
from logging import config as logging_config
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

from .config import Settings

LOG = logging.getLogger(__name__)


def configure_logging(cnf: Settings) -> None:
    """Configure logging from settings."""
    logging_config.dictConfig(cnf.build_logging_config())


class JinjaTemplateRepo:
    """Load jinja template environment."""

    _env: Environment | None = None

    @classmethod
    def setup(cls, template_dir: Path):
        """Setup jinja2 environment."""
        if cls._env is not None:
            raise RuntimeError("Template environment already loaded!")
        loader = FileSystemLoader(template_dir)
        cls._env = Environment(loader=loader)
        LOG.info("Loaded jinja2 template directory: %s", template_dir)

    @classmethod
    def get_template(cls, name: str | None = None) -> Template:
        """Get template with id either get default template."""
        if cls._env is None:
            raise RuntimeError("Template environment has not been loaded; run setup()!")
        template_name: str = "default_email" if name is None else name
        try:
            return cls._env.get_template(template_name)
        except TemplateNotFound:
            all_templates = cls._env.list_templates()
            LOG.error(
                "Cant find template: %s; templates in dir: %s",
                template_name,
                ", ".join(all_templates),
            )
            raise

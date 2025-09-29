"""Manage jinja2 templates."""

import logging
from pathlib import Path
from typing import Sequence

import bonsai_notification
from jinja2 import (ChoiceLoader, Environment, FileSystemLoader, PackageLoader,
                    Template, TemplateNotFound, select_autoescape)

LOG = logging.getLogger(__name__)


def _make_loader(custom_template_dir: Path | None = None) -> ChoiceLoader:
    """
    Build a ChoiceLoader that searches user-supplied templates first,
    then falls back to templates packaged under `notification_service/templates`.
    """
    loaders: list[FileSystemLoader | PackageLoader] = []

    if custom_template_dir is not None:
        if not custom_template_dir.exists():
            LOG.error(
                "Custom template directory does not exist: %s", custom_template_dir
            )
        loaders.append(FileSystemLoader(str(custom_template_dir)))

    # add default directory
    loaders.append(PackageLoader(bonsai_notification.__name__, "templates"))
    return ChoiceLoader(loaders)


class TemplateRepository:
    """Load jinja template with precedence order:
        1. custom templates (if provided)
        2. built in templates (notificatoin_service/templates)

    If a requested template is not found it will fallback to default_template.
    """

    def __init__(
        self,
        custom_template_dir: Path,
        auto_reload: bool = True,
        default_template: str = "default.html",
    ) -> None:
        """Setup jinja2 template environment."""

        self._template_dir: Path = custom_template_dir
        self._auto_reload: bool = auto_reload
        self._default_template: str = default_template

        LOG.debug(
            "Creating TemplateRepository(user_template_dir=%s, auto_reload=%s, default_template=%s)",
            str(custom_template_dir) if custom_template_dir else None,
            auto_reload,
            default_template,
        )

        self._env = Environment(
            loader=_make_loader(custom_template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            auto_reload=auto_reload,
            enable_async=False,  # flip to True if you plan to use async rendering
        )

    @property
    def search_paths(self) -> Sequence[str]:
        """Return the paths that are searched for templates."""
        paths: list[str] = []
        if self._template_dir is not None:
            paths.append(str(self._template_dir))
        # Represent the package loader path symbolically
        paths.append("pkg://notification_service/templates")
        return paths

    def get_template(self, name: str | None = None) -> Template:
        """Get template named `name`. If name is None use the `default_template`.

        If the template `name` does not exist fallback to `default_template`.
        """
        requested: str = self._default_template if name is None else name
        try:
            return self._env.get_template(requested)
        except TemplateNotFound as first_exec:
            LOG.warning(
                "Template '%s' not found. Will try default '%s'.",
                requested,
                self._default_template,
            )

            # dont try if the default template already have been requested
            if requested != self._default_template:
                try:
                    return self._env.get_template(self._default_template)
                except TemplateNotFound:
                    pass  # fall through to final error

            all_templates = sorted(self.list_templates())

            raise RuntimeError(
                "Template resolution failed. "
                f"Requested='{requested}', default='{self._default_template}'. "
                f"Searched in: {', '.join(self.search_paths)}. "
                f"Available: {', '.join(all_templates) if all_templates else 'none'}."
            ) from first_exec

    def list_templates(self) -> list[str]:
        """List all templates in environment."""
        return self._env.list_templates()

    def render(self, name: str | None = None, **context) -> str:
        """
        Convenience wrapper around get_template(...).render(**context).
        If `name` is None, renders the default template.
        """
        return self.get_template(name).render(**context)

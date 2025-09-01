from pathlib import Path

import pytest

from notification_service.utils import JinjaTemplateRepo


def test_jinja_template_repo_setup(tmp_path):
    """Test that template is being read and templated."""

    # Create a dummy template file
    template_dir = tmp_path
    (template_dir / "default_email").write_text("Hello {{ message }}")
    JinjaTemplateRepo._env = None  # Reset for test
    JinjaTemplateRepo.setup(template_dir)
    template = JinjaTemplateRepo.get_template("default_email")
    result = template.render(message="World")
    assert "Hello World" in result

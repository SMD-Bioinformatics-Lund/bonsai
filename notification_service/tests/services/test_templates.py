from pathlib import Path
from bonsai_notification.services.templates import TemplateRepository


def test_jinja_template_repo_setup(tmp_path: Path):
    """Test that template is being read and templated."""

    # Create a dummy template file
    template_dir = tmp_path
    (template_dir / "default_email").write_text("Hello {{ message }}")
    repo = TemplateRepository(custom_template_dir=template_dir)
    template = repo.get_template("default_email")
    result = template.render(message="World")
    assert "Hello World" in result

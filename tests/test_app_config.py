import pytest

from app.config import AppConfig


def test_app_config_accepts_supported_render_modes():
    for mode in ["text", "markdown", "pandoc", "empty_right"]:
        config = AppConfig(render_mode=mode)
        assert config.render_mode == mode


def test_app_config_rejects_unknown_render_modes():
    with pytest.raises(ValueError):
        AppConfig(render_mode="unknown")


def test_app_config_accepts_supported_output_modes():
    for mode in [
        "PDF讲解版",
        "Markdown截图讲解",
        "HTML截图版",
        "HTML-pdf2htmlEX版",
    ]:
        config = AppConfig(output_mode=mode)
        assert config.output_mode == mode


def test_app_config_rejects_unknown_output_modes():
    with pytest.raises(ValueError):
        AppConfig(output_mode="invalid")

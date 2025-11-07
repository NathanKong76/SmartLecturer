from types import SimpleNamespace

import pytest

from app.ui_helpers import validate_file_upload


class DummyFile(SimpleNamespace):
    pass


def test_validate_file_upload_requires_api_key_for_openai():
    files = [DummyFile()]
    params = {"llm_provider": "openai", "api_key": ""}

    is_valid, message = validate_file_upload(files, params)

    assert not is_valid
    assert message == "请在侧边栏填写 OpenAI API Key"


def test_validate_file_upload_requires_api_key_for_gemini():
    files = [DummyFile()]
    params = {"llm_provider": "gemini", "api_key": ""}

    is_valid, message = validate_file_upload(files, params)

    assert not is_valid
    assert message == "请在侧边栏填写 GEMINI_API_KEY"


def test_validate_file_upload_accepts_when_api_key_present():
    files = [DummyFile()]
    params = {"llm_provider": "gemini", "api_key": "test"}

    is_valid, message = validate_file_upload(files, params)

    assert is_valid
    assert message is None

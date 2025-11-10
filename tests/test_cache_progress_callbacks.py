"""
Tests that cached-result shortcuts still emit progress/page updates.

The UI relies on these callbacks to transition files from waiting -> processing
before completion, so skipping them causes the observed waiting→completed jump.
"""

import sys
import types
import unittest
from unittest.mock import patch

# Provide lightweight stubs for optional heavy dependencies so app.ui_helpers can import.
if "langchain_google_genai" not in sys.modules:
    class _FakeChatGoogleGenerativeAI:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, *args, **kwargs):
            class _Resp:
                content = ""
            return _Resp()

    sys.modules["langchain_google_genai"] = types.SimpleNamespace(
        ChatGoogleGenerativeAI=_FakeChatGoogleGenerativeAI
    )

if "langchain_core.messages" not in sys.modules:
    class _HumanMessage:  # Minimal placeholder used by Gemini client
        def __init__(self, content):
            self.content = content

    langchain_core = types.ModuleType("langchain_core")
    messages_module = types.ModuleType("langchain_core.messages")
    messages_module.HumanMessage = _HumanMessage
    langchain_core.messages = messages_module
    sys.modules["langchain_core"] = langchain_core
    sys.modules["langchain_core.messages"] = messages_module

if "langchain_openai" not in sys.modules:
    class _FakeChatOpenAI:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, *args, **kwargs):
            class _Resp:
                content = ""
            return _Resp()

    sys.modules["langchain_openai"] = types.SimpleNamespace(ChatOpenAI=_FakeChatOpenAI)

from app.ui_helpers import (
    process_single_file_markdown,
    process_single_file_html_screenshot,
    process_single_file_html_pdf2htmlex,
)


class TestCacheProgressCallbacks(unittest.TestCase):
    """Ensure cached flows still drive progress callbacks."""

    def setUp(self):
        self.filename = "test.pdf"
        self.src_bytes = b"%PDF-1.4"
        self.file_hash = "hash"
        self.cached_result = {
            "status": "completed",
            "explanations": {
                0: "Page 1",
                1: "Page 2",
                2: "Page 3",
                3: "Page 4",
            },
            "failed_pages": [2],  # 1-based index for page 2
        }
        self.params = {
            "api_key": "key",
            "model_name": "model",
            "user_prompt": "prompt",
            "temperature": 0.2,
            "max_tokens": 1024,
            "dpi": 144,
            "screenshot_dpi": 96,
            "concurrency": 2,
            "rpm_limit": 100,
            "tpm_budget": 1000,
            "rpd_limit": 50,
            "embed_images": True,
            "markdown_title": "Title",
            "cjk_font_name": "SimHei",
            "font_size": 14,
            "line_spacing": 1.2,
            "html_column_count": 2,
            "html_column_gap": 18,
            "html_show_column_rule": True,
            "right_ratio": 0.5,
            "render_mode": "markdown",
            "column_padding": 12,
            "use_context": False,
            "context_prompt": None,
            "llm_provider": "gemini",
            "api_base": None,
        }

    def _capture_callbacks(self):
        progress_calls = []

        def on_progress(done, total):
            progress_calls.append((done, total))

        page_calls = []

        def on_page_status(idx, status, error):
            page_calls.append((idx, status, error))

        return progress_calls, on_progress, page_calls, on_page_status

    def _assert_callbacks(self, progress_calls, page_calls, total_pages=4):
        self.assertEqual(progress_calls, [(0, total_pages), (total_pages, total_pages)])
        self.assertEqual(len(page_calls), total_pages)
        # Ensure failed page (1-based #2 -> index 1) recorded properly
        failed_entry = page_calls[1]
        self.assertEqual(failed_entry[0], 1)
        self.assertEqual(failed_entry[1], "failed")
        self.assertIsNotNone(failed_entry[2])
        for idx, status, _ in page_calls:
            if idx != 1:
                self.assertEqual(status, "completed")

    @patch("app.ui_helpers._get_total_pages_from_pdf", return_value=4)
    @patch("app.ui_helpers.pdf_processor.process_markdown_mode")
    def test_markdown_cache_emits_progress(self, mock_markdown_mode, mock_total_pages):
        """Markdown-mode cache should notify callbacks before finishing."""
        mock_markdown_mode.return_value = (
            "markdown content",
            self.cached_result["explanations"],
            [],
            None,
        )
        progress_calls, on_progress, page_calls, on_page_status = self._capture_callbacks()

        result = process_single_file_markdown(
            None,
            self.filename,
            self.src_bytes,
            self.params,
            self.cached_result,
            self.file_hash,
            on_progress=on_progress,
            on_page_status=on_page_status,
        )

        self._assert_callbacks(progress_calls, page_calls)
        self.assertEqual(result["status"], "completed")
        mock_markdown_mode.assert_called_once()
        mock_total_pages.assert_called_once()

    @patch("app.ui_helpers._get_total_pages_from_pdf", return_value=4)
    @patch("app.ui_helpers.pdf_processor.generate_html_screenshot_document", return_value="<html></html>")
    def test_html_screenshot_cache_emits_progress(self, mock_html_generator, mock_total_pages):
        """HTML screenshot mode cache should notify callbacks before finishing."""
        progress_calls, on_progress, page_calls, on_page_status = self._capture_callbacks()

        result = process_single_file_html_screenshot(
            None,
            self.filename,
            self.src_bytes,
            self.params,
            self.cached_result,
            self.file_hash,
            on_progress=on_progress,
            on_page_status=on_page_status,
        )

        self._assert_callbacks(progress_calls, page_calls)
        self.assertEqual(result["status"], "completed")
        mock_html_generator.assert_called_once()
        mock_total_pages.assert_called_once()

    @patch("app.ui_helpers._get_total_pages_from_pdf", return_value=4)
    @patch("app.ui_helpers.pdf_processor.generate_html_pdf2htmlex_document", return_value="<html></html>")
    def test_pdf2htmlex_cache_emits_progress(self, mock_html_generator, mock_total_pages):
        """HTML pdf2htmlEX mode cache should notify callbacks before finishing."""
        progress_calls, on_progress, page_calls, on_page_status = self._capture_callbacks()

        result = process_single_file_html_pdf2htmlex(
            None,
            self.filename,
            self.src_bytes,
            self.params,
            self.cached_result,
            self.file_hash,
            on_progress=on_progress,
            on_page_status=on_page_status,
        )

        self._assert_callbacks(progress_calls, page_calls)
        self.assertEqual(result["status"], "completed")
        mock_html_generator.assert_called_once()
        mock_total_pages.assert_called_once()


if __name__ == "__main__":
    unittest.main()

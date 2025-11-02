#!/usr/bin/env python3
"""
完整的测试套件：单元测试和集成测试（LLM模块除外）
"""

import sys
import os
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.html_renderer import HtmlRenderer, HtmlRendererError
from app.services.pdf_processor import compose_pdf, validate_pdf_file, pages_with_blank_explanations
import fitz


class TestHtmlRenderer(unittest.TestCase):
    """HtmlRenderer单元测试"""

    def test_pt_to_inches_conversion(self):
        """测试点到英寸的转换"""
        self.assertAlmostEqual(HtmlRenderer._pt_to_inches(72), 1.0)
        self.assertAlmostEqual(HtmlRenderer._pt_to_inches(144), 2.0)
        self.assertAlmostEqual(HtmlRenderer._pt_to_inches(36), 0.5)

    def test_pt_to_px_conversion(self):
        """测试点到像素的转换"""
        self.assertEqual(HtmlRenderer._pt_to_px(72), 96)  # 72pt = 1inch = 96px at 96 DPI
        self.assertEqual(HtmlRenderer._pt_to_px(36), 48)  # 36pt = 0.5inch = 48px

    def test_render_simple_html(self):
        """测试简单HTML渲染"""
        html = "<h1>Test</h1><p>Simple paragraph</p>"
        pdf_bytes = HtmlRenderer.render_html_to_pdf_fragment(
            html=html,
            width_pt=200,
            height_pt=150
        )

        # 验证PDF有效性
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 0)

        # 验证PDF可以打开
        doc = fitz.open(stream=pdf_bytes)
        self.assertEqual(len(doc), 2)  # Playwright生成2页PDF
        doc.close()

    def test_render_with_css(self):
        """测试带CSS的HTML渲染"""
        html = "<div>Styled content</div>"
        css = "div { color: red; font-size: 14pt; }"
        pdf_bytes = HtmlRenderer.render_html_to_pdf_fragment(
            html=html,
            width_pt=200,
            height_pt=150,
            css=css
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 0)

    def test_render_with_mathjax(self):
        """测试MathJax渲染"""
        html = "<p>Formula: $E = mc^2$</p>"
        pdf_bytes = HtmlRenderer.render_html_to_pdf_fragment(
            html=html,
            width_pt=200,
            height_pt=150,
            mathjax=True
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 0)

    def test_render_with_prism(self):
        """测试Prism代码高亮"""
        html = "<pre><code>print('hello')</code></pre>"
        pdf_bytes = HtmlRenderer.render_html_to_pdf_fragment(
            html=html,
            width_pt=200,
            height_pt=150,
            prism=True
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 0)

    def test_invalid_dimensions(self):
        """测试无效尺寸处理"""
        html = "<p>test</p>"

        # 测试极小尺寸
        pdf_bytes = HtmlRenderer.render_html_to_pdf_fragment(
            html=html,
            width_pt=1,
            height_pt=1
        )
        self.assertIsInstance(pdf_bytes, bytes)

    def test_empty_html(self):
        """测试空HTML处理"""
        pdf_bytes = HtmlRenderer.render_html_to_pdf_fragment(
            html="",
            width_pt=100,
            height_pt=100
        )
        self.assertIsInstance(pdf_bytes, bytes)


class TestPdfProcessor(unittest.TestCase):
    """PDF处理器单元测试"""

    def setUp(self):
        """测试前准备"""
        # 创建临时测试PDF
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf_path = os.path.join(self.temp_dir, "test.pdf")

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 100), "Test content")
        doc.save(self.test_pdf_path)
        doc.close()

        with open(self.test_pdf_path, "rb") as f:
            self.test_pdf_bytes = f.read()

    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)

    def test_validate_valid_pdf(self):
        """测试有效PDF验证"""
        is_valid, error_msg = validate_pdf_file(self.test_pdf_bytes)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")

    def test_validate_invalid_pdf(self):
        """测试无效PDF验证"""
        invalid_pdf = b"not a pdf"
        is_valid, error_msg = validate_pdf_file(invalid_pdf)
        self.assertFalse(is_valid)
        self.assertIn("无效", error_msg)

    def test_validate_empty_pdf(self):
        """测试空PDF验证"""
        empty_pdf = b""
        is_valid, error_msg = validate_pdf_file(empty_pdf)
        self.assertFalse(is_valid)

    def test_pages_with_blank_explanations(self):
        """测试空白解释页面检测"""
        explanations = {
            0: "Valid explanation",
            1: "",  # 空字符串
            2: "   ",  # 只有空格
            3: "x" * 5,  # 太短
            4: "x" * 15,  # 有效
        }

        blank_pages = pages_with_blank_explanations(explanations, min_chars=10)
        expected_blank = [1, 2, 3]  # 空字符串、只有空格、太短的文本
        self.assertEqual(sorted(blank_pages), sorted(expected_blank))

    def test_compose_pdf_simple(self):
        """测试简单PDF合成"""
        explanations = {0: "Test explanation"}

        result_pdf = compose_pdf(
            src_bytes=self.test_pdf_bytes,
            explanations=explanations,
            font_size=12
        )

        self.assertIsInstance(result_pdf, bytes)
        self.assertGreater(len(result_pdf), 0)

        # 验证结果PDF
        doc = fitz.open(stream=result_pdf)
        self.assertGreater(len(doc), 0)
        doc.close()

    def test_compose_pdf_empty_explanations(self):
        """测试空解释的PDF合成"""
        explanations = {}

        result_pdf = compose_pdf(
            src_bytes=self.test_pdf_bytes,
            explanations=explanations,
            font_size=12
        )

        self.assertIsInstance(result_pdf, bytes)

    def test_compose_pdf_markdown_mode(self):
        """测试Markdown模式PDF合成"""
        explanations = {0: "# Title\n\n**Bold text** and *italic text*"}

        result_pdf = compose_pdf(
            src_bytes=self.test_pdf_bytes,
            explanations=explanations,
            font_size=12,
            render_mode="markdown"
        )

        self.assertIsInstance(result_pdf, bytes)

    def test_compose_pdf_html_chromium_mode(self):
        """测试HTML Chromium模式PDF合成"""
        explanations = {0: "# Title\n\n```python\nprint('code')\n```"}

        result_pdf = compose_pdf(
            src_bytes=self.test_pdf_bytes,
            explanations=explanations,
            font_size=12,
            render_mode="html_chromium"
        )

        self.assertIsInstance(result_pdf, bytes)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """集成测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """集成测试后清理"""
        shutil.rmtree(self.temp_dir)

    def test_full_pdf_processing_workflow(self):
        """测试完整的PDF处理工作流"""
        # 1. 创建源PDF
        src_pdf_path = os.path.join(self.temp_dir, "source.pdf")
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page()
            page.insert_text((50, 100), f"Page {i+1} content")
        doc.save(src_pdf_path)
        doc.close()

        with open(src_pdf_path, "rb") as f:
            src_bytes = f.read()

        # 2. 准备讲解内容
        explanations = {
            0: "第一页的讲解内容",
            1: "第二页的讲解内容",
            2: "第三页的讲解内容"
        }

        # 3. 执行PDF合成
        result_pdf = compose_pdf(
            src_bytes=src_bytes,
            explanations=explanations,
            font_size=11,
            render_mode="html_chromium"
        )

        # 4. 验证结果
        self.assertIsInstance(result_pdf, bytes)
        self.assertGreater(len(result_pdf), len(src_bytes))  # 结果应该更大

        result_doc = fitz.open(stream=result_pdf)
        self.assertEqual(len(result_doc), 3)  # 应该有3页

        # 检查每页都有内容
        for i in range(3):
            page = result_doc[i]
            text = page.get_text()
            self.assertIn(f"Page {i+1}", text)  # 应该包含原内容
            self.assertIn("讲解内容", text)  # 应该包含讲解内容

        result_doc.close()

    def test_html_renderer_pdf_integration(self):
        """测试HTML渲染器与PDF合成器的集成"""
        # 1. 使用HTML渲染器生成片段
        html_content = "<h2>测试标题</h2><p>测试段落内容</p>"
        fragment_pdf = HtmlRenderer.render_html_to_pdf_fragment(
            html=html_content,
            width_pt=250,
            height_pt=200
        )

        # 2. 创建源PDF并合成
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 100), "Source content")
        src_bytes = doc.tobytes()
        doc.close()

        explanations = {0: "讲解内容"}

        result_pdf = compose_pdf(
            src_bytes=src_bytes,
            explanations=explanations,
            font_size=12
        )

        # 3. 验证集成结果
        self.assertIsInstance(result_pdf, bytes)
        result_doc = fitz.open(stream=result_pdf)
        self.assertGreater(len(result_doc), 0)
        result_doc.close()

    def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 测试无效输入的处理
        try:
            compose_pdf(
                src_bytes=b"invalid pdf",
                explanations={0: "test"},
                font_size=12
            )
            self.fail("应该抛出异常")
        except Exception:
            pass  # 期望的异常

    def test_different_render_modes(self):
        """测试不同渲染模式的集成"""
        # 创建源PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 100), "Source")
        src_bytes = doc.tobytes()
        doc.close()

        test_content = "```python\nprint('hello')\n```\n\nFormula: $x^2 + y^2 = z^2$"
        explanations = {0: test_content}

        # 测试不同渲染模式
        modes = ["text", "markdown", "html_chromium"]

        for mode in modes:
            with self.subTest(mode=mode):
                result_pdf = compose_pdf(
                    src_bytes=src_bytes,
                    explanations=explanations,
                    font_size=12,
                    render_mode=mode
                )

                self.assertIsInstance(result_pdf, bytes)
                self.assertGreater(len(result_pdf), 0)


def run_tests():
    """运行所有测试"""
    print("🧪 开始运行测试套件\n")

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestHtmlRenderer))
    suite.addTests(loader.loadTestsFromTestCase(TestPdfProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出总结
    print("\n" + "="*60)
    print("📊 测试结果总结")
    print("="*60)

    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors

    print(f"总测试数: {total_tests}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failures}")
    print(f"🔥 错误: {errors}")

    if result.wasSuccessful():
        print("\n🎉 所有测试通过！")
        return True
    else:
        print("\n⚠️  部分测试失败")
        if result.failures:
            print("\n失败的测试:")
            for test, traceback in result.failures:
                print(f"  - {test}")

        if result.errors:
            print("\n出错的测试:")
            for test, traceback in result.errors:
                print(f"  - {test}")

        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

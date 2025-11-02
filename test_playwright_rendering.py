#!/usr/bin/env python3
"""
测试Playwright渲染和PDF合成功能
"""

import sys
import os
import traceback
from typing import Dict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.html_renderer import HtmlRenderer
from app.services.pdf_processor import compose_pdf
import fitz


def test_html_to_pdf_fragment():
    """测试HTML到PDF片段的转换"""
    print("=== 测试HTML到PDF片段转换 ===\n")

    try:
        # 测试简单的HTML
        html_content = "<h1>测试标题</h1><p>这是一个测试段落，包含<b>粗体</b>和<i>斜体</i>文本。</p>"

        pdf_bytes = HtmlRenderer.render_html_to_pdf_fragment(
            html=html_content,
            width_pt=200,  # 200pt ≈ 2.78英寸
            height_pt=150,  # 150pt ≈ 2.08英寸
            css="body { font-size: 12pt; }",
            background="white"
        )

        # 保存测试PDF
        with open("test_fragment_simple.pdf", "wb") as f:
            f.write(pdf_bytes)

        print(f"✅ 简单HTML转换成功，大小: {len(pdf_bytes)} bytes")
        print("   已保存为: test_fragment_simple.pdf")

        # 测试包含代码和公式的复杂HTML
        complex_html = """
        <h2>代码示例</h2>
        <pre><code>def hello_world():
    print("Hello, 世界!")
    return True</code></pre>

        <h2>数学公式</h2>
        <p>勾股定理: <math><msup><mi>a</mi><mn>2</mn></msup><mo>+</mo><msup><mi>b</mi><mn>2</mn></msup><mo>=</mo><msup><mi>c</mi><mn>2</mn></msup></math></p>

        <h2>列表</h2>
        <ul>
            <li>项目1</li>
            <li>项目2</li>
            <li>项目3</li>
        </ul>
        """

        pdf_bytes_complex = HtmlRenderer.render_html_to_pdf_fragment(
            html=complex_html,
            width_pt=300,
            height_pt=400,
            css="""
            body { font-family: 'SimHei', sans-serif; font-size: 11pt; }
            pre { background: #f5f5f5; padding: 10pt; border-radius: 4pt; }
            code { font-family: 'Consolas', monospace; }
            h2 { color: #333; margin-top: 15pt; }
            ul { margin-left: 20pt; }
            """,
            background="white",
            mathjax=True,
            prism=True
        )

        with open("test_fragment_complex.pdf", "wb") as f:
            f.write(pdf_bytes_complex)

        print(f"✅ 复杂HTML转换成功，大小: {len(pdf_bytes_complex)} bytes")
        print("   已保存为: test_fragment_complex.pdf")

        return True

    except Exception as e:
        print(f"❌ HTML到PDF片段转换失败: {e}")
        traceback.print_exc()
        return False


def test_pdf_composition():
    """测试PDF合成功能"""
    print("\n=== 测试PDF合成功能 ===\n")

    try:
        # 创建源PDF
        print("创建测试源PDF...")
        src_doc = fitz.open()
        page = src_doc.new_page()
        page.insert_text((50, 100), "源PDF内容 - 左侧页面", fontsize=14)
        page.draw_rect([40, 90, 300, 120], color=(0, 0, 1), width=1)  # 蓝色边框
        src_bytes = src_doc.tobytes()
        src_doc.close()

        # 测试讲解内容
        explanations = {
            0: """# 页面讲解

这是一个测试页面的详细讲解内容。

## 主要要点：
1. **内容分析**：本页包含基础文本和图形元素
2. **技术细节**：使用PyMuPDF创建，包含蓝色边框
3. **渲染测试**：验证HTML渲染和PDF合成功能

### 代码示例
```python
# 创建PDF页面
page = doc.new_page()
page.insert_text((x, y), "文本内容")
```

### 数学公式
当 $a \\neq 0$ 时，方程 $ax + b = 0$ 的解为 $x = -\\frac{b}{a}$。

## 总结
通过这个测试验证了完整的渲染和合成流程。"""
        }

        # 执行PDF合成
        print("执行PDF合成...")
        result_bytes = compose_pdf(
            src_bytes=src_bytes,
            explanations=explanations,
            font_size=12,
            font_path=None,
            render_mode="markdown",
            line_spacing=1.4,
            column_padding=10
        )

        # 保存结果
        with open("test_composition_result.pdf", "wb") as f:
            f.write(result_bytes)

        print(f"✅ PDF合成成功，大小: {len(result_bytes)} bytes")
        print("   已保存为: test_composition_result.pdf")

        # 验证合成结果
        print("\n验证合成结果...")
        result_doc = fitz.open(stream=result_bytes)
        if len(result_doc) == 1:
            print("✅ PDF页数正确：1页")
        else:
            print(f"❓ PDF页数异常：{len(result_doc)}页")

        # 检查页面尺寸
        page = result_doc[0]
        width, height = page.rect.width, page.rect.height
        print(f"页面尺寸: {width:.1f} x {height:.1f} 点")

        result_doc.close()

        return True

    except Exception as e:
        print(f"❌ PDF合成失败: {e}")
        traceback.print_exc()
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试错误处理 ===\n")

    try:
        # 测试无效的HTML
        print("测试无效HTML处理...")
        try:
            HtmlRenderer.render_html_to_pdf_fragment(
                html="<invalid><unclosed><tags>",
                width_pt=100,
                height_pt=100
            )
            print("❓ 无效HTML未抛出异常")
        except Exception as e:
            print(f"✅ 无效HTML正确处理: {type(e).__name__}")

        # 测试极小尺寸
        print("测试极小尺寸处理...")
        try:
            HtmlRenderer.render_html_to_pdf_fragment(
                html="<p>test</p>",
                width_pt=1,  # 极小宽度
                height_pt=1   # 极小高度
            )
            print("✅ 极小尺寸处理成功")
        except Exception as e:
            print(f"❓ 极小尺寸处理异常: {e}")

        # 测试空内容
        print("测试空内容处理...")
        try:
            HtmlRenderer.render_html_to_pdf_fragment(
                html="",
                width_pt=100,
                height_pt=100
            )
            print("✅ 空内容处理成功")
        except Exception as e:
            print(f"❓ 空内容处理异常: {e}")

        return True

    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🎯 开始Playwright渲染和PDF合成测试\n")

    results = []

    # 执行各项测试
    results.append(("HTML到PDF片段转换", test_html_to_pdf_fragment()))
    results.append(("PDF合成功能", test_pdf_composition()))
    results.append(("错误处理", test_error_handling()))

    # 输出测试总结
    print("\n" + "="*50)
    print("📊 测试结果总结")
    print("="*50)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} {test_name}")
        if success:
            passed += 1

    print(f"\n总体结果: {passed}/{total} 项测试通过")

    if passed == total:
        print("🎉 所有测试通过！Playwright渲染和PDF合成功能正常。")
    else:
        print("⚠️  部分测试失败，请检查上述错误信息。")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

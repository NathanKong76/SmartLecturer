#!/usr/bin/env python3
"""
快速测试核心功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试导入"""
    print("测试导入...")
    try:
        from app.services.html_renderer import HtmlRenderer
        from app.services.pdf_processor import compose_pdf, validate_pdf_file
        print("✅ 导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_html_renderer():
    """测试HTML渲染器"""
    print("测试HTML渲染器...")
    try:
        from app.services.html_renderer import HtmlRenderer

        html = "<h1>Test</h1><p>Simple test</p>"
        pdf_bytes = HtmlRenderer.render_html_to_pdf_fragment(
            html=html,
            width_pt=200,
            height_pt=150
        )

        if isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 0:
            print("✅ HTML渲染器工作正常")
            return True
        else:
            print("❌ HTML渲染器返回无效数据")
            return False

    except Exception as e:
        print(f"❌ HTML渲染器测试失败: {e}")
        return False

def test_pdf_processor():
    """测试PDF处理器"""
    print("测试PDF处理器...")
    try:
        from app.services.pdf_processor import compose_pdf, validate_pdf_file
        import fitz

        # 创建测试PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 100), "Test content")
        src_bytes = doc.tobytes()
        doc.close()

        # 测试PDF验证
        is_valid, error = validate_pdf_file(src_bytes)
        if not is_valid:
            print(f"❌ PDF验证失败: {error}")
            return False

        # 测试PDF合成
        explanations = {0: "Test explanation"}
        result_pdf = compose_pdf(
            src_bytes=src_bytes,
            explanations=explanations,
            font_size=12
        )

        if isinstance(result_pdf, bytes) and len(result_pdf) > 0:
            print("✅ PDF处理器工作正常")
            return True
        else:
            print("❌ PDF处理器返回无效数据")
            return False

    except Exception as e:
        print(f"❌ PDF处理器测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始快速测试\n")

    tests = [
        ("导入测试", test_imports),
        ("HTML渲染器测试", test_html_renderer),
        ("PDF处理器测试", test_pdf_processor),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"正在运行: {test_name}")
        success = test_func()
        results.append((test_name, success))
        print()

    # 输出总结
    print("="*40)
    print("📊 快速测试结果")
    print("="*40)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} {test_name}")

    print(f"\n总体结果: {passed}/{total} 项测试通过")

    if passed == total:
        print("🎉 所有快速测试通过！核心功能正常。")
    else:
        print("⚠️  部分测试失败，请检查上述错误。")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
验证生成的PDF文件的质量和内容
"""

import os
import fitz
from PIL import Image
import io


def verify_pdf_file(filepath: str, description: str):
    """验证PDF文件的基本属性"""
    print(f"\n=== 验证 {description} ===\n")

    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        return False

    try:
        # 打开PDF
        doc = fitz.open(filepath)
        print(f"文件路径: {filepath}")
        print(f"文件大小: {os.path.getsize(filepath)} bytes")
        print(f"页数: {len(doc)}")

        if len(doc) == 0:
            print("❌ PDF文件没有页面")
            doc.close()
            return False

        # 检查第一页
        page = doc[0]
        width, height = page.rect.width, page.rect.height
        print(f"页面尺寸: {width:.1f} x {height:.1f} 点 ({width/72:.2f} x {height/72:.2f} 英寸)")

        # 提取文本内容
        text = page.get_text()
        text_length = len(text.strip())
        print(f"文本长度: {text_length} 字符")

        if text_length > 0:
            print("文本预览 (前200字符):")
            print(repr(text[:200] + "..." if len(text) > 200 else text))
        else:
            print("⚠️  页面不包含可提取的文本")

        # 检查是否有图像
        image_list = page.get_images(full=True)
        print(f"页面中的图像数量: {len(image_list)}")

        doc.close()
        print("✅ PDF文件验证通过")
        return True

    except Exception as e:
        print(f"❌ PDF验证失败: {e}")
        return False


def compare_pdf_sizes():
    """比较生成的PDF文件大小"""
    print("\n=== PDF文件大小比较 ===\n")

    files_to_check = [
        ("test_fragment_simple.pdf", "简单HTML片段"),
        ("test_fragment_complex.pdf", "复杂HTML片段"),
        ("test_composition_result.pdf", "合成PDF结果"),
    ]

    sizes = {}
    for filename, desc in files_to_check:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            sizes[filename] = size
            print(f"{desc}: {size} bytes ({size/1024:.1f} KB)")
        else:
            print(f"{desc}: 文件不存在")

    # 检查大小合理性
    if "test_fragment_simple.pdf" in sizes and "test_fragment_complex.pdf" in sizes:
        simple_size = sizes["test_fragment_simple.pdf"]
        complex_size = sizes["test_fragment_complex.pdf"]
        if complex_size > simple_size:
            print("✅ 复杂片段PDF大于简单片段PDF (合理)")
        else:
            print("⚠️  复杂片段PDF不大于简单片段PDF")

    if "test_composition_result.pdf" in sizes:
        comp_size = sizes["test_composition_result.pdf"]
        print(f"合成PDF与片段PDF的比例: {comp_size/max(sizes.values()):.2f}")


def test_pdf_rendering_quality():
    """测试PDF渲染质量"""
    print("\n=== 测试PDF渲染质量 ===\n")

    try:
        # 检查复杂HTML片段是否包含预期的元素
        if os.path.exists("test_fragment_complex.pdf"):
            doc = fitz.open("test_fragment_complex.pdf")
            page = doc[0]
            text = page.get_text().lower()

            # 检查是否包含预期的内容
            expected_elements = ["代码示例", "def hello_world", "数学公式", "列表", "项目1"]
            found_elements = []

            for element in expected_elements:
                if element.lower() in text:
                    found_elements.append(element)

            print(f"找到的预期元素 ({len(found_elements)}/{len(expected_elements)}):")
            for element in found_elements:
                print(f"  ✅ {element}")

            if len(found_elements) < len(expected_elements):
                missing = [e for e in expected_elements if e not in found_elements]
                print(f"缺失的元素: {missing}")

            doc.close()

        # 检查合成PDF的布局
        if os.path.exists("test_composition_result.pdf"):
            doc = fitz.open("test_composition_result.pdf")
            page = doc[0]

            # 检查页面是否有两个主要区域（左侧原内容 + 右侧讲解）
            text = page.get_text()
            left_content = "源pdf内容" in text.lower()
            right_content = "页面讲解" in text.lower()

            print("合成PDF内容检查:")
            print(f"  左侧原内容: {'✅' if left_content else '❌'}")
            print(f"  右侧讲解内容: {'✅' if right_content else '❌'}")

            if left_content and right_content:
                print("✅ 合成PDF包含左右两栏内容")
            else:
                print("⚠️  合成PDF内容不完整")

            doc.close()

    except Exception as e:
        print(f"❌ 渲染质量测试失败: {e}")


def main():
    """主验证函数"""
    print("🔍 开始PDF质量验证\n")

    # 要验证的文件
    test_files = [
        ("test_fragment_simple.pdf", "简单HTML片段PDF"),
        ("test_fragment_complex.pdf", "复杂HTML片段PDF"),
        ("test_composition_result.pdf", "PDF合成结果"),
    ]

    results = []
    for filepath, description in test_files:
        success = verify_pdf_file(filepath, description)
        results.append((description, success))

    # 比较文件大小
    compare_pdf_sizes()

    # 测试渲染质量
    test_pdf_rendering_quality()

    # 输出总结
    print("\n" + "="*50)
    print("📊 PDF质量验证总结")
    print("="*50)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for desc, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} {desc}")

    print(f"\n验证结果: {passed}/{total} 项通过")

    if passed == total:
        print("🎉 所有PDF质量验证通过！")
        print("\n📁 生成的文件:")
        print("  - test_fragment_simple.pdf: 简单HTML转换结果")
        print("  - test_fragment_complex.pdf: 复杂HTML转换结果（含代码和公式）")
        print("  - test_composition_result.pdf: 完整PDF合成结果")
    else:
        print("⚠️  部分验证失败，请检查上述问题。")

    return passed == total


if __name__ == "__main__":
    success = main()
    print(f"\n验证{'成功' if success else '失败'}")

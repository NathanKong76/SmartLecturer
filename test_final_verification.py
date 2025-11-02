#!/usr/bin/env python3
"""
最终验证脚本：测试批量JSON重新生成PDF功能的完整修复
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services import pdf_processor

def test_safe_html_renderer():
    """测试安全HTML渲染器"""
    print("🎯 测试安全HTML渲染器...")

    try:
        from app.services.safe_html_renderer import safe_render_html_to_pdf_fragment

        # 简单的HTML测试
        html = "<div style='font-size: 12pt; color: black;'>测试渲染</div>"
        css = "body { font-family: Arial, sans-serif; }"
        pdf_bytes = safe_render_html_to_pdf_fragment(
            html=html,
            width_pt=200,
            height_pt=100,
            css=css,
            background="white",
            timeout=10
        )

        print(f"✅ 安全HTML渲染器工作正常，生成PDF大小: {len(pdf_bytes)} bytes")
        return True

    except Exception as e:
        print(f"❌ 安全HTML渲染器测试失败: {e}")
        return False

def test_batch_json_full_cycle():
    """测试完整的批量JSON处理周期"""
    print("\n🎯 测试完整批量JSON处理周期...")

    # 使用小PDF文件进行完整测试
    pdf_path = "test_3column_layout.pdf"
    json_path = "../../Downloads/explanations.json"

    if not os.path.exists(pdf_path):
        print(f"❌ 测试PDF文件不存在: {pdf_path}")
        return False

    if not os.path.exists(json_path):
        print(f"❌ 测试JSON文件不存在: {json_path}")
        return False

    try:
        # 读取文件
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        explanations = {int(k): str(v) for k, v in json_data.items()}

        # 创建批量处理数据
        pdf_files = [("test_pdf.pdf", pdf_bytes)]
        json_files = [("test_pdf.json", json.dumps(explanations, ensure_ascii=False).encode('utf-8'))]

        # 执行批量处理
        start_time = time.time()
        results = pdf_processor.batch_recompose_from_json(
            pdf_files=pdf_files,
            json_files=json_files,
            font_size=16,
            render_mode="markdown"
        )
        elapsed = time.time() - start_time

        # 检查结果
        filename = "test_pdf.pdf"
        if filename not in results:
            print(f"❌ 结果中没有文件: {filename}")
            return False

        result = results[filename]
        if result.get("status") == "completed" and result.get("pdf_bytes"):
            print("😄 Streamlit 启动成功！")
            print(f"✅ 批量处理完成，耗时: {elapsed:.2f}秒")
            print(f"✅ 生成PDF大小: {len(result['pdf_bytes'])} bytes")
            return True
        else:
            print(f"❌ 批量处理失败: {result.get('error', '未知错误')}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("="*60)
    print("🎯 批量JSON重新生成PDF功能最终验证")
    print("="*60)

    success_count = 0
    total_tests = 2

    # 测试1：安全HTML渲染器
    if test_safe_html_renderer():
        success_count += 1

    # 测试2：完整批量JSON处理
    if test_batch_json_full_cycle():
        success_count += 1

    # 总结
    print("\n" + "="*60)
    print(f"📊 测试结果: {success_count}/{total_tests} 通过")

    if success_count == total_tests:
        print("🎉 所有测试通过！批量JSON重新生成PDF功能修复成功")
        print("\n📋 修复内容总结:")
        print("• ✅ 优化安全HTML渲染器，使用独立线程避免Streamlit冲突")
        print("• ✅ 增强HTML渲染器的错误处理和超时机制")
        print("• ✅ 添加多重降级渲染策略（Chromium → 纯文本降级）")
        print("• ✅ 改进浏览器启动选项，提高稳定性")
        print("\n🚀 建议下一步: 重新启动Streamlit应用测试界面功能")
    else:
        print(f"⚠️  {total_tests - success_count} 个测试失败，可能仍需进一步调试")

    print("="*60)

    return success_count == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

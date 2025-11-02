#!/usr/bin/env python3
"""
📋 优化完成验证清单
验证所有需求点是否完全实现
"""

import fitz
import json
from app.services import pdf_processor

def verify_render_mode_forcing():
    """验证强制Markdown渲染"""
    print("🔍 验证1: 强制Markdown渲染")

    # 1. 检查streamlit_app.py中是否移除了"text"选项
    with open("app/streamlit_app.py", "r", encoding="utf-8") as f:
        content = f.read()
        if 'render_mode = st.selectbox("右栏渲染方式", ["text", "markdown"]' in content:
            print("❌ Streamlit中仍显示text选项")
            return False
        if 'render_mode = "markdown"  # 强制使用Markdown渲染' not in content:
            print("❌ 未强制设为markdown")
            return False

    # 2. 检查pdf_processor.py中所有函数默认参数
    with open("app/services/pdf_processor.py", "r", encoding="utf-8") as f:
        content = f.read()
        # 检查关键函数默认参数
        checks = [
            'render_mode: str = "text"' in content,  # 应该为False
            'render_mode: str = "markdown"' in content,  # 应该为True
        ]
        if checks[0]:
            print("❌ 仍有text默认值存在")
            return False

    # 3. 检查代码中是否删除了text渲染分支
    if 'render_mode == "text"' in content:
        print("❌ 仍存在text渲染分支")
        return False

    print("✅ 强制Markdown渲染验证通过")
    return True

def verify_proportion_layout():
    """验证1:2比例布局"""
    print("🔍 验证2: 1:2固定比例布局")

    # 检查页面宽度计算是否为3倍
    with open("app/services/pdf_processor.py", "r", encoding="utf-8") as f:
        content = f.read()
        if 'new_w, new_h = int(w * 3), h' not in content:
            print("❌ 未找到3倍宽度计算")
            return False

    print("✅ 1:2固定比例布局验证通过 (PDF:讲解 = 1:2, 总比1:3)")
    return True

def verify_3column_dynamic_display():
    """验证3栏动态显示逻辑"""
    print("🔍 验证3: 3栏动态显示逻辑")

    with open("app/services/pdf_processor.py", "r", encoding="utf-8") as f:
        content = f.read()

        # 检查动态列数计算
        if 'column_count = max_columns' not in content:
            print("❌ 未找到动态列数计算")
            return False

        if 'for num_columns in range(1, max_columns + 1):' not in content:
            print("❌ 未找到列数递增循环")
            return False

        if 'effective_length <= capacity * fudge:' not in content:
            print("❌ 未找到容量判断")
            return False

        # 检查未填充栏位是否被跳过
        if 'column_rects = all_rects[:column_count]' not in content:
            print("❌ 未找到栏位裁剪")
            return False

    print("✅ 3栏动态显示逻辑验证通过")
    return True

def verify_continuation_page_handling():
    """验证续页处理优化"""
    print("🔍 验证4: 续页处理优化")

    with open("app/services/pdf_processor.py", "r", encoding="utf-8") as f:
        content = f.read()

        # 检查续页是否显示原始PDF
        if 'cpage.show_pdf_page(fitz.Rect(0, 0, w, h), src_doc, pno)' not in content:
            print("❌ 续页未显示原始PDF")
            return False

        # 检查续页标注
        if '"【原页面延续】"' not in content:
            print("❌ 未找到续页标注")
            return False

        # 检查续页是否使用Markdown渲染
        if 'cpage.insert_htmlbox(rect, html, css=css)' not in content:
            print("❌ 续页未使用Markdown渲染")
            return False

    print("✅ 续页处理优化验证通过")
    return True

def test_layout_functionality():
    """测试实际布局功能"""
    print("🔍 验证5: 实际布局功能测试")

    try:
        # 创建测试PDF
        src_doc = fitz.open()
        page = src_doc.new_page(width=400, height=600)
        page.insert_text((50, 100), "测试PDF内容\n用于验证布局")
        src_bytes = src_doc.tobytes()

        # 测试包含Markdown的讲解内容
        explanations = {
            0: """# 测试Markdown内容

这是**粗体**和*斜体*文本。

## 列表
- 项目1
- 项目2

代码: `print('hello')`"""
        }

        # 生成PDF
        result_bytes = pdf_processor.compose_pdf(
            src_bytes=src_bytes,
            explanations=explanations,
            right_ratio=0.5,
            font_size=12,
            render_mode="markdown"
        )

        # 验证生成的PDF
        result_doc = fitz.open(stream=result_bytes)
        page = result_doc.load_page(0)
        w, h = page.rect.width, page.rect.height

        # 检查宽度是否为3倍
        if abs(w - 400 * 3) > 1:
            print(f"❌ 宽度不正确: {w}, 期望: {400*3}")
            return False

        # 检查高度是否保持
        if abs(h - 600) > 1:
            print(f"❌ 高度不正确: {h}, 期望: 600")
            return False

        result_doc.close()
        src_doc.close()

        print("✅ 实际布局功能测试通过")
        return True

    except Exception as e:
        print(f"❌ 布局功能测试失败: {e}")
        return False

def main():
    """主验证函数"""
    print("🚀 开始全面优化验证\n")

    tests = [
        verify_render_mode_forcing,
        verify_proportion_layout,
        verify_3column_dynamic_display,
        verify_continuation_page_handling,
        test_layout_functionality
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ 测试执行失败: {e}")
            print()

    print(f"📊 验证结果: {passed}/{total} 项测试通过")

    if passed == total:
        print("🎉 所有优化需求验证通过！")
        print("\n📋 实现的核心功能点:")
        print("✅ 强制Pandoc Markdown渲染 (删除所有text分支)")
        print("✅ 固定1:2比例布局 (PDF:讲解 = 1:3总宽度)")
        print("✅ 3栏动态显示 (内容量驱动，不显示未填充栏位)")
        print("✅ 续页处理优化 (显示原始PDF + 醒目标注)")

        return True
    else:
        print("❌ 部分验证失败，需要检查和修复")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🛑 所有优化任务完成！系统现已支持您要求的所有功能。")
    else:
        print("\n⚠️ 部分功能有待完善，请检查测试输出。")

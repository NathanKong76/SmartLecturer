#!/usr/bin/env python3
"""
修复Streamlit中Playwright卡住问题的解决方案
"""
import os
import asyncio
import sys

def fix_streamlit_playwright_issue():
    """
    为Streamlit应用中的Playwright提供修复方案
    """
    print("🔧 开始修复Streamlit Playwright卡住问题...")

    # 方法1: 修改html_renderer.py中的事件循环处理
    html_renderer_path = "app/services/html_renderer.py"

    try:
        with open(html_renderer_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已经包含修复
        if "streamlit" in content.lower() and "asyncio" in content:
            print("✅ html_renderer.py已经包含Streamlit兼容性修复")
        else:
            print("📝 需要为html_renderer.py添加Streamlit事件循环修复")

            # 在render_html_to_pdf_fragment函数开头添加
            hook_code = '''
        # Streamlit兼容性修复：处理Windows事件循环问题
        import streamlit as st
        if hasattr(st, 'runtime') and hasattr(st.runtime, 'exists') and st.runtime.exists():
            # 在Streamlit环境中，强制使用Selector事件循环
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                # 没有正在运行的事件循环，设置为Selector
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        '''

            # 找到函数开始位置
            func_start = content.find("def render_html_to_pdf_fragment(")
            if func_start != -1:
                # 找到函数体开始
                body_start = content.find('\n', func_start)
                if body_start != -1:
                    # 插入修复代码
                    new_content = content[:body_start+1] + hook_code + content[body_start+1:]

                    with open(html_renderer_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                    print("✅ 已为html_renderer.py添加Streamlit事件循环修复")
                else:
                    print("❌ 无法找到函数体位置")

    except Exception as e:
        print(f"❌ 修改html_renderer.py失败: {e}")

    # 方法2: 创建安全的渲染函数包装器
    try:
        wrapper_code = '''import asyncio
import sys
from typing import Optional

def safe_render_html_to_pdf_fragment(html: str, width_pt: float, height_pt: float,
                                   css: Optional[str] = None, background: str = "white",
                                   mathjax: bool = True, prism: bool = True):
    """
    在Streamlit环境中安全渲染HTML到PDF的包装器函数
    """
    try:
        # 检测是否在Streamlit环境中
        streamlit_env = False
        try:
            import streamlit as st
            streamlit_env = hasattr(st, 'runtime') and st.runtime.exists()
        except ImportError:
            pass

        if streamlit_env:
            # Streamlit环境下的特殊处理
            if sys.platform.startswith("win"):
                # Windows上设置合适的异步策略
                try:
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                except Exception:
                    pass

        # 导入并调用原始渲染函数
        from .html_renderer import HtmlRenderer
        return HtmlRenderer.render_html_to_pdf_fragment(
            html=html,
            width_pt=width_pt,
            height_pt=height_pt,
            css=css,
            background=background,
            mathjax=mathjax,
            prism=prism
        )

    except Exception as e:
        raise RuntimeError(f"HTML渲染失败，可能是在Streamlit异步环境中: {e}")

# 为了向后兼容，保留原始函数并添加安全包装器
'''

        with open("app/services/safe_html_renderer.py", 'w', encoding='utf-8') as f:
            f.write(wrapper_code)

        print("✅ 已创建安全的HTML渲染包装器文件")

    except Exception as e:
        print(f"❌ 创建包装器失败: {e}")

    # 方法3: 修改streamlit_app.py中的批量处理函数
    try:
        streamlit_app_path = "app/streamlit_app.py"

        with open(streamlit_app_path, 'r', encoding='utf-8') as f:
            app_content = f.read()

        # 查找_build_and_run_with_pairs函数
        func_pattern = "def _build_and_run_with_pairs(pairs):"
        func_start = app_content.find(func_pattern)

        if func_start != -1:
            # 在函数开始处添加安全处理
            lines = app_content.split('\n')
            func_line_idx = None
            for i, line in enumerate(lines):
                if func_pattern in line:
                    func_line_idx = i
                    break

            if func_line_idx is not None:
                # 在函数开始后添加安全检查
                safe_code = [
                    "    from app.services.safe_html_renderer import safe_render_html_to_pdf_fragment",
                    "    # 在Streamlit中临时替换渲染函数"
                    "    import app.services.html_renderer",
                    "    original_render = app.services.html_renderer.HtmlRenderer.render_html_to_pdf_fragment",
                    "    app.services.html_renderer.HtmlRenderer.render_html_to_pdf_fragment = safe_render_html_to_pdf_fragment",
                    "    try:"
                ]

                # 找到函数体的缩进并在函数体最后添加finally
                indent_level = len(lines[func_line_idx + 1]) - len(lines[func_line_idx + 1].lstrip())

                # 插入安全代码
                safe_code.insert(1, "    " * (indent_level // 4))  # 调整缩进

                # 重新组合内容
                new_lines = []
                inserted_safety = False

                for i, line in enumerate(lines):
                    new_lines.append(line)

                    if i == func_line_idx + 1:  # 函数体第一行
                        for safe_line in safe_code[:-1]:  # 除了最后一个"try:"
                            new_lines.append("    " * (indent_level // 4) + safe_line)
                        new_lines.append("    " * (indent_level // 4) + safe_code[-1])  # 添加"try:"
                        inserted_safety = True

                if inserted_safety:
                    # 在函数结束前添加finally块
                    # 这里需要找到return语句或函数结束
                    for i in range(len(new_lines) - 1, -1, -1):
                        if "return " in new_lines[i] or "st.session_state" in new_lines[i]:
                            # 在此处之前添加finally
                            indent = len(new_lines[i]) - len(new_lines[i].lstrip())
                            finally_code = [
                                "    " * (indent // 4) + "    finally:",
                                "    " * (indent // 4) + "        # 恢复原始渲染函数",
                                "    " * (indent // 4) + "        app.services.html_renderer.HtmlRenderer.render_html_to_pdf_fragment = original_render"
                            ]
                            for finally_line in finally_code:
                                new_lines.insert(i, finally_line)
                            break

                    # 写回文件
                    with open(streamlit_app_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(new_lines))

                    print("✅ 已修改streamlit_app.py添加Playwright安全处理")

    except Exception as e:
        print(f"❌ 修改streamlit_app.py失败: {e}")

    print("\n🎯 修复建议：")
    print("1. 重启Streamlit应用: `streamlit run app/streamlit_app.py`")
    print("2. 再次测试批量JSON处理功能")
    print("3. 如果仍有问题，请尝试在非Streamlit环境中单独测试")

def alternative_solution():
    """
    替代方案：使用同步PDF处理避免异步问题
    """
    print("\n🔄 替代方案：创建同步PDF处理版本")

    alt_code = '''import asyncio
import sys

def sync_batch_recompose_from_json(pdf_files, json_files, font_size, **kwargs):
    """
    同步版本的批量PDF重新合成，避免Streamlit异步问题
    """
    try:
        # 强制同步执行模式
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        # 创建新的事件循环用于同步执行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            from app.services import pdf_processor
            return loop.run_until_complete(
                pdf_processor.batch_recompose_from_json_async(pdf_files, json_files, font_size, **kwargs)
            )
        finally:
            loop.close()

    except Exception as e:
        # 如果同步执行失败，回退到其他方法
        print(f"同步执行失败: {e}，尝试其他方法...")
        raise
'''

    try:
        with open("app/services/sync_pdf_processor.py", 'w', encoding='utf-8') as f:
            f.write(alt_code)
        print("✅ 已创建同步PDF处理替代方案")
    except Exception as e:
        print(f"❌ 创建替代方案失败: {e}")

if __name__ == "__main__":
    print("="*60)
    print("🔧 Streamlit Playwright卡住问题修复工具")
    print("="*60)

    fix_streamlit_playwright_issue()
    alternative_solution()

    print("\n" + "="*60)
    print("✅ 修复工具执行完成，请重启Streamlit应用测试")
    print("="*60)

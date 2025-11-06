#!/usr/bin/env python3
"""
Pandoc Markdown 渲染服务
使用真正的 Pandoc 命令行工具进行 Markdown 到 HTML 的转换
"""

import subprocess
import tempfile
import os
import re
from typing import Optional, Tuple
from .logger import get_logger
logger = get_logger()


class PandocRenderer:
    """Pandoc Markdown 渲染器"""
    _pandoc_exe: str = 'pandoc'  # 默认使用系统 PATH 中的 pandoc

    @staticmethod
    def check_pandoc_available() -> Tuple[bool, str]:
        """
        检测 Pandoc 是否可用
        Returns: (是否可用, 版本信息或错误信息)
        """
        logger.info('Checking Pandoc availability')
        # 先检查 PATH 中的 pandoc
        try:
            result = subprocess.run(
                ['pandoc', '--version'],
                capture_output=True,
                text=True,
                timeout=5,
                # 避免命令行输出干扰
                shell=False
            )
            if result.returncode == 0:
                # 提取版本号
                version_line = result.stdout.split('\n')[0]
                logger.info('Pandoc in PATH available: %s', version_line)
                return True, version_line
            else:
                logger.warning('Pandoc PATH error: code=%d', result.returncode)
        except (FileNotFoundError, OSError) as e:
            logger.warning('Pandoc not in PATH: %s', e)

        # 检查项目目录中的 pandoc
        import os
        pandoc_path = os.path.join(os.path.dirname(__file__), '..', '..', 'pandoc-3.8.2.1', 'pandoc.exe')

        if os.path.exists(pandoc_path):
            try:
                result = subprocess.run(
                    [pandoc_path, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    # 避免命令行输出干扰
                    shell=False
                )
                if result.returncode == 0:
                    # 提取版本号
                    version_line = result.stdout.split('\n')[0]
                    # 保存 pandoc 路径
                    PandocRenderer._pandoc_exe = pandoc_path
                    logger.info('Project Pandoc available: %s', version_line)
                    return True, version_line
                else:
                    logger.warning('Project Pandoc error: %d', result.returncode)
                    return False, f"项目 Pandoc 返回错误码: {result.returncode}"
            except Exception as e:
                logger.error('Project Pandoc run failed: %s', e, exc_info=True)
                return False, f"项目 Pandoc 运行异常: {str(e)}"
        logger.error('Pandoc not found')
        return False, "Pandoc 未找到，请先安装 Pandoc"

    @staticmethod
    def render_markdown_to_html(markdown_content: str) -> Tuple[str, bool]:
        """
        使用 Pandoc 将 Markdown 转换为 HTML

        Args:
            markdown_content: Markdown 字符串

        Returns:
            (HTML 字符串, 是否成功)
        """
        logger.info('Rendering markdown to html with Pandoc, content length=%d', len(markdown_content or ''))
        if not markdown_content.strip():
            logger.debug('Input markdown is empty')
            return "", True

        # 确保 Pandoc 路径已设置
        if PandocRenderer._pandoc_exe == 'pandoc':
            PandocRenderer.check_pandoc_available()

        try:
            # 处理 LaTeX 公式保护
            processed_md = PandocRenderer._protect_latex_formulas(markdown_content)

            # 使用 pandoc 转换
            pandoc_cmd = PandocRenderer._pandoc_exe
            process = subprocess.run(
                [
                    pandoc_cmd,
                    # 输入格式
                    '--from=markdown+tex_math_single_backslash',
                    # 输出格式
                    '--to=html5',
                    # 扩展功能
                    '--mathjax',
                    '--highlight-style=tango',
                    '--table-of-contents'  # 如果需要
                ],
                input=processed_md,
                capture_output=True,
                text=True,
                encoding='utf-8',  # 明确指定 UTF-8 编码
                timeout=10,
                # 避免命令行输出干扰
                shell=False
            )

            if process.returncode == 0:
                html = process.stdout.strip()
                logger.info('Pandoc render success, html length=%d', len(html))
                return html, True
            else:
                logger.error('Pandoc render failed: %s', process.stderr)
                return PandocRenderer._fallback_to_python_markdown(markdown_content), False

        except subprocess.TimeoutExpired:
            logger.error('Pandoc render timeout')
            return PandocRenderer._fallback_to_python_markdown(markdown_content), False
        except Exception as e:
            logger.error('Pandoc render exception: %s', e, exc_info=True)
            return PandocRenderer._fallback_to_python_markdown(markdown_content), False

    @staticmethod
    def _protect_latex_formulas(markdown_content: str) -> str:
        """
        保护 LaTeX 公式避免 pandoc 处理
        Pandoc 会自动处理 $$...$$ 格式，不需要额外处理
        """
        # 对于复杂的公式，保证格式正确
        return markdown_content

    @staticmethod
    def _fallback_to_python_markdown(markdown_content: str) -> str:
        """
        Fallback 到 Python Markdown 库
        """
        logger.info('Fallback to python-markdown, content length=%d', len(markdown_content or ''))
        try:
            from markdown import markdown
            html = markdown(markdown_content)
            logger.info('python-markdown render success, html length=%d', len(html))
            return html
        except Exception as e:
            logger.error('python-markdown render failed: %s', e, exc_info=True)
            return markdown_content.replace('\n', '<br>')


def test_pandoc_functionality():
    """测试 Pandoc 功能"""
    print("=== Pandoc 功能测试 ===\n")

    # 1. 检查 Pandoc 可用性
    available, info = PandocRenderer.check_pandoc_available()
    print(f"Pandoc 可用性: {'✅' if available else '❌'} {info}")

    if not available:
        print("⚠️ Pandoc 未可用，使用 Fallback 模式")
        return

    # 2. 测试 Markdown 转换
    test_md = """
# 测试标题

这是**粗体**和*斜体*文本。

## 数学公式
使用 LaTeX：$E = mc^2$ 和
$$\\int_0^1 x^2 dx = \\frac{1}{3}$$

## 代码块
```python
def hello():
    print("Hello, Pandoc!")
    return True
```

## 表格

| 功能 | 状态 |
|------|------|
| Markdown | ✅ |
| 数学公式 | ✅ |
| 表格 | ✅ |
"""

    print("正在测试 Pandoc 渲染...")
    html_output, success = PandocRenderer.render_markdown_to_html(test_md)

    if success and html_output:
        print("✅ Pandoc 渲染成功!")
        print(f"HTML 输出长度: {len(html_output)} 字符")
        # print(f"示例输出:\n{html_output[:200]}...")
    else:
        print("❌ Pandoc 渲染失败")


if __name__ == "__main__":
    test_pandoc_functionality()

from __future__ import annotations

import math
import sys
import asyncio
from typing import Optional

from app.services.logger import get_logger
logger = get_logger()


class HtmlRendererError(Exception):
	pass


class HtmlRenderer:
	@staticmethod
	def _pt_to_inches(pt: float) -> float:
		return pt / 72.0

	@staticmethod
	def _pt_to_px(pt: float) -> int:
		# 1pt = 1/72 inch；常规屏幕 96 DPI -> 1pt = 96/72 px ≈ 1.3333px
		return int(math.ceil(pt * (96.0 / 72.0)))

	@staticmethod
	def render_html_to_pdf_fragment(
		html: str,
		width_pt: float,
		height_pt: float,
		css: Optional[str] = None,
		background: str = "white",
		mathjax: bool = True,
		prism: bool = True,
	) -> bytes:
		logger.info('Render html to pdf fragment, html length=%d, width_pt=%.1f, height_pt=%.1f', len(html or ''), width_pt, height_pt)
		# Windows 下确保使用支持 subprocess 的事件循环
		if sys.platform.startswith("win"):
			try:
				asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
			except Exception:
				pass
		try:
			from playwright.sync_api import sync_playwright
		except Exception as e:
			logger.error('Playwright import failed: %s', e, exc_info=True)
			raise HtmlRendererError(
				f"Playwright 不可用，请先安装依赖并安装 Chromium。原始错误: {e}"
			)

		page_width_in = HtmlRenderer._pt_to_inches(width_pt)
		page_height_in = HtmlRenderer._pt_to_inches(height_pt)
		vp_w = max(1, HtmlRenderer._pt_to_px(width_pt))
		vp_h = max(1, HtmlRenderer._pt_to_px(height_pt))

		# 基础 HTML 模板，注入 CSS / Prism / MathJax
		css_block = f"<style>{css or ''}</style>"
		prism_css = (
			"<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism.min.css\" />"
			if prism else ""
		)
		prism_js = (
			"<script src=\"https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js\"></script>"
			"<script src=\"https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-python.min.js\"></script>"
			"<script src=\"https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-javascript.min.js\"></script>"
			if prism else ""
		)
		mathjax_js = (
			"<script>window.MathJax = { tex: { inlineMath: [['$','$'], ['\\\\(','\\\\)']] }, svg: { fontCache: 'global' } };</script>"
			"<script src=\"https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js\"></script>"
			if mathjax else ""
		)

		# 页面基础样式，尽量与 pdf_processor 的 markdown 模式一致
		base_css = f"""
			/* reset & base */
			html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; }}
			body {{ background: {background}; color: #000; overflow-wrap: break-word; word-break: break-word; }}
			body {{ font-size: 12pt; line-height: 1.4; font-family: 'SimHei','Noto Sans SC','Microsoft YaHei',sans-serif; }}
			pre, code {{ font-family: 'Consolas','Fira Code',monospace; font-size: 11pt; color: #000; }}
			table {{ border-collapse: collapse; width: 100%; }}
			th, td {{ border: 1px solid #ccc; padding: 2pt 4pt; color: #000; }}
			p {{ margin: 0 0 2pt 0; }}
			ul, ol {{ margin: 0 0 2pt 1.2em; }}
		"""

		html_doc = f"""
			<!doctype html>
			<html>
			<head>
			<meta charset=\"utf-8\" />
			<meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\" />
			<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
			<style>{base_css}</style>
			{prism_css}
			{css_block}
			</head>
			<body>
			<div id=\"container\" style=\"box-sizing:border-box; width:100%; height:100%; padding:0;\">{html}</div>
			{prism_js}
			{mathjax_js}
			<script>
				(async () => {{
					try {{
						if (window.Prism) {{ window.Prism.highlightAll(); }}
						if (window.MathJax && window.MathJax.typesetPromise) {{ await window.MathJax.typesetPromise(); }}
						window.__ready__ = true;
					}} catch (e) {{ window.__ready__ = true; }}
				}})();
			</script>
			</body>
			</html>
		"""

		try:
			with sync_playwright() as p:
				# 设置启动选项，增加稳定性
				browser = p.chromium.launch(
					headless=True,
					args=[
						'--no-sandbox',
						'--disable-setuid-sandbox',
						'--disable-dev-shm-usage',
						'--disable-gpu',
						'--no-first-run',
						'--disable-features=VizDisplayCompositor'
					]
				)
				context = browser.new_context(viewport={"width": vp_w, "height": vp_h})
				page = context.new_page()

				# 设置页面加载超时
				page.set_default_timeout(15000)
				page.set_default_navigation_timeout(15000)

				page.set_content(html_doc, wait_until="load")
				logger.debug('HTML content length: %d', len(html) if html else 0)

				# 等待渲染完成（Prism/MathJax），增加重试机制
				try:
					page.wait_for_function("() => window.__ready__ === true", timeout=15000)
				except Exception:
					# 如果等待失败，可能MathJax或Prism有问题，继续处理
					print("Warning: 等待渲染完成超时，可能影响公式或代码高亮显示")

				# 导出 PDF（按英寸设置尺寸），增加超时
				pdf_bytes = page.pdf(
					width=f"{page_width_in}in",
					height=f"{page_height_in}in",
					print_background=True,
					margin={"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"},
				)
				logger.info('PDF fragment rendered, bytes length=%d', len(pdf_bytes))
				logger.debug('Chromium page rendering success, result size %d bytes', len(pdf_bytes) if pdf_bytes else 0)

				context.close()
				browser.close()
				return pdf_bytes

		except NotImplementedError as e:
			logger.error('Chromium 启动失败: %s', e, exc_info=True)
			# 常见于 Windows 事件循环或子进程策略问题
			detailed_error = "Chromium 启动失败：Windows 子进程事件循环不兼容。"
			suggestions = "请尝试: 1) 重启Streamlit应用, 2) 在虚拟环境中运行 `python -m playwright install chromium`"
			if "streamlit" in detailed_error.lower():
				suggestions += ", 3) 检查是否在Streamlit版本冲突"
			elif "asyncio" in str(e).lower():
				suggestions += ", 3) 这是异步事件循环问题，已应用修复但仍可能失败"
			else:
				suggestions += ", 3) 检查系统是否有足够的权限启动浏览器"
			raise HtmlRendererError(f"{detailed_error} 建议: {suggestions}")

		except Exception as e:
			logger.error('Chromium rendering failed: %s', e, exc_info=True)
			error_msg = f"Chromium 渲染失败: {str(e)}"
			if "timeout" in str(e).lower():
				error_msg += " (渲染超时，可能内容过复杂)"
			elif "connection" in str(e).lower():
				error_msg += " (浏览器连接问题，可能需要重新安装Chromium)"
			# 在Streamlit环境中，不要立即崩溃，提供降级方案
			try:
				import streamlit as st
				if hasattr(st, 'runtime') and st.runtime.exists():
					error_msg += " (已在Streamlit环境中)"
			except ImportError:
				pass
			raise HtmlRendererError(error_msg)

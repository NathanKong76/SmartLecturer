import os
import io
import time
import json
import zipfile
import hashlib
import tempfile
from typing import Optional, Dict, Any, List

import streamlit as st
from dotenv import load_dotenv

from app.ui_helpers import (
    StateManager, display_batch_status, validate_file_upload,
    process_single_file, display_file_result,
    build_zip_cache_pdf, build_zip_cache_markdown
)

load_dotenv()


# 确保可以以包形式导入 `app.*`（将项目根目录加入 sys.path）
import sys
import os as _os
try:
    _CURRENT_DIR = _os.path.abspath(_os.path.dirname(__file__))
    _PROJECT_ROOT = _os.path.dirname(_CURRENT_DIR)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
except Exception:
    pass


# Cache processing functions moved to app/cache_processor.py to avoid circular imports
from app.cache_processor import (
	cached_process_pdf,
	cached_process_markdown,
	get_file_hash,
	save_result_to_file,
	load_result_from_file,
	TEMP_DIR  # Also export TEMP_DIR for backward compatibility
)


def setup_page():
	st.set_page_config(page_title="PDF 讲解流 · Gemini 2.5 Pro", layout="wide")
	st.title("PDF 讲解流 · Gemini 2.5 Pro")
	st.caption("逐页生成讲解，右侧留白排版，保持原PDF向量内容")


def sidebar_form():
	with st.sidebar:
		st.header("⚙️ 参数配置")
		
		# ============================================
		# 1. 输出模式选择 - 放在最顶部
		# ============================================
		st.subheader("📤 输出模式")
		output_mode = st.radio(
			"选择输出格式",
			["PDF讲解版", "Markdown截图讲解", "HTML截图版", "HTML-pdf2htmlEX版"],
			index=3,
			help="PDF讲解版：在PDF右侧添加讲解文字\nMarkdown截图讲解：生成包含页面截图和讲解的markdown文档\nHTML截图版：生成单个HTML文件，左侧显示PDF截图，右侧显示多栏markdown渲染讲解\nHTML-pdf2htmlEX版：使用pdf2htmlEX转换PDF为高质量HTML，布局与HTML截图版一致"
		)
		

		

		st.divider()
		
		# ============================================
		# 2. 模式特定参数
		# ============================================
		if output_mode == "Markdown截图讲解":
			st.subheader("📝 Markdown 参数")
			screenshot_dpi = st.slider("截图DPI", 72, 300, 150, 12, help="截图质量，较高DPI生成更清晰的图片，但文件更大")
			embed_images = st.checkbox("嵌入图片到Markdown", value=False, help="将截图base64编码嵌入markdown文件，否则使用外部图片文件")
			markdown_title = st.text_input("文档标题", value="PDF文档讲解")
			# 默认值用于非Markdown模式
			html_column_count = 2
			html_column_gap = 20
			html_show_column_rule = True
			st.divider()
		elif output_mode == "HTML截图版" or output_mode == "HTML-pdf2htmlEX版":
			if output_mode == "HTML截图版":
				st.subheader("🌐 HTML 截图版参数")
			else:
				st.subheader("🌐 HTML-pdf2htmlEX版参数")
			
			col1, col2 = st.columns(2)
			with col1:
				if output_mode == "HTML截图版":
					screenshot_dpi = st.slider("截图DPI", 72, 300, 150, 12, help="截图质量，较高DPI生成更清晰的图片，但文件更大")
				else:  # HTML-pdf2htmlEX版
					screenshot_dpi = 150  # pdf2htmlEX不需要截图DPI
					st.info("pdf2htmlEX将直接转换PDF为HTML，无需截图")
			with col2:
				font_size = st.number_input("讲解字体大小", min_value=10, max_value=24, value=14, step=1, help="讲解文字的字体大小")
			
			col1, col2 = st.columns(2)
			with col1:
				html_column_count = st.slider("分栏数量", 1, 3, 2, 1, help="讲解内容的分栏数量，类似Word分栏排版")
			with col2:
				html_column_gap = st.slider("栏间距(px)", 10, 40, 20, 2, help="分栏之间的间距")
			
			html_show_column_rule = st.checkbox("显示栏间分隔线", value=True, help="在分栏之间显示分隔线")
			markdown_title = st.text_input("文档标题", value="PDF文档讲解", help="HTML文档的标题（留空则使用文件名）")
			embed_images = True
			st.divider()
		else:  # PDF讲解版
			# PDF模式的默认值
			screenshot_dpi = 150
			embed_images = True
			markdown_title = "PDF文档讲解"
			html_column_count = 2
			html_column_gap = 20
			html_show_column_rule = True
		
		# ============================================
		# 3. API 配置
		# ============================================
		with st.expander("🔑 API 配置", expanded=True):
			provider_options = ["Gemini", "OpenAI"]
			env_provider = os.getenv('LLM_PROVIDER', 'gemini').lower()
			default_provider_index = 1 if env_provider == 'openai' else 0
			provider_label = st.radio(
				"LLM 提供方",
				provider_options,
				index=default_provider_index,
				key="llm_provider_selector"
			)
			llm_provider = 'openai' if provider_label == "OpenAI" else 'gemini'
			
			if llm_provider == 'openai':
				default_api_key = os.getenv('OPENAI_API_KEY', os.getenv('API_KEY', ''))
				api_key_help = "您的 OpenAI API 密钥"
				default_model = os.getenv('OPENAI_MODEL_NAME', os.getenv('MODEL_NAME', 'gpt-4o-mini'))
				model_help = "使用的 OpenAI 模型"
				api_base_default = os.getenv('OPENAI_API_BASE', os.getenv('LLM_API_BASE', 'https://api.openai.com/v1')) or ""
				api_base_input = st.text_input(
					"API Base URL",
					value=api_base_default,
					help="OpenAI 兼容接口基础地址，可根据需要修改。",
					key="llm_api_base"
				)
				api_base = api_base_input.strip() or None
			else:
				default_api_key = os.getenv('GEMINI_API_KEY', os.getenv('API_KEY', ''))
				api_key_help = "您的 Gemini API 密钥"
				default_model = os.getenv('GEMINI_MODEL_NAME', os.getenv('MODEL_NAME', 'gemini-2.5-pro'))
				model_help = "使用的 Gemini 模型"
				api_base_env = os.getenv('GEMINI_API_BASE', os.getenv('LLM_API_BASE', ''))
				api_base = (api_base_env.strip() if api_base_env else None)
				# 占位以确保 Streamlit 保留先前输入
				st.session_state.setdefault("llm_api_base", api_base or "")
			
			api_key = st.text_input(
				"API Key",
				value=default_api_key,
				type="password",
				help=api_key_help,
				key="llm_api_key"
			)
			model_name = st.text_input(
				"模型名称",
				value=default_model,
				help=model_help,
				key="llm_model_name"
			)
			
			col1, col2 = st.columns(2)
			with col1:
				temperature = st.slider(
					"温度", 
					0.0, 1.0, 0.4, 0.1,
					help="控制输出随机性"
				)
			with col2:
				max_tokens = st.number_input(
					"最大输出 Tokens", 
					min_value=256, 
					max_value=8192, 
					value=4096, 
					step=256,
					help="限制单次响应长度"
				)
		
		# ============================================
		# 4. 性能配置
		# ============================================
		with st.expander("⚡ 性能配置", expanded=True):
			col1, col2 = st.columns(2)
			with col1:
				concurrency = st.slider(
					"并发页数", 
					1, 100, 50, 1,
					help="同时处理的页面数量"
				)
			with col2:
				dpi = st.number_input(
					"渲染DPI", 
					min_value=96, 
					max_value=300, 
					value=180, 
					step=12,
					help="页面渲染质量（仅供LLM）"
				)
			
			rpm_limit = st.number_input(
				"RPM 上限 (请求/分钟)", 
				min_value=10, 
				max_value=5000, 
				value=150, 
				step=10,
				help="每分钟请求数限制"
			)
			
			col1, col2 = st.columns(2)
			with col1:
				tpm_budget = st.number_input(
					"TPM 预算", 
					min_value=100000, 
					max_value=20000000, 
					value=2000000, 
					step=100000,
					help="每分钟 Token 预算"
				)
			with col2:
				rpd_limit = st.number_input(
					"RPD 上限", 
					min_value=100, 
					max_value=100000, 
					value=10000, 
					step=100,
					help="每天请求数限制"
				)
		
		# ============================================
		# 5. 高级排版配置 - 默认折叠
		# ============================================
		with st.expander("🎨 高级排版配置", expanded=False):
			# PDF模式专属参数
			if output_mode == "PDF讲解版":
				col1, col2 = st.columns(2)
				with col1:
					right_ratio = st.slider(
						"右侧留白比例", 
						0.2, 0.6, 0.48, 0.01,
						help="右侧讲解区域占页面宽度比例"
					)
				with col2:
					font_size = st.number_input(
						"右栏字体大小", 
						min_value=8, 
						max_value=20, 
						value=20, 
						step=1,
						help="讲解文字的字体大小"
					)
				
				col1, col2 = st.columns(2)
				with col1:
					line_spacing = st.slider(
						"讲解文本行距", 
						0.6, 2.0, 1.2, 0.1,
						help="行与行之间的距离"
					)
				with col2:
					column_padding = st.slider(
						"栏内边距", 
						2, 16, 10, 1,
						help="控制每栏左右内边距"
					)
				
				# 字体选择
				try:
					from app.services.font_helper import get_windows_cjk_fonts
					available_fonts = get_windows_cjk_fonts()
					font_options = [font[0] for font in available_fonts]
					try:
						default_index = font_options.index("SimHei")
					except ValueError:
						default_index = 0
					cjk_font_name = st.selectbox(
						"CJK 字体", 
						font_options, 
						index=default_index, 
						help="选择用于显示中文的字体"
					)
				except Exception as e:
					st.warning(f"无法检测系统字体，使用默认字体: {e}")
					cjk_font_name = "SimHei"
				
				render_mode = st.selectbox(
					"右栏渲染方式", 
					["text", "markdown", "pandoc"], 
					index=1,
					help="text: 普通文本\nmarkdown: Markdown渲染\npandoc: 高质量PDF (需Pandoc)"
				)
			else:
				# 非PDF模式的默认值
				right_ratio = 0.48
				font_size = 20
				line_spacing = 1.2
				column_padding = 10
				cjk_font_name = "SimHei"
				render_mode = "markdown"
		
		# ============================================
		# 6. 讲解风格配置 - 所有模式通用
		# ============================================
		with st.expander("✍️ 讲解风格配置", expanded=False):
			user_prompt = st.text_area(
				"讲解风格/要求", 
				value="请用中文讲解本页pdf，关键词给出英文，讲解详尽，语言简洁易懂。讲解让人一看就懂，便于快速学习。请避免不必要的换行，使页面保持紧凑。",
				help="自定义讲解提示词，指导LLM如何生成讲解内容"
			)
		
		# ============================================
		# 7. 上下文增强 - 对所有模式可用
		# ============================================
		with st.expander("🧠 上下文增强", expanded=False):
			use_context = st.checkbox(
				"启用前后各1页上下文", 
				value=False, 
				help="启用后，LLM将同时看到前一页、当前页和后一页的内容，提高讲解连贯性。会增加API调用成本。"
			)
			context_prompt_text = st.text_area(
				"上下文提示词", 
				value="你将看到前一页、当前页和后一页的内容。请结合上下文信息，生成连贯的讲解。当前页是重点讲解页面，你不需要跟我讲上一页、下一页讲了什么。", 
				disabled=not use_context, 
				help="独立的上下文说明提示词，用于指导LLM如何处理多页内容。"
			)
		
	
	return {
		"llm_provider": llm_provider,
		"api_key": api_key,
		"api_base": api_base,
		"model_name": model_name,
		"temperature": float(temperature),
		"max_tokens": int(max_tokens),
		"dpi": int(dpi),
		"right_ratio": float(right_ratio),
		"font_size": int(font_size),
		"line_spacing": float(line_spacing),
		"column_padding": int(column_padding),
		"concurrency": int(concurrency),
		"rpm_limit": int(rpm_limit),
		"tpm_budget": int(tpm_budget),
		"rpd_limit": int(rpd_limit),
		"user_prompt": user_prompt.strip(),
		"cjk_font_name": cjk_font_name,
		"render_mode": render_mode,
		"use_context": bool(use_context),
		"context_prompt": context_prompt_text.strip() if use_context else None,
		"output_mode": output_mode,
		"screenshot_dpi": screenshot_dpi,
		"embed_images": embed_images,
		"markdown_title": markdown_title,
		"html_column_count": html_column_count,
		"html_column_gap": html_column_gap,
		"html_show_column_rule": html_show_column_rule,
	}


def batch_process_files(uploaded_files: List, params: Dict[str, Any]) -> None:
	"""
	Process multiple files in batch.
	
	Args:
		uploaded_files: List of uploaded files
		params: Processing parameters
	"""
	from app.services import pdf_processor
	
	# Validate inputs
	is_valid, error_msg = validate_file_upload(uploaded_files, params)
	if not is_valid:
		st.error(error_msg)
		if not uploaded_files:
			st.stop()
		return
	
	# Initialize processing state
	StateManager.set_processing(True)
	StateManager.set_batch_results({})
	st.session_state["batch_zip_bytes"] = None
	
	total_files = len(uploaded_files)
	output_mode = params.get("output_mode", "PDF讲解版")
	
	if output_mode == "Markdown截图讲解":
		st.info(f"开始批量处理 {total_files} 个文件：逐页渲染→生成讲解→生成Markdown文档（包含截图）")
	elif output_mode == "HTML截图版":
		st.info(f"开始批量处理 {total_files} 个文件：逐页渲染→生成讲解→生成HTML文档（包含截图和多栏布局）")
	elif output_mode == "HTML-pdf2htmlEX版":
		st.info(f"开始批量处理 {total_files} 个文件：逐页渲染→生成讲解→使用pdf2htmlEX转换→生成HTML文档（高质量PDF转HTML）")
	else:
		st.info(f"开始批量处理 {total_files} 个文件：逐页渲染→生成讲解→合成新PDF（保持向量）")
	
	# Progress tracking
	overall_progress = st.progress(0)
	overall_status = st.empty()
	
	# Process each file
	for i, uploaded_file in enumerate(uploaded_files):
		filename = uploaded_file.name
		StateManager.get_batch_results()[filename] = {
			"status": "processing",
			"pdf_bytes": None,
			"explanations": {},
			"failed_pages": [],
			"json_bytes": None
		}
		
		# Update progress
		overall_progress.progress(int((i / total_files) * 100))
		overall_status.write(f"正在处理文件 {i+1}/{total_files}: {filename}")
		
		# Read file bytes and get cache hash
		uploaded_file.seek(0)  # Reset file pointer in case it was read before
		src_bytes = uploaded_file.read()
		file_hash = get_file_hash(src_bytes, params)
		cached_result = load_result_from_file(file_hash)
		
		# Process file (pass bytes directly to avoid file read issues)
		result = process_single_file(src_bytes, filename, params, file_hash, cached_result)
		StateManager.get_batch_results()[filename] = result
		
		# Display result
		display_file_result(filename, result)
	
	# Complete processing
	overall_progress.progress(100)
	overall_status.write("批量处理完成！")
	
	# Statistics
	batch_results = StateManager.get_batch_results()
	completed = sum(1 for r in batch_results.values() if r.get("status") == "completed")
	failed = sum(1 for r in batch_results.values() if r.get("status") == "failed")
	
	if completed > 0:
		st.success(f"🎉 批量处理完成！成功: {completed} 个文件，失败: {failed} 个文件")
	else:
		st.error("❌ 所有文件处理失败")
	
	# Build ZIP cache
	if output_mode == "Markdown截图讲解":
		st.session_state["batch_zip_bytes"] = build_zip_cache_markdown(batch_results)
	elif output_mode == "HTML截图版":
		from app.ui_helpers import build_zip_cache_html_screenshot
		st.session_state["batch_zip_bytes"] = build_zip_cache_html_screenshot(batch_results)
	elif output_mode == "HTML-pdf2htmlEX版":
		from app.ui_helpers import build_zip_cache_html_pdf2htmlex
		st.session_state["batch_zip_bytes"] = build_zip_cache_html_pdf2htmlex(batch_results)
	else:
		st.session_state["batch_zip_bytes"] = build_zip_cache_pdf(batch_results)
	
	StateManager.set_processing(False)


def main():
	setup_page()
	params = sidebar_form()
	
	# Initialize state
	StateManager.initialize()
	
	# Display current batch status
	display_batch_status()

	# Batch file upload
	uploaded_files = st.file_uploader("上传 PDF 文件 (最多20个)", type=["pdf"], accept_multiple_files=True)
	if uploaded_files and len(uploaded_files) > 20:
		st.error("最多只能上传20个文件")
		uploaded_files = uploaded_files[:20]
		st.warning("已自动截取前20个文件")

	col_run, col_save = st.columns([2, 1])

	# Download options
	with col_save:
		st.subheader("下载选项")
		download_mode = st.radio(
			"下载方式",
			["分别下载", "打包下载"],
			help="分别下载：为每个PDF生成单独下载按钮\n打包下载：将所有PDF打包成ZIP文件"
		)
		if download_mode == "打包下载":
			zip_filename = st.text_input("ZIP文件名", value="批量讲解PDF.zip")

	# Batch processing button
	with col_run:
		if st.button("批量生成讲解与合成", type="primary", use_container_width=True, disabled=StateManager.is_processing()):
			if uploaded_files:
				batch_process_files(uploaded_files, params)

	with col_save:
		# 显示批量处理结果
		batch_results = st.session_state.get("batch_results", {})
		if batch_results:
			st.subheader("📋 处理结果汇总")

			# 统计信息
			total_files = len(batch_results)
			completed_files = sum(1 for r in batch_results.values() if r["status"] == "completed")
			failed_files = sum(1 for r in batch_results.values() if r["status"] == "failed")

			col_stat1, col_stat2, col_stat3 = st.columns(3)
			with col_stat1:
				st.metric("总文件数", total_files)
			with col_stat2:
				st.metric("成功处理", completed_files)
			with col_stat3:
				st.metric("处理失败", failed_files)

			# 详细结果列表
			with st.expander("查看详细结果", expanded=False):
				for filename, result in batch_results.items():
					if result["status"] == "completed":
						st.success(f"✅ {filename} - 处理成功")
						if result["failed_pages"]:
							st.warning(f"  ⚠️ {len(result['failed_pages'])} 页生成讲解失败")
					else:
						st.error(f"❌ {filename} - 处理失败: {result.get('error', '未知错误')}")

			# 重试失败的文件
			failed_files_list = [f for f, r in batch_results.items() if r["status"] == "failed"]
			if failed_files_list and not st.session_state.get("batch_processing", False):
				st.subheader("🔄 重试失败的文件")
				if st.button(f"重试 {len(failed_files_list)} 个失败的文件", use_container_width=True):
					st.info(f"开始重试 {len(failed_files_list)} 个失败的文件...")

					# 找到原始上传的文件
					retry_files = []
					for failed_filename in failed_files_list:
						for uploaded_file in uploaded_files:
							if uploaded_file.name == failed_filename:
								retry_files.append(uploaded_file)
								break

					if retry_files:
						from app.services import pdf_processor

						retry_progress = st.progress(0)
						retry_status = st.empty()

						for i, uploaded_file in enumerate(retry_files):
							filename = uploaded_file.name
							retry_progress.progress(int((i / len(retry_files)) * 100))
							retry_status.write(f"重试文件 {i+1}/{len(retry_files)}: {filename}")

							try:
								src_bytes = uploaded_file.read()

								file_progress = st.progress(0)
								file_status = st.empty()

								def on_file_progress(done: int, total: int):
									pct = int(done * 100 / max(1, total))
									file_progress.progress(pct)
									file_status.write(f"{filename}: 正在生成讲解 {done}/{total}")

								def on_file_log(msg: str):
									file_status.write(f"{filename}: {msg}")

								with st.spinner(f"重试 {filename} 中..."):
									explanations, preview_images, failed_pages = pdf_processor.generate_explanations(
										src_bytes=src_bytes,
										api_key=params["api_key"],
										model_name=params["model_name"],
										user_prompt=params["user_prompt"],
										temperature=params["temperature"],
										max_tokens=params["max_tokens"],
										dpi=params["dpi"],
										concurrency=params["concurrency"],
										rpm_limit=params["rpm_limit"],
										tpm_budget=params["tpm_budget"],
										rpd_limit=params["rpd_limit"],
										on_progress=on_file_progress,
										on_log=on_file_log,
										use_context=params.get("use_context", False),
									context_prompt=params.get("context_prompt", None),
									llm_provider=params.get("llm_provider", "gemini"),
									api_base=params.get("api_base"),
									)

									result_bytes = pdf_processor.compose_pdf(
										src_bytes,
										explanations,
										params["right_ratio"],
										params["font_size"],
										font_name=(params.get("cjk_font_name") or "SimHei"),
										render_mode=params.get("render_mode", "markdown"),
										line_spacing=params["line_spacing"],
										column_padding=params.get("column_padding", 10)
									)

								st.session_state["batch_results"][filename] = {
									"status": "completed",
									"pdf_bytes": result_bytes,
									"explanations": explanations,
									"failed_pages": failed_pages
								}

								st.success(f"✅ {filename} 重试成功！")
								if failed_pages:
									st.warning(f"⚠️ {filename} 中仍有 {len(failed_pages)} 页生成讲解失败")

								file_progress.empty()
								file_status.empty()

							except Exception as e:
								st.error(f"❌ {filename} 重试仍然失败: {str(e)}")

						retry_progress.progress(100)
						retry_status.write("重试完成！")

						# 更新统计
						completed_after_retry = sum(1 for r in st.session_state["batch_results"].values() if r["status"] == "completed")
						failed_after_retry = sum(1 for r in st.session_state["batch_results"].values() if r["status"] == "failed")
						st.success(f"重试后结果：成功 {completed_after_retry} 个，失败 {failed_after_retry} 个")

					else:
						st.error("无法找到需要重试的文件")

		# 下载功能
		if batch_results and any(r["status"] == "completed" for r in batch_results.values()):
			st.subheader("📥 下载结果")

			if download_mode == "打包下载":
				zip_bytes = st.session_state.get("batch_zip_bytes")
				output_mode = params.get("output_mode", "PDF讲解版")
				
				if output_mode == "HTML截图版":
					label_text = "📦 下载所有HTML和讲解JSON (ZIP)"
				elif output_mode == "HTML-pdf2htmlEX版":
					label_text = "📦 下载所有HTML-pdf2htmlEX和讲解JSON (ZIP)"
				elif output_mode == "Markdown截图讲解":
					label_text = "📦 下载所有Markdown和讲解JSON (ZIP)"
				else:
					label_text = "📦 下载所有PDF和讲解JSON (ZIP)"
				
				st.download_button(
					label=label_text,
					data=zip_bytes,
					file_name=zip_filename,
					mime="application/zip",
					use_container_width=True,
					disabled=st.session_state.get("batch_processing", False) or not bool(zip_bytes),
					key="download_all_zip"
				)

			else:  # 分别下载
				st.write("**分别下载每个文件：**")
				for filename, result in batch_results.items():
					if result["status"] == "completed":
						base_name = os.path.splitext(filename)[0]

						if params["output_mode"] == "Markdown截图讲解":
							# Markdown模式：下载markdown文件和JSON
							markdown_filename = f"{base_name}讲解文档.md"
							json_filename = f"{base_name}.json"

							col_dl1, col_dl2 = st.columns(2)
							with col_dl1:
								if result.get("markdown_content"):
									st.download_button(
										label=f"📄 {markdown_filename}",
										data=result["markdown_content"],
										file_name=markdown_filename,
										mime="text/markdown",
										use_container_width=True,
										disabled=st.session_state.get("batch_processing", False),
										key=f"download_md_{filename}"
									)
							with col_dl2:
								if result.get("explanations"):
									try:
										json_bytes = json.dumps(result["explanations"], ensure_ascii=False, indent=2).encode("utf-8")
										st.download_button(
											label=f"📝 {json_filename}",
											data=json_bytes,
											file_name=json_filename,
											mime="application/json",
											use_container_width=True,
											disabled=st.session_state.get("batch_processing", False),
											key=f"download_json_{filename}"
										)
									except Exception:
										pass
						elif params["output_mode"] == "HTML截图版" or params["output_mode"] == "HTML-pdf2htmlEX版":
							# HTML截图版/pdf2htmlEX模式：下载HTML文件和JSON
							html_filename = f"{base_name}讲解文档.html"
							json_filename = f"{base_name}.json"

							col_dl1, col_dl2 = st.columns(2)
							with col_dl1:
								if result.get("html_content"):
									st.download_button(
										label=f"🌐 {html_filename}",
										data=result["html_content"],
										file_name=html_filename,
										mime="text/html",
										use_container_width=True,
										disabled=st.session_state.get("batch_processing", False),
										key=f"download_html_{filename}"
									)
							with col_dl2:
								if result.get("explanations"):
									try:
										json_bytes = json.dumps(result["explanations"], ensure_ascii=False, indent=2).encode("utf-8")
										st.download_button(
											label=f"📝 {json_filename}",
											data=json_bytes,
											file_name=json_filename,
											mime="application/json",
											use_container_width=True,
											disabled=st.session_state.get("batch_processing", False),
											key=f"download_json_html_{filename}"
										)
									except Exception:
										pass
						else:
							# PDF模式：下载PDF文件和JSON
							pdf_filename = f"{base_name}讲解版.pdf"
							json_filename = f"{base_name}.json"

							col_dl1, col_dl2 = st.columns(2)
							with col_dl1:
								if result.get("pdf_bytes"):
									st.download_button(
										label=f"📄 {pdf_filename}",
										data=result["pdf_bytes"],
										file_name=pdf_filename,
										mime="application/pdf",
										use_container_width=True,
										disabled=st.session_state.get("batch_processing", False),
										key=f"download_pdf_{filename}"
									)
							with col_dl2:
								if result.get("explanations"):
									json_bytes = result.get("json_bytes")
									st.download_button(
										label=f"📝 {json_filename}",
										data=json_bytes,
										file_name=json_filename,
										mime="application/json",
										use_container_width=True,
										disabled=st.session_state.get("batch_processing", False) or not bool(json_bytes),
										key=f"download_json_{filename}"
									)

	def _build_and_run_with_pairs(pairs):
		import json
		from app.services import pdf_processor

		output_mode = params.get("output_mode", "PDF讲解版")
		if output_mode == "Markdown截图讲解":
			st.info("开始批量根据JSON重新生成Markdown文档...")
		elif output_mode == "HTML截图版":
			st.info("开始批量根据JSON重新生成HTML文档...")
		elif output_mode == "HTML-pdf2htmlEX版":
			st.info("开始批量根据JSON重新生成HTML-pdf2htmlEX文档...")
		else:
			st.info("开始批量根据JSON重新生成PDF...")

		st.session_state["batch_json_processing"] = True
		st.session_state["batch_json_results"] = {}
		st.session_state["batch_json_zip_bytes"] = None

		# 将确认配对转为现有批处理入口的两个列表，并让 JSON 名与 PDF 同名匹配
		pdf_data, json_data = [], []
		for pdf_obj, json_obj in pairs:
			pdf_name = pdf_obj.name
			json_alias = os.path.splitext(pdf_name)[0] + ".json"
			pdf_data.append((pdf_name, pdf_obj.read()))
			json_data.append((json_alias, json_obj.read()))

		batch_results = {}

		if output_mode == "Markdown截图讲解":
			# Markdown模式：手动处理每个文件
			for pdf_name, pdf_bytes in pdf_data:
				try:
					# 找到对应的JSON数据
					json_filename = os.path.splitext(pdf_name)[0] + ".json"
					json_content = None
					for json_name, json_bytes in json_data:
						if json_name == json_filename:
							json_content = json.loads(json_bytes.decode('utf-8'))
							break

					if json_content is None:
						batch_results[pdf_name] = {
							"status": "failed",
							"error": "未找到匹配的JSON文件"
						}
						continue

					# 转换键为整数
					explanations = {int(k): str(v) for k, v in json_content.items()}

					# 创建临时目录保存图片（如果不嵌入）
					embed_images = params.get("embed_images", True)
					images_dir = None
					if not embed_images:
						base_name = os.path.splitext(pdf_name)[0]
						images_dir = os.path.join(TEMP_DIR, f"{base_name}_images")
						os.makedirs(images_dir, exist_ok=True)

					# 生成markdown文档
					markdown_content, images_dir_return = pdf_processor.generate_markdown_with_screenshots(
						src_bytes=pdf_bytes,
						explanations=explanations,
						screenshot_dpi=params.get("screenshot_dpi", 150),
						embed_images=embed_images,
						title=params.get("markdown_title", "PDF文档讲解"),
						images_dir=images_dir
					)

					batch_results[pdf_name] = {
						"status": "completed",
						"markdown_content": markdown_content,
						"explanations": explanations,
						"images_dir": images_dir_return
					}

				except Exception as e:
					batch_results[pdf_name] = {
						"status": "failed",
						"error": str(e)
					}
		elif output_mode == "HTML截图版" or output_mode == "HTML-pdf2htmlEX版":
			# HTML截图版/pdf2htmlEX模式：手动处理每个文件
			for pdf_name, pdf_bytes in pdf_data:
				try:
					# 找到对应的JSON数据
					json_filename = os.path.splitext(pdf_name)[0] + ".json"
					json_content = None
					for json_name, json_bytes in json_data:
						if json_name == json_filename:
							json_content = json.loads(json_bytes.decode('utf-8'))
							break

					if json_content is None:
						batch_results[pdf_name] = {
							"status": "failed",
							"error": "未找到匹配的JSON文件"
						}
						continue

					# 转换键为整数
					explanations = {int(k): str(v) for k, v in json_content.items()}

					# 生成HTML文档
					base_name = os.path.splitext(pdf_name)[0]
					# Use user-configured title if provided, otherwise use filename
					title = params.get("markdown_title", "").strip() or base_name
					
					if output_mode == "HTML-pdf2htmlEX版":
						html_content = pdf_processor.generate_html_pdf2htmlex_document(
							src_bytes=pdf_bytes,
							explanations=explanations,
							title=title,
							font_name=params.get("cjk_font_name", "SimHei"),
							font_size=params.get("font_size", 14),
							line_spacing=params.get("line_spacing", 1.2),
							column_count=params.get("html_column_count", 2),
							column_gap=params.get("html_column_gap", 20),
							show_column_rule=params.get("html_show_column_rule", True)
						)
					else:  # HTML截图版
						html_content = pdf_processor.generate_html_screenshot_document(
							src_bytes=pdf_bytes,
							explanations=explanations,
							screenshot_dpi=params.get("screenshot_dpi", 150),
							title=title,
							font_name=params.get("cjk_font_name", "SimHei"),
							font_size=params.get("font_size", 14),
							line_spacing=params.get("line_spacing", 1.2),
							column_count=params.get("html_column_count", 2),
							column_gap=params.get("html_column_gap", 20),
							show_column_rule=params.get("html_show_column_rule", True)
						)

					batch_results[pdf_name] = {
						"status": "completed",
						"html_content": html_content,
						"explanations": explanations
					}

				except Exception as e:
					batch_results[pdf_name] = {
						"status": "failed",
						"error": str(e)
					}
		else:
			# PDF模式：使用现有的批处理方法
			batch_results = pdf_processor.batch_recompose_from_json(
				pdf_data,
				json_data,
				params["right_ratio"],
				params["font_size"],
				font_name=(params.get("cjk_font_name") or "SimHei"),
				render_mode=params.get("render_mode", "markdown"),
				line_spacing=params["line_spacing"],
				column_padding=params.get("column_padding", 10)
			)

		st.session_state["batch_json_results"] = batch_results

		# 构建ZIP缓存
		if output_mode == "Markdown截图讲解":
			completed_count = sum(1 for r in batch_results.values() if r["status"] == "completed" and r.get("markdown_content"))
			if completed_count > 0:
				zip_buffer = io.BytesIO()
				with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
					for filename, result in batch_results.items():
						if result["status"] == "completed" and result.get("markdown_content"):
							base_name = os.path.splitext(filename)[0]
							markdown_filename = f"{base_name}讲解文档.md"
							zip_file.writestr(markdown_filename, result["markdown_content"])
							# 保存JSON
							if result.get("explanations"):
								try:
									json_bytes = json.dumps(result["explanations"], ensure_ascii=False, indent=2).encode("utf-8")
									json_filename = f"{base_name}.json"
									zip_file.writestr(json_filename, json_bytes)
								except Exception:
									pass
							# 如果有外部图片文件夹，打包到ZIP中
							images_dir = result.get("images_dir")
							if images_dir and os.path.exists(images_dir):
								for img_file in os.listdir(images_dir):
									img_path = os.path.join(images_dir, img_file)
									if os.path.isfile(img_path):
										# 在ZIP中创建images目录
										zip_img_path = f"{base_name}_images/{img_file}"
										zip_file.write(img_path, zip_img_path)
				zip_buffer.seek(0)
				st.session_state["batch_json_zip_bytes"] = zip_buffer.getvalue()
			else:
				st.session_state["batch_json_zip_bytes"] = None
		elif output_mode == "HTML截图版" or output_mode == "HTML-pdf2htmlEX版":
			completed_count = sum(1 for r in batch_results.values() if r["status"] == "completed" and r.get("html_content"))
			if completed_count > 0:
				zip_buffer = io.BytesIO()
				with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
					for filename, result in batch_results.items():
						if result["status"] == "completed" and result.get("html_content"):
							base_name = os.path.splitext(filename)[0]
							html_filename = f"{base_name}讲解文档.html"
							zip_file.writestr(html_filename, result["html_content"])
							# 保存JSON
							if result.get("explanations"):
								try:
									json_bytes = json.dumps(result["explanations"], ensure_ascii=False, indent=2).encode("utf-8")
									json_filename = f"{base_name}.json"
									zip_file.writestr(json_filename, json_bytes)
								except Exception:
									pass
				zip_buffer.seek(0)
				st.session_state["batch_json_zip_bytes"] = zip_buffer.getvalue()
			else:
				st.session_state["batch_json_zip_bytes"] = None
		else:
			completed_count = sum(1 for r in batch_results.values() if r["status"] == "completed" and r.get("pdf_bytes"))
			if completed_count > 0:
				zip_buffer = io.BytesIO()
				with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
					for filename, result in batch_results.items():
						if result["status"] == "completed" and result.get("pdf_bytes"):
							base_name = os.path.splitext(filename)[0]
							new_filename = f"{base_name}讲解版.pdf"
							zip_file.writestr(new_filename, result["pdf_bytes"])
				zip_buffer.seek(0)
				st.session_state["batch_json_zip_bytes"] = zip_buffer.getvalue()
			else:
				st.session_state["batch_json_zip_bytes"] = None

		st.session_state["batch_json_processing"] = False

	# 批量根据JSON重新生成PDF/Markdown（单框上传 + 智能配对）
	st.subheader("📚 批量根据JSON重新生成PDF/Markdown（单框上传）")

	# 单一上传框：同时接收 PDF 与 JSON
	uploaded_mixed = st.file_uploader(
		"上传 PDF 与 JSON（可混合拖拽）",
		type=["pdf", "json"],
		accept_multiple_files=True,
		key="mixed_pdf_json"
	)

	MAX_BYTES = 209_715_200  # 200MB
	pdf_files, json_files = [], []
	if uploaded_mixed:
		for f in uploaded_mixed:
			if f.size and f.size > MAX_BYTES:
				st.error(f"{f.name} 超过200MB限制")
				continue
			name = f.name.lower()
			if name.endswith(".pdf"):
				pdf_files.append(f)
			elif name.endswith(".json"):
				json_files.append(f)

	# 文件智能配对显示
	if pdf_files and json_files:
		st.write("### 文件配对结果")

		# 使用pdf_processor的智能匹配功能
		from app.services import pdf_processor
		matches = pdf_processor.match_pdf_json_files(
			[f.name for f in pdf_files],
			[f.name for f in json_files]
		)

		# 显示配对结果
		col_match1, col_match2 = st.columns(2)
		with col_match1:
			st.write("**配对成功的文件：**")
			matched_pairs = [(pdf, json) for pdf, json in matches.items() if json is not None]
			if matched_pairs:
				for pdf_name, json_name in matched_pairs:
					st.success(f"📄 {pdf_name} ←→ 📝 {json_name}")
			else:
				st.warning("没有找到匹配的文件对")

		with col_match2:
			st.write("**未配对的文件：**")
			unmatched_pdfs = [pdf for pdf, json in matches.items() if json is None]
			unmatched_jsons = [json for json in [f.name for f in json_files] if json not in matches.values()]

			if unmatched_pdfs:
				for pdf in unmatched_pdfs:
					st.error(f"📄 {pdf} (无匹配JSON)")
			if unmatched_jsons:
				for json in unmatched_jsons:
					st.error(f"📝 {json} (无匹配PDF)")

		# 生成配对列表用于处理
		valid_pairs = []
		for pdf_file in pdf_files:
			matched_json_name = matches.get(pdf_file.name)
			if matched_json_name:
				# 找到对应的JSON文件对象
				for json_file in json_files:
					if json_file.name == matched_json_name:
						valid_pairs.append((pdf_file, json_file))
						break

		# 生成按钮
		if valid_pairs and not st.session_state.get("batch_json_processing", False):
			output_mode = params.get("output_mode", "PDF讲解版")
			if output_mode == 'Markdown截图讲解':
				doc_type = 'Markdown文档'
			elif output_mode == 'HTML截图版':
				doc_type = 'HTML文档'
			elif output_mode == 'HTML-pdf2htmlEX版':
				doc_type = 'HTML-pdf2htmlEX文档'
			else:
				doc_type = 'PDF'
			button_text = f"根据JSON重新生成{doc_type} ({len(valid_pairs)} 个文件)"
			if st.button(button_text, type="primary", use_container_width=True):
				_build_and_run_with_pairs(valid_pairs)

		# 显示批量JSON处理结果
		batch_json_results = st.session_state.get("batch_json_results", {})
		if batch_json_results:
			st.subheader("📥 批量JSON处理结果下载")
			# 统计信息
			total_files = len(batch_json_results)
			completed_files = sum(1 for r in batch_json_results.values() if r["status"] == "completed")
			failed_files = sum(1 for r in batch_json_results.values() if r["status"] == "failed")
			col_stat1, col_stat2, col_stat3 = st.columns(3)
			with col_stat1:
				st.metric("总文件数", total_files)
			with col_stat2:
				st.metric("成功处理", completed_files)
			with col_stat3:
				st.metric("处理失败", failed_files)
			output_mode = params.get("output_mode", "PDF讲解版")
			if completed_files > 0:
				if output_mode == "Markdown截图讲解":
					zip_filename = f"批量JSON重新生成Markdown_{time.strftime('%Y%m%d_%H%M%S')}.zip"
					button_label = "📦 下载所有成功处理的Markdown文档及图片 (ZIP)"
				elif output_mode == "HTML截图版":
					zip_filename = f"批量JSON重新生成HTML_{time.strftime('%Y%m%d_%H%M%S')}.zip"
					button_label = "📦 下载所有成功处理的HTML文档 (ZIP)"
				elif output_mode == "HTML-pdf2htmlEX版":
					zip_filename = f"批量JSON重新生成HTML-pdf2htmlEX_{time.strftime('%Y%m%d_%H%M%S')}.zip"
					button_label = "📦 下载所有成功处理的HTML-pdf2htmlEX文档 (ZIP)"
				else:
					zip_filename = f"批量JSON重新生成PDF_{time.strftime('%Y%m%d_%H%M%S')}.zip"
					button_label = "📦 下载所有成功处理的PDF (ZIP)"
				zip_bytes = st.session_state.get("batch_json_zip_bytes")
				st.info("💡 批量处理结果将以压缩包形式下载，包含所有文档和相关图片文件夹")
				st.download_button(
					label=button_label,
					data=zip_bytes,
					file_name=zip_filename,
					mime="application/zip",
					use_container_width=True,
					key="batch_json_zip_download",
					disabled=st.session_state.get("batch_json_processing", False) or not bool(zip_bytes)
				)
			
			# 显示处理失败的文件信息
			failed_results = {filename: result for filename, result in batch_json_results.items() if result["status"] == "failed"}
			if failed_results:
				st.write("**处理失败的文件：**")
				for filename, result in failed_results.items():
					st.error(f"❌ {filename} 处理失败: {result.get('error', '未知错误')}")


if __name__ == "__main__":
	main()
import os
import io
import time
import json
import zipfile
import hashlib
import tempfile
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

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


# 创建临时目录用于存储处理结果
TEMP_DIR = os.path.join(tempfile.gettempdir(), "pdf_processor_cache")
os.makedirs(TEMP_DIR, exist_ok=True)


def get_file_hash(file_bytes: bytes, params: dict) -> str:
	"""生成基于文件内容和参数的哈希值"""
	content = file_bytes + json.dumps(params, sort_keys=True).encode('utf-8')
	return hashlib.md5(content).hexdigest()


def save_result_to_file(file_hash: str, result: dict) -> str:
	"""将处理结果保存到临时文件"""
	filepath = os.path.join(TEMP_DIR, f"{file_hash}.json")
	with open(filepath, 'w', encoding='utf-8') as f:
		# 不保存pdf_bytes到文件，只保存其他信息
		result_copy = result.copy()
		result_copy.pop('pdf_bytes', None)
		json.dump(result_copy, f, ensure_ascii=False, indent=2)
	return filepath


def load_result_from_file(file_hash: str) -> Optional[dict]:
	"""从临时文件加载处理结果"""
	filepath = os.path.join(TEMP_DIR, f"{file_hash}.json")
	if os.path.exists(filepath):
		try:
			with open(filepath, 'r', encoding='utf-8') as f:
				return json.load(f)
		except:
			return None
	return None


@st.cache_data
def cached_process_pdf(src_bytes: bytes, params: dict) -> dict:
	"""缓存的PDF处理函数"""
	from app.services import pdf_processor

	file_hash = get_file_hash(src_bytes, params)
	column_padding = params.get("column_padding", 10)

	# 尝试从缓存文件加载
	cached_result = load_result_from_file(file_hash)
	if cached_result and cached_result.get("status") == "completed":
		# 如果有缓存，需要重新生成PDF bytes（因为bytes不能序列化到JSON）
		try:
			result_bytes = pdf_processor.compose_pdf(
				src_bytes,
				cached_result["explanations"],
				params["right_ratio"],
				params["font_size"],
				font_path=(params.get("cjk_font_path") or None),
				render_mode=params.get("render_mode", "markdown"),
				line_spacing=params["line_spacing"],
				column_padding=column_padding
			)
			cached_result["pdf_bytes"] = result_bytes
			return cached_result
		except Exception as e:
			# 从缓存重新合成PDF失败，返回错误结果
			return {
				"status": "failed",
				"pdf_bytes": None,
				"explanations": {},
				"failed_pages": [],
				"error": f"从缓存重新合成PDF失败: {str(e)}"
			}

	# 没有缓存或缓存无效，重新处理
	try:
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
			use_context=params.get("use_context", False),
			context_prompt=params.get("context_prompt", None),
		)

		result_bytes = pdf_processor.compose_pdf(
			src_bytes,
			explanations,
			params["right_ratio"],
			params["font_size"],
			font_path=(params.get("cjk_font_path") or None),
			render_mode=params.get("render_mode", "markdown"),
			line_spacing=params["line_spacing"],
			column_padding=column_padding
		)

		result = {
			"status": "completed",
			"pdf_bytes": result_bytes,
			"explanations": explanations,
			"failed_pages": failed_pages
		}

		# 保存到缓存文件
		save_result_to_file(file_hash, result)

		return result

	except Exception as e:
		result = {
			"status": "failed",
			"pdf_bytes": None,
			"explanations": {},
			"failed_pages": [],
			"error": str(e)
		}
		return result


@st.cache_data
def cached_process_markdown(src_bytes: bytes, params: dict) -> dict:
	"""缓存的markdown处理函数"""
	from app.services import pdf_processor

	file_hash = get_file_hash(src_bytes, params)

	# 尝试从缓存文件加载
	cached_result = load_result_from_file(file_hash)
	if cached_result and cached_result.get("status") == "completed":
		# 如果有缓存，需要重新生成markdown内容
		try:
			markdown_content, explanations, failed_pages, _ = pdf_processor.process_markdown_mode(
				src_bytes=src_bytes,
				api_key=params["api_key"],
				model_name=params["model_name"],
				user_prompt=params["user_prompt"],
				temperature=params["temperature"],
				max_tokens=params["max_tokens"],
				dpi=params["dpi"],
				screenshot_dpi=params["screenshot_dpi"],
				concurrency=params["concurrency"],
				rpm_limit=params["rpm_limit"],
				tpm_budget=params["tpm_budget"],
				rpd_limit=params["rpd_limit"],
				embed_images=params["embed_images"],
				title=params["markdown_title"],
				use_context=params.get("use_context", False),
				context_prompt=params.get("context_prompt", None),
			)
			cached_result["markdown_content"] = markdown_content
			return cached_result
		except Exception as e:
			# 从缓存重新生成markdown失败，返回错误结果
			return {
				"status": "failed",
				"markdown_content": "",
				"explanations": {},
				"failed_pages": [],
				"error": f"从缓存重新生成markdown失败: {str(e)}"
			}

	# 没有缓存或缓存无效，重新处理
	try:
		markdown_content, explanations, failed_pages, _ = pdf_processor.process_markdown_mode(
			src_bytes=src_bytes,
			api_key=params["api_key"],
			model_name=params["model_name"],
			user_prompt=params["user_prompt"],
			temperature=params["temperature"],
			max_tokens=params["max_tokens"],
			dpi=params["dpi"],
			screenshot_dpi=params["screenshot_dpi"],
			concurrency=params["concurrency"],
			rpm_limit=params["rpm_limit"],
			tpm_budget=params["tpm_budget"],
			rpd_limit=params["rpd_limit"],
			embed_images=params["embed_images"],
			title=params["markdown_title"],
			use_context=params.get("use_context", False),
			context_prompt=params.get("context_prompt", None),
		)

		result = {
			"status": "completed",
			"markdown_content": markdown_content,
			"explanations": explanations,
			"failed_pages": failed_pages
		}

		# 保存到缓存文件
		save_result_to_file(file_hash, result)

		return result

	except Exception as e:
		result = {
			"status": "failed",
			"markdown_content": "",
			"explanations": {},
			"failed_pages": [],
			"error": str(e)
		}
		return result


def setup_page():
	st.set_page_config(page_title="PDF 讲解流 · Gemini 2.5 Pro", layout="wide")
	st.title("PDF 讲解流 · Gemini 2.5 Pro")
	st.caption("逐页生成讲解，右侧留白排版，保持原PDF向量内容")


def sidebar_form():
	with st.sidebar:
		st.header("参数配置")
		api_key = st.text_input("GEMINI_API_KEY", value=os.getenv('GEMINI_API_KEY'),type="password")
		model_name = st.text_input("模型名", value="gemini-2.5-pro")
		temperature = st.slider("温度", 0.0, 1.0, 0.4, 0.1)
		max_tokens = st.number_input("最大输出 tokens", min_value=256, max_value=8192, value=4096, step=256)
		dpi = st.number_input("渲染DPI(仅供LLM)", min_value=96, max_value=300, value=180, step=12)
		right_ratio = st.slider("右侧留白比例", 0.2, 0.6, 0.48, 0.01)
		font_size = st.number_input("右栏字体大小", min_value=8, max_value=20, value=20, step=1)
		line_spacing = st.slider("讲解文本行距", 0.6, 2.0, 1.2, 0.1)
		column_padding = st.slider("栏内边距(像素)", 2, 16, 10, 1, help="控制每一栏左右内边距，防止文字被切边")
		concurrency = st.slider("并发页数", 1,100, 50, 1)
		rpm_limit = st.number_input("RPM 上限(请求/分钟)", min_value=10, max_value=5000, value=150, step=10)
		tpm_budget = st.number_input("TPM 预算(令牌/分钟)", min_value=100000, max_value=20000000, value=2000000, step=100000)
		rpd_limit = st.number_input("RPD 上限(请求/天)", min_value=100, max_value=100000, value=10000, step=100)
		user_prompt = st.text_area("讲解风格/要求(系统提示)", value="请用中文讲解本页pdf，关键词给出英文，讲解详尽，语言简洁易懂。讲解让人一看就懂，便于快速学习。请避免不必要的换行，使页面保持紧凑。")
		cjk_font_path = st.text_input("CJK 字体文件路径(可选)", value="assets/fonts/SIMHEI.TTF")
		render_mode = st.selectbox("右栏渲染方式", ["text", "markdown"], index=1)

		st.divider()
		st.subheader("输出模式选择")
		output_mode = st.radio(
			"选择输出格式",
			["Markdown截图讲解","PDF讲解版",],
			help="PDF讲解版：在PDF右侧添加讲解文字\nMarkdown截图讲解：生成包含页面截图和讲解的markdown文档"
		)

		# Markdown模式的参数
		if output_mode == "Markdown截图讲解":
			st.subheader("📝 Markdown参数")
			screenshot_dpi = st.slider("截图DPI", 72, 300, 150, 12, help="截图质量，较高DPI生成更清晰的图片，但文件更大")
			embed_images = st.checkbox("嵌入图片到Markdown", value=False, help="将截图base64编码嵌入markdown文件，否则使用外部图片文件")
			markdown_title = st.text_input("文档标题", value="PDF文档讲解")
		else:
			screenshot_dpi = 150
			embed_images = True
			markdown_title = "PDF文档讲解"
		
		st.divider()
		st.subheader("上下文增强")
		use_context = st.checkbox("启用前后各1页上下文", value=False, help="启用后，LLM将同时看到前一页、当前页和后一页的内容，提高讲解连贯性。会增加API调用成本。")
		context_prompt_text = st.text_area("上下文提示词", value="你将看到前一页、当前页和后一页的内容。请结合上下文信息，生成连贯的讲解。当前页是重点讲解页面，你不需要跟我讲上一页、下一页讲了什么。", disabled=not use_context, help="独立的上下文说明提示词，用于指导LLM如何处理多页内容。")
		
		return {
			"api_key": api_key,
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
			"cjk_font_path": cjk_font_path.strip(),
			"render_mode": render_mode,
			"use_context": bool(use_context),
			"context_prompt": context_prompt_text.strip() if use_context else None,
			"output_mode": output_mode,
			"screenshot_dpi": screenshot_dpi,
			"embed_images": embed_images,
			"markdown_title": markdown_title,
		}


def main():
	setup_page()
	params = sidebar_form()
	column_padding_value = params.get("column_padding", 10)

	# 显示当前处理状态
	batch_results = st.session_state.get("batch_results", {})
	if batch_results:
		total_files = len(batch_results)
		completed_files = sum(1 for r in batch_results.values() if r["status"] == "completed")
		failed_files = sum(1 for r in batch_results.values() if r["status"] == "failed")
		processing_files = sum(1 for r in batch_results.values() if r["status"] == "processing")

		if processing_files > 0:
			st.info(f"🔄 正在处理中... 已完成: {completed_files}/{total_files} 个文件")
		elif completed_files > 0:
			st.success(f"✅ 处理完成！成功: {completed_files} 个文件，失败: {failed_files} 个文件")
		elif failed_files > 0:
			st.error(f"❌ 处理失败！失败: {failed_files} 个文件")

	# 批量上传模式
	uploaded_files = st.file_uploader("上传 PDF 文件 (最多20个)", type=["pdf"], accept_multiple_files=True)
	if len(uploaded_files) > 20:
		st.error("最多只能上传20个文件")
		uploaded_files = uploaded_files[:20]
		st.warning("已自动截取前20个文件")

	col_run, col_save = st.columns([2, 1])

	# 下载选项
	with col_save:
		st.subheader("下载选项")
		download_mode = st.radio(
			"下载方式",
			["分别下载", "打包下载"],
			help="分别下载：为每个PDF生成单独下载按钮\n打包下载：将所有PDF打包成ZIP文件"
		)
		if download_mode == "打包下载":
			zip_filename = st.text_input("ZIP文件名", value="批量讲解PDF.zip")

	# 初始化session_state
	if "batch_results" not in st.session_state:
		st.session_state["batch_results"] = {}  # {filename: {"pdf_bytes": bytes, "explanations": dict, "status": str, "failed_pages": list}}
	if "batch_processing" not in st.session_state:
		st.session_state["batch_processing"] = False
	if "batch_zip_bytes" not in st.session_state:
		st.session_state["batch_zip_bytes"] = None
	if "batch_json_results" not in st.session_state:
		st.session_state["batch_json_results"] = {}
	if "batch_json_processing" not in st.session_state:
		st.session_state["batch_json_processing"] = False
	if "batch_json_zip_bytes" not in st.session_state:
		st.session_state["batch_json_zip_bytes"] = None

	with col_run:
		if st.button("批量生成讲解与合成", type="primary", use_container_width=True, disabled=st.session_state.get("batch_processing", False)):
			if not uploaded_files:
				st.error("请先上传 PDF 文件")
				st.stop()
			if not params["api_key"]:
				st.error("请在侧边栏填写 GEMINI_API_KEY")
				st.stop()

			st.session_state["batch_processing"] = True
			st.session_state["batch_results"] = {}
			st.session_state["batch_zip_bytes"] = None

			total_files = len(uploaded_files)
			if params["output_mode"] == "Markdown截图讲解":
				st.info(f"开始批量处理 {total_files} 个文件：逐页渲染→生成讲解→生成Markdown文档（包含截图）")
			else:
				st.info(f"开始批量处理 {total_files} 个文件：逐页渲染→生成讲解→合成新PDF（保持向量）")

			# 延后导入以加快首屏
			from app.services import pdf_processor

			# 整体进度
			overall_progress = st.progress(0)
			overall_status = st.empty()

			# 限制同时处理的PDF数量，避免API过载
			max_concurrent_pdfs = min(5, total_files)  # 最多同时处理5个PDF

			for i, uploaded_file in enumerate(uploaded_files):
				filename = uploaded_file.name
				st.session_state["batch_results"][filename] = {"status": "processing", "pdf_bytes": None, "explanations": {}, "failed_pages": [], "json_bytes": None}

				# 更新整体进度
				overall_progress.progress(int((i / total_files) * 100))
				overall_status.write(f"正在处理文件 {i+1}/{total_files}: {filename}")

				try:
					# 读取源PDF bytes
					src_bytes = uploaded_file.read()

					# 验证PDF文件有效性
					is_valid, validation_error = pdf_processor.validate_pdf_file(src_bytes)
					if not is_valid:
						st.session_state["batch_results"][filename] = {
							"status": "failed",
							"pdf_bytes": None,
							"explanations": {},
							"failed_pages": [],
							"error": f"PDF文件验证失败: {validation_error}"
						}
						st.error(f"❌ {filename} PDF文件无效: {validation_error}")
						continue

					# 检查是否有缓存
					file_hash = get_file_hash(src_bytes, params)
					cached_result = load_result_from_file(file_hash)

					# 根据输出模式选择处理方式
					if params["output_mode"] == "Markdown截图讲解":
						# Markdown模式下的缓存和处理逻辑
						st.session_state["batch_results"][filename] = {"status": "processing", "markdown_content": "", "explanations": {}, "failed_pages": []}

						if cached_result and cached_result.get("status") == "completed":
							st.info(f"📋 {filename} 使用缓存结果")
							# 从缓存加载，需要重新生成markdown
							try:
								markdown_content, explanations, failed_pages, _ = pdf_processor.process_markdown_mode(
									src_bytes=src_bytes,
									api_key=params["api_key"],
									model_name=params["model_name"],
									user_prompt=params["user_prompt"],
									temperature=params["temperature"],
									max_tokens=params["max_tokens"],
									dpi=params["dpi"],
									screenshot_dpi=params["screenshot_dpi"],
									concurrency=params["concurrency"],
									rpm_limit=params["rpm_limit"],
									tpm_budget=params["tpm_budget"],
									rpd_limit=params["rpd_limit"],
									embed_images=params["embed_images"],
									title=params["markdown_title"],
									use_context=params.get("use_context", False),
									context_prompt=params.get("context_prompt", None),
								)
								st.session_state["batch_results"][filename] = {
									"status": "completed",
									"markdown_content": markdown_content,
									"explanations": explanations,
									"failed_pages": failed_pages
								}
							except Exception as e:
								# 缓存重新生成失败，标记为失败并尝试重新处理
								st.warning(f"缓存重新生成失败，尝试重新处理: {str(e)}")
								st.session_state["batch_results"][filename] = {"status": "processing", "markdown_content": "", "explanations": {}, "failed_pages": []}
								# 继续到下面的重新处理逻辑
								cached_result = None
						else:
							# 需要重新处理
							with st.spinner(f"处理 {filename} 中..."):
								result = cached_process_markdown(src_bytes, params)
								st.session_state["batch_results"][filename] = result

						result = st.session_state["batch_results"][filename]
						if result["status"] == "completed":
							st.success(f"✅ {filename} 处理完成！")
						if result["failed_pages"]:
							st.warning(f"⚠️ {filename} 中 {len(result['failed_pages'])} 页生成讲解失败")
						else:
							st.error(f"❌ {filename} 处理失败: {result.get('error', '未知错误')}")
					else:
						# PDF模式下的缓存和处理逻辑
						if cached_result and cached_result.get("status") == "completed":
							st.info(f"📋 {filename} 使用缓存结果")
							# 从缓存加载，需要重新合成PDF
							try:
								result_bytes = pdf_processor.compose_pdf(
									src_bytes,
									cached_result["explanations"],
									params["right_ratio"],
									params["font_size"],
									font_path=(params.get("cjk_font_path") or None),
									render_mode=params.get("render_mode", "markdown"),
									line_spacing=params["line_spacing"],
									column_padding=column_padding_value
								)
								st.session_state["batch_results"][filename] = {
									"status": "completed",
									"pdf_bytes": result_bytes,
									"explanations": cached_result["explanations"],
									"failed_pages": cached_result["failed_pages"],
									"json_bytes": None
								}
							except Exception as e:
								# 缓存重新合成失败，标记为失败并尝试重新处理
								st.warning(f"缓存重新合成失败，尝试重新处理: {str(e)}")
								st.session_state["batch_results"][filename] = {"status": "processing", "pdf_bytes": None, "explanations": {}, "failed_pages": []}
								# 继续到下面的重新处理逻辑
								cached_result = None
						else:
							# 需要重新处理
							with st.spinner(f"处理 {filename} 中..."):
								result = cached_process_pdf(src_bytes, params)
								st.session_state["batch_results"][filename] = result

					result = st.session_state["batch_results"][filename]
					if result["status"] == "completed":
						st.success(f"✅ {filename} 处理完成！")
					if result["failed_pages"]:
						st.warning(f"⚠️ {filename} 中 {len(result['failed_pages'])} 页生成讲解失败")
					else:
						st.error(f"❌ {filename} 处理失败: {result.get('error', '未知错误')}")

				except Exception as e:
					st.session_state["batch_results"][filename] = {
						"status": "failed",
						"pdf_bytes": None,
						"explanations": {},
						"failed_pages": [],
						"error": str(e)
					}
					st.error(f"❌ {filename} 处理失败: {str(e)}")

			# 完成处理
			overall_progress.progress(100)
			overall_status.write("批量处理完成！")

			# 统计结果
			completed = sum(1 for r in st.session_state["batch_results"].values() if r["status"] == "completed")
			failed = sum(1 for r in st.session_state["batch_results"].values() if r["status"] == "failed")

			if completed > 0:
				st.success(f"🎉 批量处理完成！成功: {completed} 个文件，失败: {failed} 个文件")
			else:
				st.error("❌ 所有文件处理失败")

			# 根据输出模式处理下载缓存
			if params["output_mode"] == "Markdown截图讲解":
				# Markdown模式的下载缓存
				# 仅当存在成功项时构建ZIP
				completed_any = any(r.get("status") == "completed" and r.get("markdown_content") for r in st.session_state["batch_results"].values())
				if completed_any:
					zip_buffer = io.BytesIO()
					with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
						for fname, res in st.session_state["batch_results"].items():
							if res.get("status") == "completed" and res.get("markdown_content"):
								base_name = os.path.splitext(fname)[0]
								markdown_filename = f"{base_name}讲解文档.md"
								zip_file.writestr(markdown_filename, res["markdown_content"])
								# 如果有explanations，也保存为JSON
								if res.get("explanations"):
									try:
										json_bytes = json.dumps(res["explanations"], ensure_ascii=False, indent=2).encode("utf-8")
										json_filename = f"{base_name}.json"
										zip_file.writestr(json_filename, json_bytes)
									except Exception:
										pass
					zip_buffer.seek(0)
					st.session_state["batch_zip_bytes"] = zip_buffer.getvalue()
				else:
					st.session_state["batch_zip_bytes"] = None
			else:
				# PDF模式的下载缓存
				# 预生成每个文件的 json_bytes，并构建ZIP缓存
				for fname, res in st.session_state["batch_results"].items():
					if res.get("status") == "completed" and res.get("explanations"):
						try:
							res["json_bytes"] = json.dumps(res["explanations"], ensure_ascii=False, indent=2).encode("utf-8")
						except Exception:
							res["json_bytes"] = None
				# 仅当存在成功项时构建ZIP
				completed_any = any(r.get("status") == "completed" and r.get("pdf_bytes") for r in st.session_state["batch_results"].values())
				if completed_any:
					zip_buffer = io.BytesIO()
					with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
						for fname, res in st.session_state["batch_results"].items():
							if res.get("status") == "completed" and res.get("pdf_bytes"):
								base_name = os.path.splitext(fname)[0]
								new_filename = f"{base_name}讲解版.pdf"
								zip_file.writestr(new_filename, res["pdf_bytes"])
								if res.get("json_bytes"):
									json_filename = f"{base_name}.json"
									zip_file.writestr(json_filename, res["json_bytes"])
					zip_buffer.seek(0)
					st.session_state["batch_zip_bytes"] = zip_buffer.getvalue()
				else:
					st.session_state["batch_zip_bytes"] = None

			st.session_state["batch_processing"] = False

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
									)

									result_bytes = pdf_processor.compose_pdf(
										src_bytes,
										explanations,
										params["right_ratio"],
										params["font_size"],
										font_path=(params.get("cjk_font_path") or None),
										render_mode=params.get("render_mode", "markdown"),
										line_spacing=params["line_spacing"],
										column_padding=column_padding_value
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
				st.download_button(
					label="📦 下载所有PDF和讲解JSON (ZIP)",
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
		else:
			# PDF模式：使用现有的批处理方法
			batch_results = pdf_processor.batch_recompose_from_json(
				pdf_data,
				json_data,
				params["right_ratio"],
				params["font_size"],
				font_path=(params.get("cjk_font_path") or None),
				render_mode=params.get("render_mode", "markdown"),
				line_spacing=params["line_spacing"],
				column_padding=column_padding_value
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
			button_text = f"根据JSON重新生成{'Markdown文档' if output_mode == 'Markdown截图讲解' else 'PDF'} ({len(valid_pairs)} 个文件)"
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
				else:
					zip_filename = f"批量JSON重新生成PDF_{time.strftime('%Y%m%d_%H%M%S')}.zip"
				zip_bytes = st.session_state.get("batch_json_zip_bytes")
				st.download_button(
					label=f"📦 下载所有成功处理的{'PDF' if output_mode != 'Markdown截图讲解' else 'Markdown文档'} (ZIP)",
					data=zip_bytes,
					file_name=zip_filename,
					mime="application/zip",
					use_container_width=True,
					key="batch_json_zip_download",
					disabled=st.session_state.get("batch_json_processing", False) or not bool(zip_bytes)
				)
			st.write("**分别下载每个成功处理的文件：**")
			for filename, result in batch_json_results.items():
				if result["status"] == "completed":
					base_name = os.path.splitext(filename)[0]
					if output_mode == "Markdown截图讲解" and result.get("markdown_content"):
						# Markdown模式：下载markdown文件和JSON
						markdown_filename = f"{base_name}讲解文档.md"
						col_dl1, col_dl2 = st.columns([3, 1])
						with col_dl1:
							st.write(f"📄 {markdown_filename}")
						with col_dl2:
							st.download_button(
								label="下载",
								data=result["markdown_content"],
								file_name=markdown_filename,
								mime="text/markdown",
								key=f"batch_json_md_{filename}",
								disabled=st.session_state.get("batch_json_processing", False)
							)
					elif output_mode != "Markdown截图讲解" and result.get("pdf_bytes"):
						# PDF模式：下载PDF文件
						pdf_filename = f"{base_name}讲解版.pdf"
						col_dl1, col_dl2 = st.columns([3, 1])
						with col_dl1:
							st.write(f"📄 {pdf_filename}")
						with col_dl2:
							st.download_button(
								label="下载",
								data=result["pdf_bytes"],
								file_name=pdf_filename,
								mime="application/pdf",
								key=f"batch_json_pdf_{filename}",
								disabled=st.session_state.get("batch_json_processing", False)
							)
				elif result["status"] == "failed":
					# 显示失败的文件及其错误信息
					st.error(f"❌ {filename} 处理失败: {result.get('error', '未知错误')}")


if __name__ == "__main__":
	main()
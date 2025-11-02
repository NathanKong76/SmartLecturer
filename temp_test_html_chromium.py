import fitz
from app.services.pdf_processor import compose_pdf


def main():
	# 创建一页源PDF
	doc = fitz.open()
	p = doc.new_page()
	p.insert_text((50, 80), "Source Page - 左侧原PDF", fontsize=14)
	src_bytes = doc.tobytes()
	doc.close()

	# 右栏Markdown内容，含代码与公式（避免表格以减少 shell 转义问题）
	md = (
		"# 标题\n\n"
		"这是右栏 html_chromium 渲染测试。\n\n"
		"```python\nprint('hello 世界')\n```\n\n"
		"行内公式: $a^2+b^2=c^2$\n"
	)

	pdf_bytes = compose_pdf(
		src_bytes,
		{0: md},
		right_ratio=0.48,
		font_size=14,
		font_path="assets/fonts/SIMHEI.TTF",
		render_mode="html_chromium",
		line_spacing=1.2,
		column_padding=10,
	)
	with open("test_html_chromium.pdf", "wb") as f:
		f.write(pdf_bytes)
	print("OK test_html_chromium.pdf", len(pdf_bytes))


if __name__ == "__main__":
	main()

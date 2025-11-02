import json
import os
from app.services.pdf_processor import generate_markdown_with_screenshots

def create_sample_pdf():
    """创建一个简单的测试PDF文件"""
    try:
        import fitz  # PyMuPDF
        
        # 创建一个新的PDF文档
        doc = fitz.open()
        
        # 添加几页内容
        for i in range(3):
            page = doc.new_page()
            rect = fitz.Rect(50, 50, 500, 50)
            # 添加一些文本
            page.insert_text(fitz.Point(50, 50), f"这是第{i+1}页的测试内容", fontsize=12)
        
        # 保存到字节流
        pdf_bytes = doc.write()
        doc.close()
        
        return pdf_bytes
    except Exception as e:
        print(f"创建测试PDF失败: {e}")
        # 返回一个简单的PDF内容
        return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF"

def test_generate_markdown_with_screenshots():
    """测试generate_markdown_with_screenshots函数"""
    print("开始测试generate_markdown_with_screenshots函数...")
    
    # 创建测试PDF
    pdf_bytes = create_sample_pdf()
    print(f"创建了大小为 {len(pdf_bytes)} 字节的测试PDF")
    
    # 创建测试讲解内容
    explanations = {
        0: "这是第一页的讲解内容，包含一些技术细节和关键点。",
        1: "这是第二页的讲解内容，进一步解释了相关概念。",
        2: "这是第三页的讲解内容，总结了前面的内容并提供了一些结论。"
    }
    
    try:
        # 调用函数生成Markdown文档
        markdown_content = generate_markdown_with_screenshots(
            src_bytes=pdf_bytes,
            explanations=explanations,
            screenshot_dpi=150,
            embed_images=True,
            title="测试PDF文档讲解"
        )
        
        print("✓ Markdown文档生成成功")
        print(f"  生成的Markdown文档大小: {len(markdown_content)} 字符")
        print(f"  文档预览: {markdown_content[:200]}...")
        
        # 保存到文件以便查看
        with open("test_markdown_output.md", "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print("  已保存到 test_markdown_output.md 文件")
        
        return True
        
    except Exception as e:
        print(f"✗ Markdown文档生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_generate_markdown_with_screenshots()
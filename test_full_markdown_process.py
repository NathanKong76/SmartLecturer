import json
import os
from app.services.pdf_processor import generate_markdown_with_screenshots

def test_full_markdown_process():
    """测试完整的Markdown生成流程"""
    print("开始测试完整的Markdown生成流程...")
    
    # 创建测试PDF内容
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF"
    
    # 创建测试JSON内容
    explanations = {
        "0": "这是第一页的讲解内容。",
        "1": "这是第二页的讲解内容。",
        "2": "这是第三页的讲解内容。"
    }
    
    try:
        # 模拟streamlit应用中的处理流程
        # 1. 解析JSON
        json_content = {int(k): str(v) for k, v in explanations.items()}
        print(f"✓ JSON解析成功，包含 {len(json_content)} 个讲解条目")
        
        # 2. 生成Markdown文档
        markdown_content = generate_markdown_with_screenshots(
            src_bytes=pdf_content,
            explanations=json_content,
            screenshot_dpi=150,
            embed_images=True,
            title="测试PDF文档讲解"
        )
        
        print("✓ Markdown文档生成成功")
        print(f"  生成的Markdown文档大小: {len(markdown_content)} 字符")
        
        # 3. 模拟保存结果
        result = {
            "status": "completed",
            "markdown_content": markdown_content,
            "explanations": json_content
        }
        
        print("✓ 完整流程处理成功")
        return True
        
    except Exception as e:
        print(f"✗ 处理流程失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_full_markdown_process()
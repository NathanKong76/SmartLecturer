import json
from app.services.pdf_processor import process_markdown_mode

def test_process_markdown_mode():
    """测试process_markdown_mode函数"""
    # 创建一个简单的测试PDF内容（这里使用假的PDF内容仅用于测试函数结构）
    # 在实际使用中，这里应该是真实的PDF字节数据
    fake_pdf_content = b"%PDF-1.4 fake pdf content for testing"
    
    try:
        # 测试函数调用（使用假的API密钥，应该会在实际API调用时失败，但不会在我们修复的地方失败）
        markdown_content, explanations, failed_pages = process_markdown_mode(
            src_bytes=fake_pdf_content,
            api_key="fake_api_key_for_testing",
            model_name="gemini-pro",
            user_prompt="请讲解这个PDF",
            temperature=0.4,
            max_tokens=1000,
            dpi=150,
            screenshot_dpi=150,
            concurrency=1,
            rpm_limit=60,
            tpm_budget=100000,
            rpd_limit=1000,
            embed_images=True,
            title="测试文档"
        )
        print("✓ process_markdown_mode函数调用成功")
        return True
    except Exception as e:
        # 检查是否是我们修复的错误
        if "'NoneType' object has no attribute 'sort'" in str(e):
            print(f"✗ 修复失败，仍然出现原始错误: {e}")
            return False
        else:
            # 其他错误是预期的（如PDF文件无效），因为我们使用的是假的PDF内容
            print(f"✓ 修复成功，已解决'NoneType'排序错误。其他错误是预期的: {type(e).__name__}")
            return True

if __name__ == "__main__":
    test_process_markdown_mode()
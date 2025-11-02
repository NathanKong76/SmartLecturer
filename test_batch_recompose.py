import json
import os
from app.services.pdf_processor import batch_recompose_from_json

def test_batch_recompose_from_json():
    """测试批量根据JSON重新合成PDF的功能"""
    # 创建测试数据
    test_pdf_content = b"fake pdf content for testing"
    test_explanations = {
        "0": "这是第一页的讲解内容。",
        "1": "这是第二页的讲解内容，包含一些技术细节。",
        "2": "这是第三页的讲解内容，总结了前面的内容。"
    }
    
    # 创建测试JSON内容
    json_bytes = json.dumps(test_explanations, ensure_ascii=False).encode('utf-8')
    
    # 准备测试数据
    pdf_files = [("test.pdf", test_pdf_content)]
    json_files = [("test.json", json_bytes)]
    
    # 调用批量重新合成函数
    try:
        results = batch_recompose_from_json(
            pdf_files=pdf_files,
            json_files=json_files,
            right_ratio=0.48,
            font_size=20,
            font_path=None,
            render_mode="markdown",
            line_spacing=1.2,
            column_padding=10
        )
        
        print("✓ 批量重新合成测试完成")
        print(f"  处理结果: {results}")
        
        # 检查结果
        if "test.pdf" in results:
            result = results["test.pdf"]
            if result["status"] == "failed":
                print(f"✗ 处理失败: {result['error']}")
                return False
            else:
                print("✓ PDF重新合成成功")
                print(f"  PDF大小: {len(result['pdf_bytes']) if result['pdf_bytes'] else 0} 字节")
                return True
        else:
            print("✗ 未找到处理结果")
            return False
            
    except Exception as e:
        print(f"✗ 批量重新合成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_batch_recompose_from_json()
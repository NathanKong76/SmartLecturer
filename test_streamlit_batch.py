#!/usr/bin/env python3
"""
测试批量JSON重新生成PDF功能
"""
import sys
import io
import json
from app.services import pdf_processor

def test_batch_recompose():
    """测试batch_recompose_from_json函数"""
    print("开始测试batch_recompose_from_json函数...")

    # 创建测试PDF数据（一个简单的PDF）
    test_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000200 00000 n\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n284\n%%EOF"

    # 创建测试JSON数据
    test_json_content = json.dumps({0: "这是一个测试讲解内容"}, ensure_ascii=False).encode('utf-8')

    pdf_files = [("test.pdf", test_pdf_content)]
    json_files = [("test.json", test_json_content)]

    try:
        # 测试参数：font_size=20（其他参数都有默认值）
        results = pdf_processor.batch_recompose_from_json(
            pdf_files=pdf_files,
            json_files=json_files,
            font_size=20
        )
        print("✅ batch_recompose_from_json函数调用成功！")
        print(f"结果: {results}")
        return True

    except Exception as e:
        print(f"❌ batch_recompose_from_json函数调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_batch_recompose()
    sys.exit(0 if success else 1)

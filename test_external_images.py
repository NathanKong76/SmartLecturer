#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试外部图片打包功能
"""

import sys
import os
import tempfile
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services import pdf_processor

def test_external_images():
    """测试外部图片生成和打包"""
    print("Testing external images functionality...")
    
    # 创建一个简单的PDF（这里假设已经有一个测试PDF）
    # 由于我们没有实际的PDF文件，我们只测试函数调用和参数
    
    # 测试create_page_screenshot_markdown函数
    test_bytes = b"fake_png_data"
    result = pdf_processor.create_page_screenshot_markdown(
        page_num=1,
        screenshot_bytes=test_bytes,
        explanation="Test explanation",
        embed_images=False,
        image_path="/fake/path/page_1.png"
    )
    
    # 验证生成的内容
    assert "images/page_1.png" in result, "External image path not found in markdown"
    assert "Test explanation" in result, "Explanation not found in markdown"
    assert "data:image/png;base64" not in result, "Should not contain base64 when embed_images=False"
    
    print("[PASS] create_page_screenshot_markdown with external images")
    
    # 测试embed_images=True的情况
    result2 = pdf_processor.create_page_screenshot_markdown(
        page_num=1,
        screenshot_bytes=test_bytes,
        explanation="Test explanation",
        embed_images=True
    )
    
    assert "data:image/png;base64" in result2, "Should contain base64 when embed_images=True"
    assert "Test explanation" in result2, "Explanation not found in markdown"
    
    print("[PASS] create_page_screenshot_markdown with embedded images")
    
    print("\nAll tests passed! External images functionality works correctly.")
    return True

if __name__ == "__main__":
    try:
        test_external_images()
        sys.exit(0)
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

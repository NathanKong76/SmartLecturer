#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试图片路径修复
"""

import sys
import os
import tempfile

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services import pdf_processor

def test_image_path_generation():
    """测试图片路径生成"""
    print("Testing image path generation...")
    
    # 测试create_page_screenshot_markdown函数
    test_bytes = b"fake_png_data"
    
    # 测试1: 嵌入图片模式
    result1 = pdf_processor.create_page_screenshot_markdown(
        page_num=1,
        screenshot_bytes=test_bytes,
        explanation="Test explanation",
        embed_images=True
    )
    
    assert "data:image/png;base64" in result1, "Should contain base64 when embed_images=True"
    assert "Test explanation" in result1, "Explanation not found"
    print("[PASS] Embedded images path test")
    
    # 测试2: 外部图片模式 - 传递images_dir_name
    result2 = pdf_processor.create_page_screenshot_markdown(
        page_num=1,
        screenshot_bytes=test_bytes,
        explanation="Test explanation",
        embed_images=False,
        images_dir_name="Week12_Security2_images"
    )
    
    assert "Week12_Security2_images/page_1.png" in result2, f"Expected 'Week12_Security2_images/page_1.png' in result, got: {result2}"
    assert "Test explanation" in result2, "Explanation not found"
    assert "data:image/png;base64" not in result2, "Should not contain base64 when embed_images=False"
    print("[PASS] External images path test with images_dir_name")
    
    # 测试3: 外部图片模式 - 只传递image_path
    result3 = pdf_processor.create_page_screenshot_markdown(
        page_num=2,
        screenshot_bytes=test_bytes,
        explanation="Test explanation 2",
        embed_images=False,
        image_path="/fake/path/page_2.png"
    )
    
    assert "page_2.png" in result3, f"Expected 'page_2.png' in result, got: {result3}"
    assert "Test explanation 2" in result3, "Explanation not found"
    print("[PASS] External images path test with image_path only")
    
    print("\n✅ All image path tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_image_path_generation()
        sys.exit(0)
    except Exception as e:
        print(f"❌ [FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

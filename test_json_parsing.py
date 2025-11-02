import json
import os
from app.services.pdf_processor import safe_utf8_loads

def test_safe_utf8_loads_comprehensive():
    """全面测试safe_utf8_loads函数"""
    print("开始全面测试safe_utf8_loads函数...")
    
    # 测试1: 正常的UTF-8 JSON
    test_data = {"page_1": "这是第一页的讲解", "page_2": "这是第二页的讲解"}
    json_bytes = json.dumps(test_data, ensure_ascii=False).encode('utf-8')
    
    try:
        result = safe_utf8_loads(json_bytes, "test_normal.json")
        assert result == test_data
        print("✓ 测试1通过: 正常UTF-8 JSON解析")
    except Exception as e:
        print(f"✗ 测试1失败: {e}")
        return False
    
    # 测试2: 带BOM的UTF-8 JSON
    json_bytes_with_bom = b'\xef\xbb\xbf' + json_bytes
    try:
        result = safe_utf8_loads(json_bytes_with_bom, "test_bom.json")
        assert result == test_data
        print("✓ 测试2通过: 带BOM的UTF-8 JSON解析")
    except Exception as e:
        print(f"✗ 测试2失败: {e}")
        return False
    
    # 测试3: 空JSON
    empty_json = b'{}'
    try:
        result = safe_utf8_loads(empty_json, "test_empty.json")
        assert result == {}
        print("✓ 测试3通过: 空JSON解析")
    except Exception as e:
        print(f"✗ 测试3失败: {e}")
        return False
    
    # 测试4: 复杂JSON结构
    complex_data = {
        "0": "这是第一页的讲解内容，包含一些特殊字符：@#$%^&*()",
        "1": "这是第二页的讲解内容，包含数字：1234567890",
        "2": "这是第三页的讲解内容，包含英文：ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    }
    complex_json_bytes = json.dumps(complex_data, ensure_ascii=False).encode('utf-8')
    
    try:
        result = safe_utf8_loads(complex_json_bytes, "test_complex.json")
        assert result == complex_data
        print("✓ 测试4通过: 复杂JSON结构解析")
    except Exception as e:
        print(f"✗ 测试4失败: {e}")
        return False
    
    print("所有测试通过!")
    return True

if __name__ == "__main__":
    test_safe_utf8_loads_comprehensive()
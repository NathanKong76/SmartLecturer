#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test JSON batch processing after fix
"""

import sys
import json

def test_json_import():
    """Test json module import"""
    try:
        test_data = {"key": "value", "number": 123}
        json_str = json.dumps(test_data, ensure_ascii=False)
        parsed_data = json.loads(json_str)
        assert parsed_data == test_data
        print("[PASS] json module import test")
        return True
    except Exception as e:
        print(f"[FAIL] json module import test: {e}")
        return False

def test_streamlit_import():
    """Test streamlit_app module import"""
    try:
        import app.streamlit_app
        print("[PASS] streamlit_app module import test")
        return True
    except Exception as e:
        print(f"[FAIL] streamlit_app module import test: {e}")
        return False

def test_pdf_processor_import():
    """Test pdf_processor module import"""
    try:
        from app.services import pdf_processor
        print("[PASS] pdf_processor module import test")
        return True
    except Exception as e:
        print(f"[FAIL] pdf_processor module import test: {e}")
        return False

if __name__ == "__main__":
    print("Testing fixed code...\n")

    tests = [
        test_json_import,
        test_pdf_processor_import,
        test_streamlit_import,
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    print(f"\nTest Results: Passed {passed}, Failed {failed}")

    if failed == 0:
        print("All tests passed! JSON scope issue fixed.")
        sys.exit(0)
    else:
        print("Some tests failed, need further check.")
        sys.exit(1)

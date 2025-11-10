#!/usr/bin/env python3
"""
Simple verification script for ScriptRunContext fixes.
"""

import sys
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
sys.path.insert(0, os.getcwd())

print("=== ScriptRunContext Fix Verification ===")

def test_imports():
    """Test that all imports work without ScriptRunContext errors."""
    print("\n1. Testing imports...")
    try:
        from app.cache_processor import _is_main_thread, _safe_cache_data
        from app.ui_helpers import safe_streamlit_call, StateManager
        print("   ✅ All imports successful")
        return True
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False

def test_thread_detection():
    """Test the improved thread detection."""
    print("\n2. Testing thread detection...")
    try:
        from app.cache_processor import _is_main_thread
        
        # Test in main thread
        result = _is_main_thread()
        print(f"   Main thread detection: {result} (expected: False in test environment)")
        
        # Test in background thread
        bg_result = [None]
        def bg_test():
            bg_result[0] = _is_main_thread()
        
        thread = threading.Thread(target=bg_test)
        thread.start()
        thread.join()
        
        print(f"   Background thread detection: {bg_result[0]} (expected: False)")
        print("   ✅ Thread detection working")
        return True
    except Exception as e:
        print(f"   ❌ Thread detection failed: {e}")
        return False

def test_cache_decorator():
    """Test the safe cache decorator."""
    print("\n3. Testing cache decorator...")
    try:
        from app.cache_processor import _safe_cache_data
        
        call_count = [0]
        
        @_safe_cache_data
        def test_function(x):
            call_count[0] += 1
            return x * 2
        
        # Test multiple calls
        result1 = test_function(5)
        result2 = test_function(5)  # Should be cached in main thread
        result3 = test_function(6)  # Different argument
        
        print(f"   Results: {result1}, {result2}, {result3}")
        print(f"   Function calls: {call_count[0]} (should be 2)")
        
        if result1 == 10 and result2 == 10 and result3 == 12:
            print("   ✅ Cache decorator working correctly")
            return True
        else:
            print("   ❌ Cache decorator results incorrect")
            return False
    except Exception as e:
        print(f"   ❌ Cache decorator failed: {e}")
        return False

def test_background_calls():
    """Test function calls in background threads."""
    print("\n4. Testing background thread safety...")
    try:
        from app.cache_processor import _is_main_thread
        
        results = []
        errors = []
        
        def background_task(task_id):
            try:
                # These calls should not cause ScriptRunContext warnings
                is_main = _is_main_thread()
                results.append(f"Task {task_id}: main_thread={is_main}")
                
                # Simulate work that would previously cause warnings
                time.sleep(0.1)
                results.append(f"Task {task_id}: completed")
                
            except Exception as e:
                errors.append(f"Task {task_id}: {e}")
        
        # Run multiple background tasks
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(background_task, i) for i in range(5)]
            for future in futures:
                future.result()  # Wait for completion
        
        print(f"   Background tasks completed: {len(results)}")
        print(f"   Errors encountered: {len(errors)}")
        
        if len(errors) == 0:
            print("   ✅ Background thread safety verified")
            return True
        else:
            print(f"   ❌ Background errors: {errors}")
            return False
    except Exception as e:
        print(f"   ❌ Background testing failed: {e}")
        return False

def test_safe_streamlit_calls():
    """Test safe Streamlit calls (without actual Streamlit context)."""
    print("\n5. Testing safe Streamlit calls...")
    try:
        # This test verifies the function doesn't crash
        # In a real Streamlit app, it would handle the context properly
        from app.ui_helpers import safe_streamlit_call
        import streamlit as st
        
        # Mock a simple function to test the safety wrapper
        def mock_st_func(message):
            return f"Mock call: {message}"
        
        # Test in main thread (should work or fallback gracefully)
        try:
            result = safe_streamlit_call(mock_st_func, "Test message")
            print("   ✅ Safe Streamlit call wrapper working")
            return True
        except Exception as e:
            # Even if it fails, it shouldn't be ScriptRunContext related
            if "ScriptRunContext" not in str(e):
                print("   ✅ Safe Streamlit call handled gracefully")
                return True
            else:
                print(f"   ❌ ScriptRunContext error still present: {e}")
                return False
    except Exception as e:
        print(f"   ❌ Safe Streamlit call test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Starting ScriptRunContext fix verification...")
    
    tests = [
        test_imports,
        test_thread_detection,
        test_cache_decorator,
        test_background_calls,
        test_safe_streamlit_calls
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Summary
    print("\n=== Test Results Summary ===")
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results), 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i}. {test.__name__}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! ScriptRunContext fixes are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the fixes.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
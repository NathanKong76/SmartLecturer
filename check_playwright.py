#!/usr/bin/env python3
"""
检查Playwright是否已安装
"""

try:
    import playwright
    print("✅ Playwright已安装")
except ImportError:
    print("❌ Playwright未安装")

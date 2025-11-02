#!/usr/bin/env python3
"""
检查Playwright Chromium是否已安装
"""

try:
    from playwright.sync_api import sync_playwright
    print("✅ Playwright sync_api可用")

    # 尝试启动Chromium
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        print("✅ Chromium浏览器可用")
        browser.close()

except Exception as e:
    print(f"❌ Chromium不可用: {e}")
    print("需要运行: python -m playwright install chromium")

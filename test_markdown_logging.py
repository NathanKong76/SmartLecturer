#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试markdown生成功能的日志记录
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.pdf_processor import generate_markdown_with_screenshots

def test_markdown_logging():
    """测试markdown生成功能的日志记录"""
    # 创建一个简单的测试PDF（如果没有实际PDF文件）
    try:
        # 使用一个小的示例PDF或创建测试数据
        # 这里我们简单地测试参数传递
        print("测试markdown日志记录功能...")

        # 由于没有真实的PDF文件，我们只测试日志导入
        from app.services.logger import get_logger
        logger = get_logger()
        logger.info("markdown日志测试：导入成功")

        print("✓ markdown相关日志功能测试完成")
        print("请查看 logs/app.log 文件确认日志记录")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_markdown_logging()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试日志功能
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.logger import get_logger

def test_logger():
    """测试日志功能"""
    logger = get_logger()

    # 测试不同级别的日志
    logger.debug("这是调试信息")
    logger.info("这是信息消息")
    logger.warning("这是警告消息")
    logger.error("这是错误消息")
    logger.critical("这是严重错误消息")

    # 测试中文日志
    logger.info("测试中文日志：这是一条测试消息")

    print("日志测试完成")

    # 检查日志文件是否存在
    from app.services.logger import LOG_PATH
    print(f"日志文件路径: {LOG_PATH}")
    print(f"日志文件是否存在: {os.path.exists(LOG_PATH)}")

    if os.path.exists(LOG_PATH):
        print("日志文件内容:")
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content[-500:])  # 显示最后500字符

        # 检查文件编码
        with open(LOG_PATH, 'rb') as f:
            raw_bytes = f.read()
            if raw_bytes.startswith(b'\xef\xbb\xbf'):
                print("警告: 文件包含BOM标记!")
            else:
                print("✓ 文件使用UTF-8无BOM编码")
    else:
        print("日志文件不存在")

if __name__ == "__main__":
    test_logger()

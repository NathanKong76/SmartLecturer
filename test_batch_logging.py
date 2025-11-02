#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试批量JSON处理日志记录
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_batch_recompose_logging():
    """测试批量重新合成函数的日志记录"""
    try:
        # 模拟调用batch_recompose_from_json函数
        from app.services import pdf_processor

        # 创建空的PDF和JSON数据列表来触发日志
        pdf_files = []
        json_files = []

        print("测试日志记录：批量重新合成PDF")
        print("开始调用 batch_recompose_from_json 函数...")

        # 调用函数，应该会触发日志记录
        result = pdf_processor.batch_recompose_from_json(
            pdf_files,
            json_files,
            right_ratio=0.4,
            font_size=20,
            font_path=None,
            render_mode="text",
            line_spacing=1.2,
            column_padding=10
        )

        print("函数调用完成")
        print("✓ 批量处理日志测试完成")
        print("请查看 logs/app.log 文件确认批量处理日志记录")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_batch_recompose_logging()

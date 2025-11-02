#!/usr/bin/env python3
"""
调试批量JSON重新生成PDF功能，找出卡住的原因
"""
import sys
import os
import json
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services import pdf_processor

def test_batch_json_step_by_step(pdf_path=None, json_path=None):
    """逐步调试批量JSON处理"""
    print("🎯 开始逐步调试批量JSON处理...\n")

    # 如果没有提供路径，使用测试文件或存在的文件
    if not pdf_path:
        # 尝试使用test_3column_layout.py生成的测试PDF（如果存在）
        pdf_path = "test_3column_layout.pdf"
        if not os.path.exists(pdf_path):
            print("❌ 测试PDF文件不存在，请先运行test_3column_layout.py生成测试文件")
            return False

    if not json_path:
        # 尝试使用上一个explanations.json文件
        json_path = "../../Downloads/explanations.json"
        if not os.path.exists(json_path):
            print("❌ 测试JSON文件不存在，请提供有效的JSON文件路径")
            return False

    print("📁 准备处理文件：")
    print(f"  PDF: {pdf_path}")
    print(f"  JSON: {json_path}")
    print()

    # Step 1: 检查文件是否存在
    print("Step 1: 检查文件是否存在...")
    if not os.path.exists(pdf_path):
        print(f"❌ PDF文件不存在: {pdf_path}")
        return False
    if not os.path.exists(json_path):
        print(f"❌ JSON文件不存在: {json_path}")
        return False
    print("✅ 文件存在")
    print()

    # Step 2: 读取PDF文件
    print("Step 2: 读取PDF文件...")
    try:
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        print(f"✅ PDF文件读取成功，大小: {len(pdf_bytes)} bytes")
    except Exception as e:
        print(f"❌ PDF文件读取失败: {e}")
        return False
    print()

    # Step 3: 读取并解析JSON文件
    print("Step 3: 读取并解析JSON文件...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        print(f"✅ JSON文件解析成功，包含 {len(json_data)} 页讲解")

        # 验证JSON内容
        for page_num, content in list(json_data.items())[:2]:  # 只显示前2页
            content_preview = str(content)[:100] + "..." if len(str(content)) > 100 else str(content)
            print(f"  页 {page_num}: {content_preview}")

    except Exception as e:
        print(f"❌ JSON文件解析失败: {e}")
        return False
    print()

    # Step 4: 转换JSON格式
    print("Step 4: 转换JSON格式...")
    try:
        explanations = {int(k): str(v) for k, v in json_data.items()}
        print("✅ JSON格式转换成功")
    except Exception as e:
        print(f"❌ JSON格式转换失败: {e}")
        return False
    print()

    # Step 5: 验证PDF文件
    print("Step 5: 验证PDF文件...")
    try:
        is_valid, validation_error = pdf_processor.validate_pdf_file(pdf_bytes)
        if not is_valid:
            print(f"❌ PDF文件验证失败: {validation_error}")
            return False
        print("✅ PDF文件验证通过")
    except Exception as e:
        print(f"❌ PDF验证过程出错: {e}")
        return False
    print()

    # Step 6: 创建测试数据结构（模拟Streamlit的文件处理）
    print("Step 6: 创建批量处理数据结构...")
    try:
        # 使用与Streamlit相同的逻辑：pdf_name 的 basename + ".json"
        pdf_name = "Week 10-application layer 2 security .pdf"
        json_alias = os.path.splitext(pdf_name)[0] + ".json"

        pdf_files = [(pdf_name, pdf_bytes)]
        json_files = [(json_alias, json.dumps(explanations, ensure_ascii=False).encode('utf-8'))]

        print(f"📄 PDF文件名: {pdf_name}")
        print(f"📝 JSON文件名: {json_alias}")
        print("✅ 测试数据结构创建成功")
    except Exception as e:
        print(f"❌ 数据结构创建失败: {e}")
        return False
    print()

    # Step 7: 执行批量处理
    print("Step 7: 执行batch_recompose_from_json...")
    print("(这步可能耗时较长，如果卡住说明问题出现在这里)")
    start_time = time.time()

    try:
        results = pdf_processor.batch_recompose_from_json(
            pdf_files=pdf_files,
            json_files=json_files,
            right_ratio=0.48,
            font_size=20
        )

        elapsed = time.time() - start_time
        print(f"✅ 批量处理完成，耗时: {elapsed:.2f}秒")

        # 检查结果
        if not results:
            print("❌ 返回结果为空")
            return False

        filename = pdf_name  # 使用实际的PDF文件名
        if filename not in results:
            print(f"❌ 结果中没有文件: {filename}")
            print(f"  可用文件: {list(results.keys())}")
            return False

        result = results[filename]
        print(f"📋 处理文件: {filename}")
        if result.get("status") == "completed":
            pdf_bytes_result = result.get("pdf_bytes")
            if pdf_bytes_result:
                print(f"✅ PDF合成成功，大小: {len(pdf_bytes_result)} bytes")

                # 保存结果
                output_path = "debug_batch_result.pdf"
                with open(output_path, "wb") as f:
                    f.write(pdf_bytes_result)
                print(f"📁 结果保存到: {output_path}")

                return True
            else:
                print("❌ 合成完成但PDF数据为空")
                error = result.get("error", "未知错误")
                print(f"  错误信息: {error}")
                return False
        else:
            print(f"❌ 处理失败: {result.get('error', '未知错误')}")
            return False

    except Exception as e:
        elapsed = time.time() - start_time if start_time else 0
        print(f"❌ 批量处理异常 (耗时: {elapsed:.2f}秒): {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("="*60)
    print("🔍 批量JSON重新生成PDF - 详细调试")
    print("="*60)

    success = test_batch_json_step_by_step()

    print("\n" + "="*60)
    if success:
        print("🎉 调试完成！所有步骤都正常，请检查是否为Streamlit特定问题")
    else:
        print("⚠️  调试发现问题，请查看上述详细错误信息")
    print("="*60)

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

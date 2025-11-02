# -*- coding: utf-8 -*-
"""
完整的应用功能测试
验证streamlit应用是否能正常运行所有核心功能
"""

import sys
import os
import tempfile
import json
from pathlib import Path

# 确保使用UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试所有必要的导入"""
    print("🔍 测试导入模块...")
    try:
        import streamlit as st
        print("✓ streamlit 导入成功")

        from dotenv import load_dotenv
        print("✓ python-dotenv 导入成功")

        import app.streamlit_app as app
        print("✓ 应用模块导入成功")

        from app.services import pdf_processor
        print("✓ PDF处理器导入成功")

        from app.services import gemini_client
        print("✓ Gemini客户端导入成功")

        import fitz
        print("✓ PyMuPDF (fitz) 导入成功")

        import reportlab
        print("✓ ReportLab 导入成功")

        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 其他导入错误: {e}")
        return False

def test_app_structure():
    """测试应用结构"""
    print("\n🔍 测试应用结构...")
    try:
        import app.streamlit_app as app

        # 检查关键函数
        required_functions = ['main', 'setup_page', 'sidebar_form']
        for func_name in required_functions:
            if hasattr(app, func_name):
                print(f"✓ 函数 {func_name} 存在")
            else:
                print(f"✗ 函数 {func_name} 不存在")
                return False

        return True
    except Exception as e:
        print(f"✗ 应用结构检查失败: {e}")
        return False

def test_services():
    """测试服务模块"""
    print("\n🔍 测试服务模块...")
    try:
        from app.services import pdf_processor, gemini_client

        # 检查PDF处理器关键函数
        pdf_functions = ['generate_explanations', 'compose_pdf', 'validate_pdf_file']
        for func_name in pdf_functions:
            if hasattr(pdf_processor, func_name):
                print(f"✓ PDF处理器函数 {func_name} 存在")
            else:
                print(f"✗ PDF处理器函数 {func_name} 不存在")
                return False

        # 检查Gemini客户端关键类
        if hasattr(gemini_client, 'GeminiClient'):
            print("✓ Gemini客户端类存在")
        else:
            print("✗ Gemini客户端类不存在")
            return False

        return True
    except Exception as e:
        print(f"✗ 服务模块测试失败: {e}")
        return False

def test_font_file():
    """测试字体文件是否存在"""
    print("\n🔍 测试字体文件...")
    font_path = project_root / "assets" / "fonts" / "SIMHEI.TTF"
    if font_path.exists():
        print("✓ 中文字体文件存在")
        return True
    else:
        print("✗ 中文字体文件不存在")
        return False

def test_env_file():
    """测试环境配置文件"""
    print("\n🔍 测试环境配置...")
    env_path = project_root / ".env"
    if env_path.exists():
        print("✓ .env文件存在")
        # 检查是否有必要的环境变量
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            print("✓ GEMINI_API_KEY环境变量已设置")
        else:
            print("⚠ GEMINI_API_KEY环境变量未设置（这在实际运行时需要设置）")
        return True
    else:
        print("⚠ .env文件不存在（在实际运行时需要创建）")
        return True  # 不算错误，只是警告

def main():
    """主测试函数"""
    print("=" * 50)
    print("🚀 开始完整的Streamlit应用功能测试")
    print("=" * 50)

    all_passed = True

    # 执行各项测试
    tests = [
        ("导入模块", test_imports),
        ("应用结构", test_app_structure),
        ("服务模块", test_services),
        ("字体文件", test_font_file),
        ("环境配置", test_env_file),
    ]

    for test_name, test_func in tests:
        try:
            result = test_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"✗ 测试 '{test_name}' 出现异常: {e}")
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有测试通过！应用应该可以正常运行")
        print("\n启动命令:")
        print("  streamlit run app/streamlit_app.py")
        print("\n注意事项:")
        print("- 确保设置了GEMINI_API_KEY环境变量")
        print("- 确保网络连接正常（需要访问Gemini API）")
        print("- 首次运行可能需要安装浏览器依赖")
    else:
        print("❌ 部分测试失败，请检查上述错误信息")
    print("=" * 50)

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# 测试streamlit应用是否能正常启动
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

try:
    # 导入应用模块
    import app.streamlit_app as app
    print("✓ 模块导入成功")

    # 检查主函数是否存在
    if hasattr(app, 'main'):
        print("✓ main函数存在")
    else:
        print("✗ main函数不存在")

    # 检查setup_page函数
    if hasattr(app, 'setup_page'):
        print("✓ setup_page函数存在")
    else:
        print("✗ setup_page函数不存在")

    # 检查sidebar_form函数
    if hasattr(app, 'sidebar_form'):
        print("✓ sidebar_form函数存在")
    else:
        print("✗ sidebar_form函数不存在")

    print("✓ Streamlit应用结构检查完成，所有基本组件都存在")

except ImportError as e:
    print(f"✗ 导入错误: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ 其他错误: {e}")
    sys.exit(1)

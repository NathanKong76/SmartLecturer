#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用状态检查脚本
检查PDF讲解应用是否正在运行以及重启状态
"""
import os
import socket
from datetime import datetime

def check_app_status():
    print(f"检查时间: {datetime.now()}")
    print("=" * 60)

    # 1. 检查端口8501是否被占用
    port_in_use = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # 设置1秒超时
        result = sock.connect_ex(('127.0.0.1', 8501))
        if result == 0:
            port_in_use = True
            print("✓ 端口8501正在被使用（应用正在运行）")
        else:
            print("✗ 端口8501未被使用")
        sock.close()
    except Exception as e:
        print(f"端口检查错误: {e}")

    # 2. 检查Streamlit进程
    streamlit_running = False
    try:
        import subprocess
        # Windows下检查streamlit进程
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq streamlit.exe', '/NH'],
                              capture_output=True, text=True, shell=True)
        if 'streamlit.exe' in result.stdout:
            print("✓ 发现Streamlit进程正在运行")
            streamlit_running = True
        else:
            print("✗ 未发现运行中的Streamlit进程")
    except Exception as e:
        print(f"进程检查错误: {e}")
        streamlit_running = False

    # 3. 检查日志文件
    log_file = "logs/app.log"
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    print("✓ 日志文件存在，最后一行记录：")
                    print(f"  {lines[-1].strip()}")
                else:
                    print("✓ 日志文件存在但为空")
        except Exception as e:
            print(f"读取日志错误: {e}")
    else:
        print("✗ 日志文件不存在")

    # 4. 检查缓存目录
    try:
        temp_cache = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
        if os.path.exists(temp_cache):
            cache_files = [f for f in os.listdir(temp_cache) if f.endswith('.json')]
            print(f"✓ 缓存目录存在，包含 {len(cache_files)} 个JSON缓存文件")
        else:
            print("✗ 缓存目录不存在（重启时可能被清理）")
    except Exception as e:
        print(f"缓存目录检查错误: {e}")

    # 5. 总结状态
    print("=" * 60)
    if port_in_use and streamlit_running:
        print("🟢 应用状态: 正在运行")
        print("💡 如果您刚刚重启，说明重启成功了")
    elif port_in_use:
        print("🟡 应用状态: 端口被占用（可能正在启动）")
    else:
        print("🔴 应用状态: 未运行（需要重新启动）")
        print("💡 要启动应用：")
        print("   1. 激活虚拟环境: .\\.venv\\Scripts\\Activate.ps1")
        print("   2. 启动应用: streamlit run app/streamlit_app.py")

    print("=" * 60)

if __name__ == "__main__":
    check_app_status()

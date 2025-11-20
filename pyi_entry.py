#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Entry point for PyInstaller bundled application
# This script is used when packaging with PyInstaller

import sys
import os
import subprocess
import platform

# Fix for importlib.metadata in PyInstaller
if getattr(sys, 'frozen', False):
    # Running as a bundled application
    # Patch importlib.metadata before importing streamlit
    import importlib.metadata
    import importlib.util
    
    # Create a mock distribution finder for missing packages
    class PyInstallerMetadataFinder:
        def __init__(self):
            self._distributions = {}
        
        def find_distributions(self, name=None):
            # Return empty list if not found
            return []
        
        def find_distribution(self, name):
            # Return None if not found, which will be handled gracefully
            return None
    
    # Try to patch importlib.metadata to handle missing distributions
    try:
        # Use pkg_resources as fallback
        import pkg_resources
        pkg_resources.working_set.add_entry(sys._MEIPASS)
        
        # Monkey patch importlib.metadata.version to use pkg_resources
        _original_version = importlib.metadata.version
        def _patched_version(name):
            try:
                return _original_version(name)
            except importlib.metadata.PackageNotFoundError:
                try:
                    return pkg_resources.get_distribution(name).version
                except:
                    # Return a default version if both fail
                    return "unknown"
        
        importlib.metadata.version = _patched_version
        
        # Patch distribution lookup
        _original_distribution = importlib.metadata.distribution
        def _patched_distribution(name):
            try:
                return _original_distribution(name)
            except importlib.metadata.PackageNotFoundError:
                try:
                    dist = pkg_resources.get_distribution(name)
                    # Create a minimal Distribution object
                    class MinimalDistribution:
                        def __init__(self, name, version):
                            self.name = name
                            self.version = version
                        def read_text(self, filename):
                            return None
                    return MinimalDistribution(name, dist.version)
                except:
                    raise importlib.metadata.PackageNotFoundError(name)
        
        importlib.metadata.distribution = _patched_distribution
        
    except Exception as e:
        # If patching fails, continue anyway
        pass
    
    # Add the bundled app directory to sys.path
    base_path = sys._MEIPASS
    app_path = os.path.join(base_path, 'app')
    if os.path.exists(app_path):
        sys.path.insert(0, app_path)
    
    # Set project root to the directory containing the executable
    project_root = os.path.dirname(sys.executable)
else:
    # Running as a normal Python script
    project_root = os.path.dirname(os.path.abspath(__file__))

# Ensure project root is in sys.path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Change to project root directory
os.chdir(project_root)


def check_pdf2htmlex_installed():
    """
    检查 pdf2htmlEX 是否已安装（支持原生和 WSL）
    
    Returns:
        (is_installed, version_or_error)
    """
    # 方法 1: 尝试原生命令
    try:
        result = subprocess.run(
            ['pdf2htmlEX', '--version'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            return True, f"Native: {version}"
    except FileNotFoundError:
        pass
    except Exception:
        pass
    
    # 方法 2: 在 Windows 上尝试 WSL
    if platform.system() == 'Windows':
        try:
            result = subprocess.run(
                ['wsl', 'pdf2htmlEX', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                return True, f"WSL: {version}"
        except FileNotFoundError:
            pass
        except Exception:
            pass
    
    return False, "pdf2htmlEX 未安装"


def install_pdf2htmlex_wsl(project_root):
    """
    自动运行 install-pdf2htmlex-wsl.ps1 脚本安装 pdf2htmlEX
    
    Args:
        project_root: 项目根目录路径
        
    Returns:
        bool: 安装是否成功
    """
    if platform.system() != 'Windows':
        print("警告: pdf2htmlEX 自动安装仅在 Windows 上支持（通过 WSL）")
        return False
    
    # 查找安装脚本
    # 优先级：1. 打包路径中的脚本 2. 项目根目录中的脚本
    script_path = None
    
    if getattr(sys, 'frozen', False):
        # 在打包的 exe 中，脚本应该在 _MEIPASS/scripts 目录
        script_path = os.path.join(sys._MEIPASS, 'scripts', 'install-pdf2htmlex-wsl.ps1')
        if not os.path.exists(script_path):
            script_path = None
    
    # 如果打包路径中没找到，尝试项目根目录
    if not script_path or not os.path.exists(script_path):
        script_path = os.path.join(project_root, 'scripts', 'install-pdf2htmlex-wsl.ps1')
    
    if not os.path.exists(script_path):
        print(f"警告: 未找到安装脚本")
        print(f"  尝试路径 1: {os.path.join(sys._MEIPASS if getattr(sys, 'frozen', False) else '', 'scripts', 'install-pdf2htmlex-wsl.ps1')}")
        print(f"  尝试路径 2: {os.path.join(project_root, 'scripts', 'install-pdf2htmlex-wsl.ps1')}")
        print("请手动运行: scripts\\install-pdf2htmlex-wsl.ps1")
        return False
    
    try:
        print("=" * 50)
        print("检测到 pdf2htmlEX 未安装，正在自动安装...")
        print("=" * 50)
        print(f"安装脚本: {script_path}")
        print()
        print("注意: 安装可能需要几分钟时间，并可能需要管理员权限")
        print("如果提示需要管理员权限，请以管理员身份运行此程序")
        print()
        
        # 使用 PowerShell 执行脚本
        # 使用 -SkipWSLCheck 参数，因为 WSL 检查需要管理员权限
        # 如果 WSL 未安装，脚本会提示用户
        ps_command = f'powershell.exe -ExecutionPolicy Bypass -File "{script_path}" -SkipWSLCheck'
        
        print("正在执行安装脚本...")
        result = subprocess.run(
            ps_command,
            shell=True,
            capture_output=False,  # 显示输出给用户
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0:
            print()
            print("=" * 50)
            print("安装完成！")
            print("=" * 50)
            return True
        else:
            print()
            print("=" * 50)
            print("安装可能未完全成功，请检查上面的输出")
            print("=" * 50)
            # 即使返回码不为 0，也可能部分成功，所以再次检查
            is_installed, _ = check_pdf2htmlex_installed()
            return is_installed
            
    except Exception as e:
        print(f"执行安装脚本时出错: {e}")
        print(f"请手动运行: {script_path}")
        return False


# Import and run streamlit app
if __name__ == '__main__':
    # Set environment variables (only non-conflicting ones)
    if getattr(sys, 'frozen', False):
        # Disable usage stats
        os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
        # 禁用开发模式，这样才能使用 server.port 参数
        os.environ['STREAMLIT_GLOBAL_DEVELOPMENT_MODE'] = 'false'
        # 设置服务器端口，确保端口配置一致
        os.environ['STREAMLIT_SERVER_PORT'] = '8501'
        # 设置服务器地址
        os.environ['STREAMLIT_SERVER_ADDRESS'] = 'localhost'
    
    # Print startup info
    try:
        print("=" * 50)
        print("PDF 讲解流 - 正在启动...")
        print("=" * 50)
        print(f"项目根目录: {project_root}")
        if getattr(sys, 'frozen', False):
            print(f"打包路径: {sys._MEIPASS}")
        print("=" * 50)
        print()
    except:
        pass  # Ignore print errors if stdout is not available
    
    # 检查并自动安装 pdf2htmlEX（如果需要）
    try:
        is_installed, version_info = check_pdf2htmlex_installed()
        if not is_installed:
            print("=" * 50)
            print("pdf2htmlEX 检查")
            print("=" * 50)
            print("pdf2htmlEX 未安装")
            print("此工具用于 'HTML-pdf2htmlEX版' 输出模式")
            print()
            
            # 仅在 Windows 上尝试自动安装
            if platform.system() == 'Windows':
                # 检查环境变量，允许跳过自动安装提示
                skip_auto_install = os.environ.get('SKIP_PDF2HTMLEX_AUTO_INSTALL', '').lower() == 'true'
                
                if skip_auto_install:
                    print("已跳过自动安装（环境变量 SKIP_PDF2HTMLEX_AUTO_INSTALL=true）")
                    print("如需使用 'HTML-pdf2htmlEX版' 模式，请手动安装 pdf2htmlEX")
                else:
                    user_input = None
                    try:
                        print("是否现在自动安装 pdf2htmlEX？(Y/N，默认: Y)")
                        print("提示: 安装需要 WSL，如果未安装 WSL 可能需要管理员权限")
                        user_input = input("请输入: ").strip().upper()
                    except:
                        # 如果无法获取输入（例如在非交互式环境中），默认尝试安装
                        user_input = 'Y'
                    
                    if not user_input or user_input == 'Y':
                        success = install_pdf2htmlex_wsl(project_root)
                        if success:
                            print()
                            print("pdf2htmlEX 安装成功！")
                        else:
                            print()
                            print("自动安装未成功，您可以稍后手动运行安装脚本")
                            script_path_hint = os.path.join(project_root, 'scripts', 'install-pdf2htmlex-wsl.ps1')
                            if getattr(sys, 'frozen', False):
                                script_path_hint = os.path.join(sys._MEIPASS, 'scripts', 'install-pdf2htmlex-wsl.ps1')
                            print(f"脚本路径: {script_path_hint}")
                    else:
                        print("已跳过自动安装")
                        print("如需使用 'HTML-pdf2htmlEX版' 模式，请手动安装 pdf2htmlEX")
            else:
                print("在非 Windows 系统上，请手动安装 pdf2htmlEX")
                print("Linux: sudo apt-get install pdf2htmlex")
                print("macOS: brew install pdf2htmlex")
            
            print()
        else:
            # 已安装，静默跳过（可选：显示版本信息）
            pass
    except Exception as e:
        # 检查失败不影响主程序启动
        try:
            print(f"检查 pdf2htmlEX 时出错（不影响主程序）: {e}")
        except:
            pass
    
    try:
        import streamlit.web.cli as stcli
        
        # Get the path to streamlit_app.py
        if getattr(sys, 'frozen', False):
            # In PyInstaller bundle
            app_file = os.path.join(sys._MEIPASS, 'app', 'streamlit_app.py')
        else:
            # Normal execution
            app_file = os.path.join(project_root, 'app', 'streamlit_app.py')
        
        # 转换为绝对路径，确保 Streamlit 能正确找到文件
        app_file = os.path.abspath(app_file)
        
        if not os.path.exists(app_file):
            error_msg = f"错误: 未找到应用文件: {app_file}"
            try:
                print(error_msg)
            except:
                pass
            try:
                input("按 Enter 键退出...")
            except:
                pass  # stdin not available
            sys.exit(1)
        
        try:
            print(f"应用文件: {app_file}")
            print(f"应用文件存在: {os.path.exists(app_file)}")
            print("正在启动 Streamlit...")
            print()
            print("=" * 50)
            print("提示: 应用将在以下地址启动:")
            print("  http://localhost:8501")
            print("=" * 50)
            print()
        except:
            pass
        
        # 确保应用文件所在目录在 sys.path 中，以便 Streamlit 能正确解析导入
        # 但保持工作目录在项目根目录，这样相对路径引用才能正常工作
        app_dir = os.path.dirname(app_file)
        parent_dir = os.path.dirname(app_dir)  # app 目录的父目录（项目根目录）
        
        # 确保项目根目录在 sys.path 中
        if parent_dir and parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # 确保 app 目录在 sys.path 中
        if app_dir and app_dir not in sys.path:
            sys.path.insert(0, app_dir)
        
        # 保持工作目录在项目根目录（已在前面设置）
        # 这样 Streamlit 和应用的相对路径引用才能正常工作
        
        # Run streamlit with proper arguments
        # 明确设置端口为 8501，确保端口配置一致
        # 使用绝对路径确保 Streamlit 能正确找到应用文件
        # 注意：必须先禁用开发模式（通过环境变量），才能使用 server.port 参数
        sys.argv = [
            'streamlit',
            'run',
            app_file,
            '--server.address=localhost',
            '--server.port=8501',
            '--server.headless=true',  # 禁用自动打开浏览器
            '--global.developmentMode=false',  # 明确禁用开发模式
            '--server.enableCORS=false',  # 禁用 CORS（如果需要）
            '--server.enableXsrfProtection=false'  # 禁用 XSRF 保护以避免与 CORS 冲突
        ]
        
        # 打印最终配置信息用于调试
        try:
            print(f"最终配置:")
            print(f"  工作目录: {os.getcwd()}")
            print(f"  应用文件: {app_file}")
            print(f"  应用文件存在: {os.path.exists(app_file)}")
            print(f"  sys.path 前3项: {sys.path[:3]}")
            print()
        except:
            pass
        
        stcli.main()
        
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        try:
            print("\n应用已停止")
        except:
            pass
        sys.exit(0)
    except Exception as e:
        error_msg = f"启动失败: {e}"
        try:
            print("=" * 50)
            print("错误详情:")
            print("=" * 50)
            print(error_msg)
            print()
            import traceback
            print("完整错误堆栈:")
            print("-" * 50)
            traceback.print_exc()
            print("=" * 50)
            print()
            print("提示:")
            print("1. 检查是否所有依赖都已正确安装")
            print("2. 检查 PyInstaller 打包是否完整")
            print("3. 检查应用文件路径是否正确")
            if getattr(sys, 'frozen', False):
                print(f"4. 打包路径: {sys._MEIPASS}")
                print(f"5. 可执行文件路径: {sys.executable}")
            print("=" * 50)
        except Exception as print_error:
            # 如果打印也失败，尝试写入文件
            try:
                error_log = os.path.join(os.path.dirname(sys.executable), "error.log")
                with open(error_log, "w", encoding="utf-8") as f:
                    f.write(f"启动失败: {e}\n")
                    f.write(f"打印错误: {print_error}\n")
                    import traceback
                    traceback.print_exc(file=f)
                print(f"错误信息已保存到: {error_log}")
            except:
                pass
        try:
            input("\n按 Enter 键退出...")
        except:
            pass  # stdin not available
        sys.exit(1)


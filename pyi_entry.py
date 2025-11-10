#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Entry point for PyInstaller bundled application
# This script is used when packaging with PyInstaller

import sys
import os

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

# Import and run streamlit app
if __name__ == '__main__':
    # Set environment variables (only non-conflicting ones)
    if getattr(sys, 'frozen', False):
        # Disable usage stats
        os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
        # Don't set server.port here as it conflicts with developmentMode
    
    # Print startup info
    try:
        print("=" * 50)
        print("智讲 / PDF-Lecture-AI - 正在启动...")
        print("=" * 50)
        print(f"项目根目录: {project_root}")
        if getattr(sys, 'frozen', False):
            print(f"打包路径: {sys._MEIPASS}")
        print("=" * 50)
        print()
    except:
        pass  # Ignore print errors if stdout is not available
    
    try:
        import streamlit.web.cli as stcli
        
        # Get the path to streamlit_app.py
        if getattr(sys, 'frozen', False):
            # In PyInstaller bundle
            app_file = os.path.join(sys._MEIPASS, 'app', 'streamlit_app.py')
        else:
            # Normal execution
            app_file = os.path.join(project_root, 'app', 'streamlit_app.py')
        
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
            print("正在启动 Streamlit...")
            print()
        except:
            pass
        
        # Run streamlit with proper arguments
        # Use --server.port and --server.address via command line args
        sys.argv = [
            'streamlit', 
            'run', 
            app_file,
            '--server.port=8501',
            '--server.address=localhost'
        ]
        
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
            print(error_msg)
            import traceback
            traceback.print_exc()
        except:
            pass
        try:
            input("按 Enter 键退出...")
        except:
            pass  # stdin not available
        sys.exit(1)


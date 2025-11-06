#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Entry point for PyInstaller bundled application
# This script is used when packaging with PyInstaller

import sys
import os

# Fix for importlib.metadata in PyInstaller
if getattr(sys, 'frozen', False):
    # Running as a bundled application
    import importlib.metadata
    
    # Patch importlib.metadata to work with PyInstaller
    try:
        # Try to set distribution paths
        import pkg_resources
        # Add the MEIPASS path to pkg_resources
        pkg_resources.working_set.add_entry(sys._MEIPASS)
    except:
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
    # Set environment variable to help Streamlit find its files
    if getattr(sys, 'frozen', False):
        os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
        os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    
    import streamlit.web.cli as stcli
    
    # Get the path to streamlit_app.py
    if getattr(sys, 'frozen', False):
        # In PyInstaller bundle
        app_file = os.path.join(sys._MEIPASS, 'app', 'streamlit_app.py')
    else:
        # Normal execution
        app_file = os.path.join(project_root, 'app', 'streamlit_app.py')
    
    # Run streamlit
    sys.argv = ['streamlit', 'run', app_file]
    stcli.main()


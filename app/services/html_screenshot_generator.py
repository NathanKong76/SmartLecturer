#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML Screenshot Generator
Generate single HTML file with PDF screenshots on left and markdown-rendered explanations on right
"""

import base64
import json
from typing import Dict, Optional, List
from .logger import get_logger

logger = get_logger()


class HTMLScreenshotGenerator:
    """Generate HTML screenshot view with scrollable PDF screenshots and column-layout explanations"""
    
    @staticmethod
    def _render_markdown_to_html(markdown_content: str) -> str:
        """
        Render markdown content to HTML
        
        Args:
            markdown_content: Markdown formatted text
            
        Returns:
            Rendered HTML string
        """
        if not markdown_content or not markdown_content.strip():
            return "<p>暂无讲解内容</p>"
        
        try:
            # Try using markdown library for rendering
            import markdown
            html_content = markdown.markdown(
                markdown_content,
                extensions=[
                    'fenced_code',  # Code block support
                    'tables',       # Table support
                    'nl2br',        # Auto line break
                    'sane_lists'    # Better list handling
                ]
            )
            return html_content
        except ImportError:
            # If markdown library not available, use simple text conversion
            html_content = markdown_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_content = html_content.replace('\n\n', '</p><p>').replace('\n', '<br>')
            return f"<p>{html_content}</p>"
        except Exception as e:
            # If rendering fails, return escaped original content
            logger.warning(f"Failed to render markdown: {e}")
            html_content = markdown_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_content = html_content.replace('\n\n', '</p><p>').replace('\n', '<br>')
            return f"<p>{html_content}</p>"
    
    @staticmethod
    def _generate_css_styles(
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2,
        column_count: int = 2,
        column_gap: int = 20,
        show_column_rule: bool = True
    ) -> str:
        """
        Generate CSS styles for HTML screenshot view
        
        Args:
            font_name: Font family name
            font_size: Font size in pt
            line_spacing: Line height multiplier
            column_count: Number of columns for explanation text
            column_gap: Gap between columns in px
            show_column_rule: Whether to show column separator line
            
        Returns:
            CSS string
        """
        column_rule = f"1px solid #ddd" if show_column_rule else "none"
        
        css = f"""
/* HTML Screenshot View Styles - Minimalist Breathing Layout */
:root {{
    --bg-color: #ffffff;
    --text-color: #1a1a1a;
    --accent-color: #0ea5e9;
    --accent-hover: #38bdf8;
    --border-color: #e5e5e5;
    --card-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    --hover-bg: rgba(14, 165, 233, 0.05);
    --code-bg: #f8f9fa;
    --font-size: {font_size}pt;
    --line-height: 1.8;
}}

body.dark-mode {{
    --bg-color: #0a0a0a;
    --text-color: #e5e5e5;
    --accent-color: #38bdf8;
    --accent-hover: #0ea5e9;
    --border-color: #262626;
    --card-shadow: 0 2px 8px rgba(255, 255, 255, 0.06);
    --hover-bg: rgba(56, 189, 248, 0.1);
    --code-bg: #1a1a1a;
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: '{font_name}', 'Microsoft YaHei', 'SimHei', sans-serif;
    font-size: var(--font-size);
    line-height: var(--line-height);
    color: var(--text-color);
    background-color: #f5f5f5;
    overflow: hidden;
    transition: background-color 0.3s ease, color 0.3s ease;
}}

.main-container {{
    display: flex;
    height: 100vh;
    width: 100vw;
}}

/* Left panel: PDF screenshots */
.screenshots-panel {{
    flex: 1;
    max-width: 50%;
    background: #2c3e50;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 5px;
    position: relative;
}}

.screenshots-panel::-webkit-scrollbar {{
    width: 12px;
}}

.screenshots-panel::-webkit-scrollbar-track {{
    background: #34495e;
}}

.screenshots-panel::-webkit-scrollbar-thumb {{
    background: #7f8c8d;
    border-radius: 6px;
}}

.screenshots-panel::-webkit-scrollbar-thumb:hover {{
    background: #95a5a6;
}}

.page-screenshot {{
    margin-bottom: 30px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    overflow: hidden;
    transition: all 0.3s ease;
    position: relative;
}}

.page-screenshot.active {{
    box-shadow: 0 8px 32px rgba(52, 152, 219, 0.6);
    transform: scale(1.02);
}}

.page-screenshot img {{
    width: 100%;
    height: auto;
    display: block;
}}

.page-number-badge {{
    position: absolute;
    top: 10px;
    left: 10px;
    background: rgba(52, 152, 219, 0.9);
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 12pt;
    z-index: 10;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}}

/* Right panel: Explanations */
.explanations-panel {{
    flex: 1;
    max-width: 50%;
    background: var(--bg-color);
    overflow-y: auto;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    transition: background-color 0.3s ease;
}}

.explanations-panel::-webkit-scrollbar {{
    width: 8px;
}}

.explanations-panel::-webkit-scrollbar-track {{
    background: transparent;
}}

.explanations-panel::-webkit-scrollbar-thumb {{
    background: var(--border-color);
    border-radius: 4px;
}}

.explanations-panel::-webkit-scrollbar-thumb:hover {{
    background: var(--accent-color);
}}

.explanation-header {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px 30px;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    position: sticky;
    top: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}}

.explanation-header h1 {{
    font-size: 24pt;
    font-weight: bold;
    margin: 0;
}}

.current-page-indicator {{
    font-size: 14pt;
    margin-top: 8px;
    opacity: 0.9;
}}

.theme-toggle {{
    position: absolute;
    right: 20px;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255, 255, 255, 0.2);
    border: none;
    color: white;
    font-size: 20pt;
    width: 45px;
    height: 45px;
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
}}

.theme-toggle:hover {{
    background: rgba(255, 255, 255, 0.3);
    transform: translateY(-50%) scale(1.1);
}}

.explanations-container {{
    flex: 1;
    position: relative;
}}

.explanation-item {{
    display: none;
    animation: fadeInUp 0.5s ease-out;
}}

.explanation-item.active {{
    display: block;
}}

.explanation-page-title {{
    font-size: 28pt;
    font-weight: bold;
    color: var(--text-color);
    margin-bottom: 60px;
    margin-top: 40px;
    padding-bottom: 15px;
    border-bottom: 2px solid var(--accent-color);
    max-width: 720px;
    margin-left: auto;
    margin-right: auto;
    transition: color 0.3s ease, border-color 0.3s ease;
}}

/* Single column centered layout for explanation content */
.explanation-content {{
    max-width: 720px;
    margin: 0 auto;
    padding: 0 40px 60px 40px;
    line-height: var(--line-height);
    text-align: justify;
    text-justify: inter-word;
}}

.explanation-content h1,
.explanation-content h2,
.explanation-content h3,
.explanation-content h4,
.explanation-content h5,
.explanation-content h6 {{
    color: var(--text-color);
    margin-top: 50px;
    margin-bottom: 25px;
    font-weight: 600;
    line-height: 1.3;
    transition: color 0.3s ease;
}}

.explanation-content h1 {{
    font-size: 28pt;
    border-bottom: 2px solid var(--accent-color);
    padding-bottom: 12px;
    margin-top: 60px;
}}

.explanation-content h2 {{
    font-size: 22pt;
    color: var(--accent-color);
}}

.explanation-content h3 {{
    font-size: 18pt;
    font-weight: 500;
}}

.explanation-content h4 {{
    font-size: 16pt;
    font-weight: 500;
}}

.explanation-content p {{
    margin-bottom: 40px;
}}

.explanation-content ul,
.explanation-content ol {{
    margin-left: 24px;
    margin-bottom: 35px;
    padding-left: 10px;
}}

.explanation-content li {{
    margin-bottom: 12px;
    line-height: 1.6;
}}

.explanation-content code {{
    background: var(--code-bg);
    padding: 3px 8px;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 14pt;
    color: var(--accent-color);
    transition: background-color 0.3s ease;
}}

.explanation-content pre {{
    background: var(--code-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 25px;
    overflow-x: auto;
    margin: 30px 0;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13pt;
    line-height: 1.6;
    box-shadow: var(--card-shadow);
    transition: all 0.3s ease;
}}

.explanation-content pre:hover {{
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}}

.explanation-content blockquote {{
    border-left: 4px solid var(--accent-color);
    padding-left: 25px;
    margin: 35px 0;
    font-style: italic;
    color: var(--text-color);
    opacity: 0.9;
    background: var(--hover-bg);
    padding: 20px 25px;
    border-radius: 0 8px 8px 0;
    transition: all 0.3s ease;
}}

.explanation-content blockquote:hover {{
    opacity: 1;
    padding-left: 30px;
}}

.explanation-content table {{
    width: 100%;
    border-collapse: collapse;
    margin: 35px 0;
    box-shadow: var(--card-shadow);
    border-radius: 8px;
    overflow: hidden;
}}

.explanation-content table th,
.explanation-content table td {{
    border: 1px solid var(--border-color);
    padding: 12px 16px;
    text-align: left;
    transition: background-color 0.3s ease;
}}

.explanation-content table th {{
    background: var(--accent-color);
    color: white;
    font-weight: bold;
    font-size: 15pt;
}}

.explanation-content table tr:nth-child(even) {{
    background: var(--hover-bg);
}}

.explanation-content table tr:hover {{
    background: var(--hover-bg);
}}

/* Animations */
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

@keyframes fadeInUp {{
    from {{ 
        opacity: 0; 
        transform: translateY(30px); 
    }}
    to {{ 
        opacity: 1; 
        transform: translateY(0); 
    }}
}}

/* Reading Progress Bar */
.reading-progress {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent-color), var(--accent-hover));
    width: 0%;
    transition: width 0.1s cubic-bezier(0.4, 0.0, 0.2, 1);
    z-index: 10001;
    box-shadow: 0 2px 4px rgba(14, 165, 233, 0.3);
}}

/* Font Controls Panel */
.font-controls {{
    position: fixed;
    bottom: 100px;
    right: 30px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    z-index: 1001;
    min-width: 220px;
    opacity: 0;
    transform: translateX(300px);
    transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}}

body.dark-mode .font-controls {{
    background: rgba(26, 26, 26, 0.95);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}}

.font-controls.visible {{
    opacity: 1;
    transform: translateX(0);
}}

.font-controls-toggle {{
    position: absolute;
    right: 75px;
    top: 50%;
    transform: translateY(-50%);
    width: 45px;
    height: 45px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.2);
    color: white;
    border: none;
    font-size: 18pt;
    cursor: pointer;
    backdrop-filter: blur(10px);
    z-index: 1001;
    transition: all 0.3s ease;
}}

.font-controls-toggle:hover {{
    transform: translateY(-50%) scale(1.1);
    background: rgba(255, 255, 255, 0.3);
}}

.font-control-group {{
    margin-bottom: 15px;
}}

.font-control-group:last-child {{
    margin-bottom: 0;
}}

.font-control-label {{
    display: block;
    margin-bottom: 8px;
    font-size: 12pt;
    font-weight: 600;
    color: var(--text-color);
}}

.font-control-slider {{
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: var(--border-color);
    outline: none;
    -webkit-appearance: none;
    appearance: none;
}}

.font-control-slider::-webkit-slider-thumb {{
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--accent-color);
    cursor: pointer;
    transition: all 0.2s ease;
}}

.font-control-slider::-webkit-slider-thumb:hover {{
    transform: scale(1.2);
    box-shadow: 0 2px 8px rgba(14, 165, 233, 0.4);
}}

.font-control-slider::-moz-range-thumb {{
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--accent-color);
    cursor: pointer;
    border: none;
    transition: all 0.2s ease;
}}

.font-control-slider::-moz-range-thumb:hover {{
    transform: scale(1.2);
    box-shadow: 0 2px 8px rgba(14, 165, 233, 0.4);
}}

.font-control-value {{
    display: inline-block;
    margin-left: 8px;
    font-size: 11pt;
    color: var(--accent-color);
    font-weight: bold;
}}

/* Navigation controls */
.nav-controls {{
    position: fixed;
    bottom: 30px;
    right: 30px;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 15px 20px;
    border-radius: 25px;
    display: flex;
    align-items: center;
    gap: 15px;
    z-index: 1000;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}}

.nav-btn {{
    background: #3498db;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 12pt;
    font-weight: bold;
    transition: all 0.3s ease;
}}

.nav-btn:hover:not(:disabled) {{
    background: #2980b9;
    transform: translateY(-2px);
}}

.nav-btn:disabled {{
    background: #7f8c8d;
    cursor: not-allowed;
    opacity: 0.5;
}}

.page-info {{
    font-weight: bold;
    font-size: 14pt;
    min-width: 80px;
    text-align: center;
}}

/* Loading indicator */
.loading {{
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: rgba(255, 255, 255, 0.95);
    padding: 30px 50px;
    border-radius: 15px;
    text-align: center;
    z-index: 10000;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}}

.loading::after {{
    content: '';
    display: block;
    width: 40px;
    height: 40px;
    margin: 15px auto 0;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}}

@keyframes spin {{
    0% {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
}}

/* Responsive design */
@media (max-width: 1024px) {{
    .main-container {{
        flex-direction: column;
    }}
    
    .screenshots-panel,
    .explanations-panel {{
        max-width: 100%;
        height: 50vh;
    }}
    
    .explanation-content {{
        padding: 0 30px 50px 30px;
    }}
    
    .font-controls {{
        right: 20px;
        bottom: 90px;
        min-width: 200px;
    }}
    
    .font-controls-toggle {{
        right: 65px;
        width: 40px;
        height: 40px;
        font-size: 16pt;
    }}
}}

@media (max-width: 768px) {{
    :root {{
        --font-size: 14pt;
        --line-height: 1.7;
    }}
    
    .explanation-header {{
        padding: 15px 20px;
    }}
    
    .explanation-header h1 {{
        font-size: 18pt;
    }}
    
    .theme-toggle {{
        width: 40px;
        height: 40px;
        font-size: 18pt;
    }}
    
    .explanation-page-title {{
        font-size: 22pt;
        margin-bottom: 40px;
        margin-top: 30px;
    }}
    
    .explanation-content {{
        max-width: 100%;
        padding: 0 20px 40px 20px;
    }}
    
    .explanation-content h1 {{
        font-size: 22pt;
        margin-top: 40px;
    }}
    
    .explanation-content h2 {{
        font-size: 18pt;
    }}
    
    .explanation-content h3 {{
        font-size: 16pt;
    }}
    
    .explanation-content p {{
        margin-bottom: 30px;
    }}
    
    .nav-controls {{
        bottom: 15px;
        right: 15px;
        padding: 10px 15px;
        gap: 10px;
    }}
    
    .font-controls {{
        right: 10px;
        bottom: 80px;
        min-width: 180px;
        padding: 15px;
    }}
    
    .font-controls-toggle {{
        right: 55px;
        width: 35px;
        height: 35px;
        font-size: 14pt;
    }}
}}

/* Print styles */
@media print {{
    .nav-controls,
    .loading,
    .reading-progress,
    .theme-toggle,
    .font-controls,
    .font-controls-toggle {{
        display: none !important;
    }}
    
    .main-container {{
        flex-direction: column;
    }}
    
    .screenshots-panel,
    .explanations-panel {{
        max-width: 100%;
        overflow: visible;
    }}
    
    .explanation-content {{
        max-width: 100%;
        padding: 20px;
    }}
}}
"""
        return css
    
    @staticmethod
    def _generate_javascript(total_pages: int) -> str:
        """
        Generate JavaScript for scroll synchronization
        
        Args:
            total_pages: Total number of pages
            
        Returns:
            JavaScript string
        """
        js = f"""
// HTML Screenshot View Synchronization - Enhanced with Theme & Font Controls
class ScreenshotExplanationSync {{
    constructor() {{
        this.currentPage = 1;
        this.totalPages = {total_pages};
        this.observer = null;
        this.fontControlsVisible = false;
        this.pageScrollPositions = {{}}; // Store scroll position for each page
        this.init();
    }}
    
    init() {{
        // Remove loading indicator
        const loading = document.querySelector('.loading');
        if (loading) {{
            setTimeout(() => loading.remove(), 500);
        }}
        
        // Load saved theme and font settings
        this.loadSettings();
        
        // Setup intersection observer
        this.setupObserver();
        
        // Setup navigation controls
        this.setupControls();
        
        // Setup reading progress bar
        this.setupReadingProgress();
        
        // Setup theme toggle
        this.setupThemeToggle();
        
        // Setup font controls
        this.setupFontControls();
        
        // Show first page
        this.showExplanation(1);
    }}
    
    loadSettings() {{
        // Load theme preference
        const savedTheme = localStorage.getItem('html-screenshot-theme');
        if (savedTheme === 'dark') {{
            document.body.classList.add('dark-mode');
        }}
        
        // Load font settings
        const savedFontSize = localStorage.getItem('html-screenshot-font-size');
        const savedLineHeight = localStorage.getItem('html-screenshot-line-height');
        
        if (savedFontSize) {{
            document.documentElement.style.setProperty('--font-size', savedFontSize + 'pt');
        }}
        
        if (savedLineHeight) {{
            document.documentElement.style.setProperty('--line-height', savedLineHeight);
        }}
    }}
    
    setupReadingProgress() {{
        const explanationsPanel = document.querySelector('.explanations-panel');
        if (!explanationsPanel) return;
        
        let ticking = false;
        explanationsPanel.addEventListener('scroll', () => {{
            if (!ticking) {{
                window.requestAnimationFrame(() => {{
                    const scrollTop = explanationsPanel.scrollTop;
                    const scrollHeight = explanationsPanel.scrollHeight - explanationsPanel.clientHeight;
                    const progress = (scrollTop / scrollHeight) * 100;
                    
                    const progressBar = document.querySelector('.reading-progress');
                    if (progressBar) {{
                        progressBar.style.width = Math.min(progress, 100) + '%';
                    }}
                    
                    ticking = false;
                }});
                ticking = true;
            }}
        }});
    }}
    
    setupThemeToggle() {{
        const themeToggle = document.querySelector('.theme-toggle');
        if (!themeToggle) return;
        
        // Update button icon based on current theme
        this.updateThemeIcon();
        
        themeToggle.addEventListener('click', () => {{
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            localStorage.setItem('html-screenshot-theme', isDark ? 'dark' : 'light');
            this.updateThemeIcon();
        }});
    }}
    
    updateThemeIcon() {{
        const themeToggle = document.querySelector('.theme-toggle');
        if (!themeToggle) return;
        
        const isDark = document.body.classList.contains('dark-mode');
        themeToggle.textContent = isDark ? '☀️' : '🌙';
        themeToggle.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
    }}
    
    setupFontControls() {{
        const toggle = document.querySelector('.font-controls-toggle');
        const panel = document.querySelector('.font-controls');
        const fontSizeSlider = document.getElementById('font-size-slider');
        const lineHeightSlider = document.getElementById('line-height-slider');
        
        if (!toggle || !panel) return;
        
        // Toggle panel visibility
        toggle.addEventListener('click', () => {{
            this.fontControlsVisible = !this.fontControlsVisible;
            panel.classList.toggle('visible', this.fontControlsVisible);
        }});
        
        // Font size control
        if (fontSizeSlider) {{
            const savedFontSize = localStorage.getItem('html-screenshot-font-size') || '16';
            fontSizeSlider.value = savedFontSize;
            document.getElementById('font-size-value').textContent = savedFontSize + 'pt';
            
            fontSizeSlider.addEventListener('input', (e) => {{
                const value = e.target.value;
                document.documentElement.style.setProperty('--font-size', value + 'pt');
                document.getElementById('font-size-value').textContent = value + 'pt';
                localStorage.setItem('html-screenshot-font-size', value);
            }});
        }}
        
        // Line height control
        if (lineHeightSlider) {{
            const savedLineHeight = localStorage.getItem('html-screenshot-line-height') || '1.8';
            lineHeightSlider.value = savedLineHeight;
            document.getElementById('line-height-value').textContent = savedLineHeight;
            
            lineHeightSlider.addEventListener('input', (e) => {{
                const value = e.target.value;
                document.documentElement.style.setProperty('--line-height', value);
                document.getElementById('line-height-value').textContent = value;
                localStorage.setItem('html-screenshot-line-height', value);
            }});
        }}
    }}
    
    setupObserver() {{
        const options = {{
            root: document.querySelector('.screenshots-panel'),
            rootMargin: '-20% 0px -20% 0px',
            threshold: 0.5
        }};
        
        this.observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    const pageNum = parseInt(entry.target.dataset.page);
                    this.showExplanation(pageNum);
                    
                    // Add active class to current screenshot
                    document.querySelectorAll('.page-screenshot').forEach(el => {{
                        el.classList.remove('active');
                    }});
                    entry.target.classList.add('active');
                }}
            }});
        }}, options);
        
        // Observe all page screenshots
        document.querySelectorAll('.page-screenshot').forEach(el => {{
            this.observer.observe(el);
        }});
    }}
    
    setupControls() {{
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        
        if (prevBtn) {{
            prevBtn.addEventListener('click', () => this.goToPrevPage());
        }}
        
        if (nextBtn) {{
            nextBtn.addEventListener('click', () => this.goToNextPage());
        }}
        
        // Keyboard navigation with smooth scrolling
        document.addEventListener('keydown', (e) => {{
            // Don't trigger if user is typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {{
                return;
            }}
            
            switch(e.key) {{
                case 'ArrowUp':
                case 'ArrowLeft':
                    e.preventDefault();
                    this.goToPrevPage();
                    break;
                case 'ArrowDown':
                case 'ArrowRight':
                case ' ':
                    e.preventDefault();
                    this.goToNextPage();
                    break;
                case 'Home':
                    e.preventDefault();
                    this.goToPage(1);
                    break;
                case 'End':
                    e.preventDefault();
                    this.goToPage(this.totalPages);
                    break;
            }}
        }});
        
        // Apply smooth scrolling to explanations panel
        const explanationsPanel = document.querySelector('.explanations-panel');
        if (explanationsPanel) {{
            explanationsPanel.style.scrollBehavior = 'smooth';
        }}
    }}
    
    showExplanation(pageNum) {{
        if (pageNum < 1 || pageNum > this.totalPages) {{
            return;
        }}
        
        // Save current page scroll position before switching
        const explanationsPanel = document.querySelector('.explanations-panel');
        if (explanationsPanel && this.currentPage) {{
            this.pageScrollPositions[this.currentPage] = explanationsPanel.scrollTop;
        }}
        
        this.currentPage = pageNum;
        
        // Hide all explanations
        document.querySelectorAll('.explanation-item').forEach(el => {{
            el.classList.remove('active');
        }});
        
        // Show current explanation
        const targetExplanation = document.getElementById(`explanation-${{pageNum}}`);
        if (targetExplanation) {{
            targetExplanation.classList.add('active');
        }}
        
        // Restore scroll position for this page, or scroll to top if first visit
        if (explanationsPanel) {{
            // Temporarily disable smooth scrolling for instant position restore
            const originalBehavior = explanationsPanel.style.scrollBehavior;
            explanationsPanel.style.scrollBehavior = 'auto';
            
            if (this.pageScrollPositions[pageNum] !== undefined) {{
                // Restore previous scroll position
                explanationsPanel.scrollTop = this.pageScrollPositions[pageNum];
            }} else {{
                // First visit to this page, scroll to top
                explanationsPanel.scrollTop = 0;
            }}
            
            // Restore smooth scrolling for manual scrolling
            setTimeout(() => {{
                explanationsPanel.style.scrollBehavior = originalBehavior;
            }}, 0);
        }}
        
        // Update page indicator
        const indicator = document.querySelector('.current-page-indicator');
        if (indicator) {{
            indicator.textContent = `第 ${{pageNum}} 页 / 共 ${{this.totalPages}} 页`;
        }}
        
        // Update page info in controls
        const pageInfo = document.querySelector('.page-info');
        if (pageInfo) {{
            pageInfo.textContent = `${{pageNum}} / ${{this.totalPages}}`;
        }}
        
        // Update button states
        this.updateButtons();
        
        // Update document title
        document.title = `第${{pageNum}}页 - HTML截图版`;
    }}
    
    goToPage(pageNum) {{
        if (pageNum < 1 || pageNum > this.totalPages) {{
            return;
        }}
        
        // Scroll to the page screenshot
        const screenshot = document.getElementById(`page-${{pageNum}}`);
        if (screenshot) {{
            screenshot.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}
    }}
    
    goToPrevPage() {{
        if (this.currentPage > 1) {{
            this.goToPage(this.currentPage - 1);
        }}
    }}
    
    goToNextPage() {{
        if (this.currentPage < this.totalPages) {{
            this.goToPage(this.currentPage + 1);
        }}
    }}
    
    updateButtons() {{
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        
        if (prevBtn) {{
            prevBtn.disabled = this.currentPage <= 1;
        }}
        
        if (nextBtn) {{
            nextBtn.disabled = this.currentPage >= this.totalPages;
        }}
    }}
}}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {{
    window.sync = new ScreenshotExplanationSync();
    console.log('HTML Screenshot View initialized with {{}} pages', {total_pages});
}});

// Expose global functions
window.goToPage = function(pageNum) {{
    if (window.sync) {{
        window.sync.goToPage(pageNum);
    }}
}};
"""
        return js
    
    @staticmethod
    def generate_html_screenshot_view(
        screenshot_data: List[Dict[str, any]],
        explanations: Dict[int, str],
        total_pages: int,
        title: str = "PDF文档讲解",
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2,
        column_count: int = 2,
        column_gap: int = 20,
        show_column_rule: bool = True
    ) -> str:
        """
        Generate complete HTML screenshot view
        
        Args:
            screenshot_data: List of dicts with 'page_num' and 'image_bytes' keys
            explanations: Dict mapping page numbers (1-indexed) to explanation text
            total_pages: Total number of pages
            title: Document title
            font_name: Font family name
            font_size: Font size in pt
            line_spacing: Line height multiplier
            column_count: Number of columns for explanation text
            column_gap: Gap between columns in px
            show_column_rule: Whether to show column separator line
            
        Returns:
            Complete HTML document string
        """
        logger.info(f"Generating HTML screenshot view for {total_pages} pages with {column_count} columns")
        
        # Generate CSS and JavaScript
        css_styles = HTMLScreenshotGenerator._generate_css_styles(
            font_name, font_size, line_spacing, column_count, column_gap, show_column_rule
        )
        javascript_code = HTMLScreenshotGenerator._generate_javascript(total_pages)
        
        # Generate screenshot HTML
        screenshots_html = ""
        for data in screenshot_data:
            page_num = data['page_num']
            image_bytes = data['image_bytes']
            
            # Convert image to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            screenshots_html += f"""
            <div class="page-screenshot" id="page-{page_num}" data-page="{page_num}">
                <div class="page-number-badge">第 {page_num} 页</div>
                <img src="data:image/png;base64,{base64_image}" alt="第{page_num}页截图" />
            </div>
            """
        
        # Generate explanations HTML
        explanations_html = ""
        for page_num in range(1, total_pages + 1):
            explanation_text = explanations.get(page_num, "")
            
            # Render markdown to HTML
            if explanation_text.strip():
                explanation_html = HTMLScreenshotGenerator._render_markdown_to_html(explanation_text)
            else:
                explanation_html = "<p>暂无讲解内容</p>"
            
            explanations_html += f"""
            <div class="explanation-item" id="explanation-{page_num}" data-page="{page_num}">
                <div class="explanation-page-title">📖 第 {page_num} 页讲解</div>
                <div class="explanation-content">
                    {explanation_html}
                </div>
            </div>
            """
        
        # Generate complete HTML document
        html_document = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - HTML截图版</title>
    <style>{css_styles}</style>
</head>
<body>
    <!-- Reading Progress Bar -->
    <div class="reading-progress"></div>
    
    <!-- Loading indicator -->
    <div class="loading">
        <div style="font-size: 16pt; font-weight: bold; color: #2c3e50;">正在加载...</div>
    </div>
    
    <div class="main-container">
        <!-- Left panel: PDF screenshots -->
        <div class="screenshots-panel">
            {screenshots_html}
        </div>
        
        <!-- Right panel: Explanations -->
        <div class="explanations-panel">
            <div class="explanation-header">
                <div style="text-align: center; flex: 1;">
                    <h1>📚 {title}</h1>
                    <div class="current-page-indicator">第 1 页 / 共 {total_pages} 页</div>
                </div>
                <button class="font-controls-toggle" title="字体设置">Aa</button>
                <button class="theme-toggle" title="切换主题">🌙</button>
            </div>
            <div class="explanations-container">
                {explanations_html}
            </div>
        </div>
    </div>
    
    <!-- Navigation controls -->
    <div class="nav-controls">
        <button class="nav-btn" id="prev-btn" title="上一页 (↑)">‹ 上一页</button>
        <span class="page-info">1 / {total_pages}</span>
        <button class="nav-btn" id="next-btn" title="下一页 (↓)">下一页 ›</button>
    </div>
    
    <!-- Font Controls Panel -->
    <div class="font-controls">
        <div class="font-control-group">
            <label class="font-control-label">
                字体大小
                <span class="font-control-value" id="font-size-value">16pt</span>
            </label>
            <input 
                type="range" 
                class="font-control-slider" 
                id="font-size-slider" 
                min="12" 
                max="24" 
                step="1" 
                value="16"
            />
        </div>
        <div class="font-control-group">
            <label class="font-control-label">
                行距
                <span class="font-control-value" id="line-height-value">1.8</span>
            </label>
            <input 
                type="range" 
                class="font-control-slider" 
                id="line-height-slider" 
                min="1.3" 
                max="2.5" 
                step="0.1" 
                value="1.8"
            />
        </div>
    </div>
    
    <script>{javascript_code}</script>
</body>
</html>
"""
        
        logger.info(f"HTML screenshot view generated successfully, size: {len(html_document)} bytes")
        return html_document


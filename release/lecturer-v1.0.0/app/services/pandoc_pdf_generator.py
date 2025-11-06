#!/usr/bin/env python3
"""
Pandoc PDF 生成服务
使用 Pandoc + LaTeX 引擎生成三栏布局的讲解 PDF
"""

import subprocess
import tempfile
import os
import re
from typing import Optional, Tuple
from .logger import get_logger
from .pandoc_renderer import PandocRenderer

logger = get_logger()


class PandocPDFGenerator:
    """使用 Pandoc + LaTeX 生成 PDF"""
    
    _xelatex_path: Optional[str] = None  # 缓存的 XeLaTeX 路径
    _xelatex_available: Optional[bool] = None  # 缓存的 XeLaTeX 可用性
    _pandoc_available: Optional[bool] = None  # 缓存的 Pandoc 可用性
    _template_cache: dict = {}  # 模板缓存，key: (width, height, font_name, font_size, line_spacing, column_padding)
    _template_version = "2.0"  # 模板版本号，更改此值会清除所有缓存
    _last_error: Optional[str] = None  # 最后一次错误的详细信息
    
    @staticmethod
    def check_latex_engine_available() -> Tuple[bool, str]:
        """
        检查 LaTeX 引擎（XeLaTeX）是否可用（带缓存）
        
        Returns:
            (是否可用, 引擎信息或错误信息)
        """
        # 如果已缓存且可用，直接返回
        if PandocPDFGenerator._xelatex_available is True and PandocPDFGenerator._xelatex_path:
            return True, "XeLaTeX (cached)"
        
        logger.debug('Checking XeLaTeX availability')
        
        # 首先尝试 PATH 中的 xelatex
        try:
            result = subprocess.run(
                ['xelatex', '--version'],
                capture_output=True,
                text=True,
                timeout=5,
                shell=False
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                logger.info('XeLaTeX available in PATH: %s', version_line)
                PandocPDFGenerator._xelatex_available = True
                PandocPDFGenerator._xelatex_path = 'xelatex'
                return True, version_line
            else:
                logger.warning('XeLaTeX error: code=%d', result.returncode)
        except (FileNotFoundError, OSError):
            pass  # Continue to check common installation paths
        
        # 检查常见的 MiKTeX 安装路径
        common_paths = [
            r"C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe",
            r"C:\Program Files (x86)\MiKTeX\miktex\bin\xelatex.exe",
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "MiKTeX", "miktex", "bin", "x64", "xelatex.exe"),
        ]
        
        for xelatex_path in common_paths:
            if os.path.exists(xelatex_path):
                try:
                    result = subprocess.run(
                        [xelatex_path, '--version'],
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=5,
                        shell=False
                    )
                    if result.returncode == 0:
                        version_line = result.stdout.split('\n')[0] if result.stdout else "XeLaTeX"
                        logger.info('XeLaTeX available at: %s, version: %s', xelatex_path, version_line)
                        # 缓存找到的路径和可用性
                        PandocPDFGenerator._xelatex_path = xelatex_path
                        PandocPDFGenerator._xelatex_available = True
                        return True, f"{version_line} (at {xelatex_path})"
                except Exception as e:
                    logger.debug('XeLaTeX at %s failed: %s', xelatex_path, e)
                    continue
        
        logger.warning('XeLaTeX not found in PATH or common installation paths')
        PandocPDFGenerator._xelatex_available = False
        return False, "XeLaTeX 未找到。请确保 MiKTeX 已安装并添加到 PATH，或重启终端以刷新环境变量。"
    
    @staticmethod
    def _create_latex_template(
        width_pt: float,
        height_pt: float,
        font_name: Optional[str] = None,
        font_size: int = 12,
        line_spacing: float = 1.4,
        column_padding: int = 10
    ) -> str:
        """
        创建 LaTeX 模板，实现三栏布局（带缓存）
        
        Args:
            width_pt: 页面宽度（磅）
            height_pt: 页面高度（磅）
            font_name: 字体名称
            font_size: 字号
            line_spacing: 行距倍数
            column_padding: 栏内边距
            
        Returns:
            LaTeX 模板字符串
        """
        # 检查缓存（包含版本号以确保使用最新模板）
        cache_key = (PandocPDFGenerator._template_version, width_pt, height_pt, font_name, font_size, line_spacing, column_padding)
        if cache_key in PandocPDFGenerator._template_cache:
            logger.debug('Using cached LaTeX template')
            return PandocPDFGenerator._template_cache[cache_key]
        # 计算三栏布局的参数
        margin_x = 25  # 左右外边距
        margin_y = 40  # 上下外边距
        column_spacing = 12  # 栏间距
        available_width = width_pt - 2 * margin_x
        column_width = (available_width - 2 * column_spacing) / 3
        
        # 使用传入的字体名称，如果没有则使用默认
        if not font_name:
            font_name = "SimHei"  # 默认字体
        
        # 构建 LaTeX 模板
        # Pandoc 模板需要使用 $body$ 变量来插入 markdown 转换后的内容
        # XeLaTeX 不需要 inputenc，使用 xeCJK 处理中文
        template = f"""\\documentclass[fontsize={font_size}pt]{{article}}
\\usepackage{{xcolor}}
\\usepackage{{multicol}}
\\usepackage{{geometry}}
\\usepackage{{xeCJK}}
\\usepackage{{fancyvrb}}
% 不使用 listings 包，避免 METAFONT 相关问题
% \\usepackage{{listings}}
\\usepackage{{amsmath}}
\\usepackage{{amsfonts}}
\\usepackage{{amssymb}}
\\usepackage{{graphicx}}
\\usepackage{{url}}
\\usepackage{{hyperref}}
\\hypersetup{{colorlinks=false, pdfborder={{0 0 0}}, hidelinks}}
% 完全禁用 METAFONT，避免字体生成错误
\\pdfinclusioncopyfonts=0
\\pdfmapfile{{}}
% 不使用 booktabs 包，避免 METAFONT 相关问题
% 直接定义表格命令，避免依赖外部字体
\\makeatletter
% 定义简单的表格规则命令，不依赖 booktabs
\\newcommand{{\\toprule}}{{%
  \\\\[-0.5\\baselineskip]\\noindent\\hrulefill\\\\[0.5\\baselineskip]
}}
\\newcommand{{\\midrule}}{{%
  \\\\[0.5\\baselineskip]\\noindent\\hrulefill\\\\[0.5\\baselineskip]
}}
\\newcommand{{\\bottomrule}}{{%
  \\\\[0.5\\baselineskip]\\noindent\\hrulefill\\\\[-0.5\\baselineskip]
}}
\\newcommand{{\\cmidrule}}[1]{{%
  \\\\[0.5\\baselineskip]\\noindent\\hrulefill\\\\[0.5\\baselineskip]
}}
\\makeatother

% 页面尺寸
\\geometry{{
    paperwidth={width_pt}pt,
    paperheight={height_pt}pt,
    margin=0pt,
    noheadfoot
}}

% 字体设置
"""
        
        # 使用字体名称（LaTeX 会自动从系统字体中查找）
        # 获取 LaTeX 字体名称
        from app.services.font_helper import get_latex_font_name
        latex_font_name = get_latex_font_name(font_name)
        template += f"\\setCJKmainfont{{{latex_font_name}}}\n"
        logger.debug('Using font name: %s (LaTeX: %s)', font_name, latex_font_name)
        
        template += f"""

% 行距设置
\\renewcommand{{\\baselinestretch}}{{{line_spacing}}}
\\setlength{{\\baselineskip}}{{{font_size * line_spacing}pt}}

% 定义 pandoc 需要的命令（如果未定义则定义）
\\providecommand{{\\tightlist}}{{\\setlength{{\\itemsep}}{{0pt}}\\setlength{{\\parskip}}{{0pt}}}}

% 三栏布局设置
\\setlength{{\\columnsep}}{{{column_spacing}pt}}
\\setlength{{\\columnseprule}}{{0pt}}

% 代码块样式（不使用 listings 包，改用简单的 verbatim 环境）
% \\lstset 已移除，因为不再使用 listings 包
% 代码块将使用 verbatim 或 fancyvrb 环境处理

% 表格和浮动环境处理
\\makeatletter
% 简化表格，避免在三栏中溢出
\\renewenvironment{{table}}{{}}{{}}
\\renewenvironment{{table*}}{{}}{{}}
% 定义 pandoc 需要的环境（代码块相关）
\\newenvironment{{Shaded}}{{}}{{}}
\\newenvironment{{Highlighting}}{{}}{{}}
% Define longtable environment (pandoc may use, but multicols doesn't support it, use tabular instead)
% Syntax: \\begin{{longtable}}[position]{{columns}}, need to handle two parameters
\\makeatletter
% 定义 longtable 需要的命令
\\newcommand{{\\endhead}}{{}}  % longtable 表头结束标记
\\newcommand{{\\endfirsthead}}{{}}  % longtable 第一页表头结束标记
\\newcommand{{\\endfoot}}{{}}  % longtable 表尾结束标记
\\newcommand{{\\endlastfoot}}{{}}  % longtable 最后页表尾结束标记
\\newenvironment{{longtable}}[2][]{{
  \\begin{{tabular}}{{#2}}
}}{{
  \\end{{tabular}}
}}
\\makeatother
\\let\\oldverbatim\\verbatim
\\let\\oldendverbatim\\endverbatim
\\renewenvironment{{verbatim}}{{\\oldverbatim}}{{\\oldendverbatim}}
% 定义 Pandoc 代码高亮的 Token 命令（如果未定义则定义为空）
\\providecommand{{\\BuiltInTok}}[1]{{#1}}
\\providecommand{{\\CommentTok}}[1]{{#1}}
\\providecommand{{\\ControlFlowTok}}[1]{{#1}}
\\providecommand{{\\DocumentationTok}}[1]{{#1}}
\\providecommand{{\\ErrorTok}}[1]{{#1}}
\\providecommand{{\\ExtensionTok}}[1]{{#1}}
\\providecommand{{\\FunctionTok}}[1]{{#1}}
\\providecommand{{\\ImportTok}}[1]{{#1}}
\\providecommand{{\\InformationTok}}[1]{{#1}}
\\providecommand{{\\KeywordTok}}[1]{{#1}}
\\providecommand{{\\NormalTok}}[1]{{#1}}
\\providecommand{{\\OperatorTok}}[1]{{#1}}
\\providecommand{{\\OtherTok}}[1]{{#1}}
\\providecommand{{\\PreprocessorTok}}[1]{{#1}}
\\providecommand{{\\RegionMarkerTok}}[1]{{#1}}
\\providecommand{{\\SpecialCharTok}}[1]{{#1}}
\\providecommand{{\\SpecialStringTok}}[1]{{#1}}
\\providecommand{{\\StringTok}}[1]{{#1}}
\\providecommand{{\\VariableTok}}[1]{{#1}}
\\providecommand{{\\VerbatimStringTok}}[1]{{#1}}
\\providecommand{{\\WarningTok}}[1]{{#1}}
% 在多栏环境中，确保表格命令不使用 \\noalign
% 这些命令已经在前面定义过了，这里不需要重复
% 处理链接
\\let\\href\\url
\\makeatother

\\pagestyle{{empty}}
\\begin{{document}}
\\noindent
\\begin{{multicols*}}{{3}}
\\setlength{{\\parindent}}{{0pt}}
\\setlength{{\\parskip}}{{2pt}}
\\vspace*{{-\\topskip}}
% 在多栏环境中，\\noalign 不能使用，需要重新定义为无操作
\\makeatletter
\\renewcommand{{\\noalign}}[1]{{
  % 在多栏环境中忽略 \\noalign
}}
\\makeatother

$body$

\\end{{multicols*}}
\\end{{document}}
"""
        
        # 缓存模板
        PandocPDFGenerator._template_cache[cache_key] = template
        return template
    
    @staticmethod
    def get_last_error() -> Optional[str]:
        """获取最后一次错误的详细信息"""
        return PandocPDFGenerator._last_error
    
    @staticmethod
    def generate_pdf(
        markdown_content: str,
        width_pt: float,
        height_pt: float,
        font_name: Optional[str] = None,
        font_size: int = 12,
        line_spacing: float = 1.4,
        column_padding: int = 10
    ) -> Tuple[Optional[bytes], bool]:
        """
        使用 Pandoc + LaTeX 生成三栏布局的 PDF
        
        Args:
            markdown_content: Markdown 内容
            width_pt: PDF 宽度（磅），必须 > 0
            height_pt: PDF 高度（磅），必须 > 0
            font_name: 字体名称（如 "SimHei"），如果为 None 则使用默认字体
            font_size: 字号，必须 > 0
            line_spacing: 行距倍数，必须 > 0
            column_padding: 栏内边距，必须 >= 0
            
        Returns:
            (PDF bytes, 是否成功)
        """
        # 清除之前的错误
        PandocPDFGenerator._last_error = None
        
        # 参数验证
        if not markdown_content.strip():
            logger.debug('Empty markdown content, returning empty PDF')
            return None, True
        
        if width_pt <= 0 or height_pt <= 0:
            error_msg = f'Invalid dimensions: width_pt={width_pt}, height_pt={height_pt}'
            logger.error(error_msg)
            PandocPDFGenerator._last_error = error_msg
            return None, False
        
        if font_size <= 0:
            error_msg = f'Invalid font_size: {font_size}, must be > 0'
            logger.error(error_msg)
            PandocPDFGenerator._last_error = error_msg
            return None, False
        
        if line_spacing <= 0:
            error_msg = f'Invalid line_spacing: {line_spacing}, must be > 0'
            logger.error(error_msg)
            PandocPDFGenerator._last_error = error_msg
            return None, False
        
        if column_padding < 0:
            error_msg = f'Invalid column_padding: {column_padding}, must be >= 0'
            logger.error(error_msg)
            PandocPDFGenerator._last_error = error_msg
            return None, False
        
        # 检查 pandoc 可用性（使用缓存，但允许重新检查）
        if PandocPDFGenerator._pandoc_available is None:
            pandoc_available, pandoc_info = PandocRenderer.check_pandoc_available()
            PandocPDFGenerator._pandoc_available = pandoc_available
            if not pandoc_available:
                error_msg = f'Pandoc not available: {pandoc_info}'
                logger.error(error_msg)
                PandocPDFGenerator._last_error = error_msg
                return None, False
        elif not PandocPDFGenerator._pandoc_available:
            # 如果缓存显示不可用，尝试重新检查一次（可能工具刚安装）
            logger.warning('Pandoc cached as unavailable, re-checking...')
            pandoc_available, pandoc_info = PandocRenderer.check_pandoc_available()
            PandocPDFGenerator._pandoc_available = pandoc_available
            if not pandoc_available:
                error_msg = f'Pandoc not available (cached and re-checked): {pandoc_info}'
                logger.error(error_msg)
                PandocPDFGenerator._last_error = error_msg
                return None, False
        
        # 确保 pandoc 路径已设置（只检查一次）
        if PandocRenderer._pandoc_exe == 'pandoc':
            PandocRenderer.check_pandoc_available()
        
        pandoc_cmd = PandocRenderer._pandoc_exe
        if not pandoc_cmd:
            error_msg = 'Pandoc command not found after check'
            logger.error(error_msg)
            PandocPDFGenerator._last_error = error_msg
            return None, False
        
        # 检查 LaTeX 引擎可用性（使用缓存，但允许重新检查）
        if PandocPDFGenerator._xelatex_available is None:
            latex_available, latex_info = PandocPDFGenerator.check_latex_engine_available()
            if not latex_available:
                error_msg = f'LaTeX engine not available: {latex_info}'
                logger.error(error_msg)
                PandocPDFGenerator._last_error = error_msg
                return None, False
        elif not PandocPDFGenerator._xelatex_available:
            # 如果缓存显示不可用，尝试重新检查一次（可能工具刚安装）
            logger.warning('XeLaTeX cached as unavailable, re-checking...')
            latex_available, latex_info = PandocPDFGenerator.check_latex_engine_available()
            if not latex_available:
                error_msg = f'LaTeX engine not available (cached and re-checked): {latex_info}'
                logger.error(error_msg)
                PandocPDFGenerator._last_error = error_msg
                return None, False
        
        # 创建临时文件（使用更安全的临时目录名）
        temp_dir_obj = None
        try:
            try:
                temp_dir_obj = tempfile.TemporaryDirectory(prefix='pandoc_pdf_')
                temp_dir = temp_dir_obj.name
            except Exception as e:
                error_msg = f'Failed to create temporary directory: {e}'
                logger.error(error_msg)
                PandocPDFGenerator._last_error = error_msg
                return None, False
            
            # 创建 LaTeX 模板文件
            template_file = os.path.join(temp_dir, 'template.tex')
            template_content = PandocPDFGenerator._create_latex_template(
                width_pt, height_pt, font_name, font_size, line_spacing, column_padding
            )
            
            # 写入模板文件（使用 UTF-8 编码，确保无 BOM）
            try:
                with open(template_file, 'w', encoding='utf-8', errors='strict') as f:
                    f.write(template_content)
            except Exception as e:
                logger.error('Failed to write template file: %s', e)
                return None, False
            
            # 创建临时 markdown 文件（使用 UTF-8 编码，确保无 BOM）
            md_file = os.path.join(temp_dir, 'input.md')
            try:
                with open(md_file, 'w', encoding='utf-8', errors='strict') as f:
                    f.write(markdown_content)
            except Exception as e:
                logger.error('Failed to write markdown file: %s', e)
                return None, False
            
            # 方案5: 先生成 LaTeX，后处理移除 \noalign{}，然后编译
            logger.info('Calling pandoc to generate LaTeX, content length=%d', len(markdown_content))
            
            # 第一步：使用 pandoc 生成 LaTeX
            tex_file = os.path.join(temp_dir, 'output.tex')
            pandoc_args_tex = [
                pandoc_cmd,
                md_file,
                '--from=markdown+tex_math_single_backslash',
                '--to=latex',
                '--template', template_file,
                '--standalone',
            ]
            
            # 根据内容长度动态调整超时时间
            content_size_factor = max(1.0, len(markdown_content) / 10000)  # 每10KB增加1倍
            pandoc_timeout = min(30, max(10, int(10 * content_size_factor)))
            
            process_tex = subprocess.run(
                pandoc_args_tex,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=pandoc_timeout,
                shell=False,
                cwd=temp_dir
            )
            
            if process_tex.returncode != 0:
                error_msgs = []
                error_msgs.append(f"Pandoc return code: {process_tex.returncode}")
                if process_tex.stderr:
                    stderr_preview = process_tex.stderr[:2000] if len(process_tex.stderr) > 2000 else process_tex.stderr
                    error_msgs.append(f"stderr: {stderr_preview}")
                if process_tex.stdout:
                    stdout_preview = process_tex.stdout[:2000] if len(process_tex.stdout) > 2000 else process_tex.stdout
                    error_msgs.append(f"stdout: {stdout_preview}")
                error_msg = "\n".join(error_msgs) if error_msgs else "Unknown error"
                
                # 记录完整错误信息
                logger.error('Pandoc LaTeX generation failed (return code %d)', process_tex.returncode)
                logger.debug('Full Pandoc error: %s', error_msg)
                
                # 检查常见错误并设置详细错误信息
                detailed_error = error_msg
                if "not found" in error_msg.lower() or "cannot find" in error_msg.lower():
                    detailed_error = f"Pandoc or template file not found: {error_msg}"
                    logger.error('Pandoc or template file not found')
                elif "permission" in error_msg.lower() or "access" in error_msg.lower():
                    detailed_error = f"Permission denied accessing files: {error_msg}"
                    logger.error('Permission denied accessing files')
                elif "encoding" in error_msg.lower() or "utf" in error_msg.lower():
                    detailed_error = f"Encoding error in input: {error_msg}"
                    logger.error('Encoding error in input')
                
                PandocPDFGenerator._last_error = detailed_error
                return None, False
            
            # 第二步：后处理生成的 LaTeX，移除 \noalign{}（在多栏环境中不能使用）
            tex_content = process_tex.stdout
            
            # 使用更高效的正则表达式，一次性处理多个模式
            # 移除 toprule\midrule\bottomrule 后面的 \noalign{}
            tex_content = re.sub(r'\\(toprule|midrule|bottomrule)\\noalign\{\}', 
                                r'\\\1', tex_content, flags=re.MULTILINE)
            
            # 移除 cmidrule 后面的 \noalign{}
            tex_content = re.sub(r'\\cmidrule\{([^}]+)\}\\noalign\{\}', 
                                r'\\cmidrule{\1}', tex_content, flags=re.MULTILINE)
            
            # 移除所有 listings 相关的命令（如果 Pandoc 生成的话）
            tex_content = re.sub(r'\\begin\{lstlisting\}.*?\\end\{lstlisting\}', 
                                r'\\begin{verbatim}\\1\\end{verbatim}', tex_content, flags=re.DOTALL)
            tex_content = re.sub(r'\\lstinline\{[^}]+\}', r'\\verb|\\1|', tex_content)
            
            # 移除可能触发 METAFONT 的包引用
            tex_content = re.sub(r'\\usepackage\{booktabs\}', '', tex_content)
            tex_content = re.sub(r'\\usepackage\{listings\}', '', tex_content)
            
            # 保存处理后的 LaTeX
            processed_tex_file = os.path.join(temp_dir, 'processed.tex')
            try:
                with open(processed_tex_file, 'w', encoding='utf-8', errors='strict') as f:
                    f.write(tex_content)
            except Exception as e:
                logger.error('Failed to write processed LaTeX file: %s', e)
                return None, False
            
            logger.debug('Processed LaTeX file, removed \\noalign{} commands')
            
            # 第三步：使用 xelatex 直接编译处理后的 LaTeX
            xelatex_path_final = PandocPDFGenerator._xelatex_path or 'xelatex'
            pdf_file = os.path.join(temp_dir, 'processed.pdf')
            # 备用文件名（如果 xelatex 使用不同的命名）
            pdf_file_alt = os.path.join(temp_dir, os.path.splitext(os.path.basename(processed_tex_file))[0] + '.pdf')
            
            # 构建 xelatex 命令（优化编译速度，禁用 METAFONT）
            # -halt-on-error: 遇到错误立即停止
            # -interaction=nonstopmode: 非交互模式，遇到错误不停止
            # -synctex=0: 禁用同步，加快编译
            # 设置环境变量禁用 METAFONT
            env = os.environ.copy()
            env['MPMODE'] = 'OFF'  # 禁用 METAFONT 模式
            
            xelatex_args = [
                xelatex_path_final,
                '-interaction=nonstopmode',
                '-halt-on-error',
                '-synctex=0',  # 禁用同步，加快编译
                '-output-directory', temp_dir,
                processed_tex_file
            ]
            
            logger.debug('Compiling LaTeX with XeLaTeX: %s', xelatex_path_final)
            
            # 根据内容长度动态调整超时时间
            content_size_factor = max(1.0, len(markdown_content) / 10000)
            xelatex_timeout = min(45, max(15, int(15 * content_size_factor)))
            
            xelatex_process = subprocess.run(
                xelatex_args,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=xelatex_timeout,
                shell=False,
                cwd=temp_dir,
                env=env  # 传递环境变量以禁用 METAFONT
            )
            
            # 即使返回码非0，有时 PDF 也会生成（如果有警告但不致命）
            # 检查两个可能的 PDF 文件名
            pdf_to_check = pdf_file if os.path.exists(pdf_file) else pdf_file_alt
            
            if os.path.exists(pdf_to_check):
                try:
                    with open(pdf_to_check, 'rb') as f:
                        pdf_bytes = f.read()
                    if len(pdf_bytes) > 0:
                        if xelatex_process.returncode == 0:
                            logger.info('PDF generation success (via LaTeX processing), size=%d bytes', len(pdf_bytes))
                        else:
                            logger.warning('PDF generated with warnings (return code %d), size=%d bytes', 
                                         xelatex_process.returncode, len(pdf_bytes))
                        return pdf_bytes, True
                    else:
                        logger.error('Generated PDF file is empty: %s', pdf_to_check)
                        return None, False
                except Exception as e:
                    logger.error('Failed to read generated PDF file: %s', e)
                    return None, False
            elif xelatex_process.returncode == 0:
                # 返回码为0但PDF不存在，这是错误
                logger.error('XeLaTeX returned 0 but PDF file not found. Checked: %s, %s', 
                           pdf_file, pdf_file_alt)
                return None, False
            else:
                # 返回码非0且PDF不存在，收集错误信息
                error_msgs = []
                error_msgs.append(f"XeLaTeX return code: {xelatex_process.returncode}")
                if xelatex_process.stderr:
                    stderr_preview = xelatex_process.stderr[:2000] if len(xelatex_process.stderr) > 2000 else xelatex_process.stderr
                    error_msgs.append(f"stderr: {stderr_preview}")
                if xelatex_process.stdout:
                    stdout_preview = xelatex_process.stdout[:2000] if len(xelatex_process.stdout) > 2000 else xelatex_process.stdout
                    error_msgs.append(f"stdout: {stdout_preview}")
                if not error_msgs:
                    error_msgs.append("Unknown error")
                
                error_msg = "\n".join(error_msgs) if error_msgs else "Unknown error"
                
                # 记录完整错误信息
                logger.error('XeLaTeX compilation failed (return code %d)', xelatex_process.returncode)
                logger.debug('Full XeLaTeX error: %s', error_msg)
                
                # 检查是否是字体加载错误，如果是则自动回退到系统字体
                # 检查 stderr 和 stdout 以获取完整的错误信息
                full_error_text = ""
                if xelatex_process.stderr:
                    full_error_text += xelatex_process.stderr.lower()
                if xelatex_process.stdout:
                    full_error_text += xelatex_process.stdout.lower()
                
                error_lower = error_msg.lower()
                # 更激进的字体错误检测：如果使用自定义字体路径且编译失败，尝试回退
                # 检查明确的字体错误关键词
                has_font_keyword = (
                    "font" in error_lower or 
                    "cannot find font" in error_lower or 
                    "fontspec error" in error_lower or 
                    "font not found" in error_lower or
                    "font" in full_error_text or
                    "fontspec" in full_error_text or
                    "xecjk" in full_error_text or
                    "setcjkmainfont" in full_error_text
                )
                
                # 检查是否是明显的语法错误（如果是，则不是字体问题）
                is_syntax_error = (
                    "emergency stop" in error_lower or
                    "undefined control" in error_lower or
                    "file ended" in error_lower or
                    "missing" in error_lower or
                    "package" in error_lower
                )
                
                # 如果使用自定义字体路径且编译失败，且不是明显的语法错误，尝试回退
                should_try_fallback = (
                    has_font_keyword or  # 明确的字体错误
                    (font_name and xelatex_process.returncode == 1 and 
                     not is_syntax_error)  # 使用字体路径但编译失败，且不是语法错误
                )
                
                # 如果检测到可能是字体错误，尝试回退
                if should_try_fallback and font_name:
                    # 字体加载错误，尝试自动回退到系统字体
                    logger.warning('Font loading failed, retrying with system font (no custom font path)')
                    try:
                        # 重新生成模板，不使用字体路径
                        template_content_fallback = PandocPDFGenerator._create_latex_template(
                            width_pt, height_pt, None, font_size, line_spacing, column_padding
                        )
                        
                        # 重新写入模板文件
                        with open(template_file, 'w', encoding='utf-8', errors='strict') as f:
                            f.write(template_content_fallback)
                        
                        # 重新生成 LaTeX
                        process_tex_fallback = subprocess.run(
                            pandoc_args_tex,
                            capture_output=True,
                            text=True,
                            encoding='utf-8',
                            errors='replace',
                            timeout=pandoc_timeout,
                            shell=False,
                            cwd=temp_dir
                        )
                        
                        if process_tex_fallback.returncode == 0:
                            # 处理生成的 LaTeX
                            tex_content_fallback = process_tex_fallback.stdout
                            tex_content_fallback = re.sub(r'\\(toprule|midrule|bottomrule)\\noalign\{\}', 
                                                        r'\\\1', tex_content_fallback, flags=re.MULTILINE)
                            tex_content_fallback = re.sub(r'\\cmidrule\{([^}]+)\}\\noalign\{\}', 
                                                        r'\\cmidrule{\1}', tex_content_fallback, flags=re.MULTILINE)
                            
                            # 保存处理后的 LaTeX
                            with open(processed_tex_file, 'w', encoding='utf-8', errors='strict') as f:
                                f.write(tex_content_fallback)
                            
                            # 重新编译
                            logger.debug('Retrying XeLaTeX compilation with system font')
                            xelatex_process_fallback = subprocess.run(
                                xelatex_args,
                                capture_output=True,
                                text=True,
                                encoding='utf-8',
                                errors='replace',
                                timeout=xelatex_timeout,
                                shell=False,
                                cwd=temp_dir,
                                env=env  # 传递环境变量以禁用 METAFONT
                            )
                            
                            # 检查 PDF 是否生成（回退后可能文件名不同）
                            pdf_to_check_fallback = pdf_file if os.path.exists(pdf_file) else pdf_file_alt
                            
                            # 检查所有可能的 PDF 文件名
                            possible_pdf_files = [
                                pdf_file,
                                pdf_file_alt,
                                os.path.join(temp_dir, 'processed.pdf'),
                                os.path.join(temp_dir, os.path.splitext(os.path.basename(processed_tex_file))[0] + '.pdf'),
                            ]
                            
                            pdf_found = False
                            for pdf_candidate in possible_pdf_files:
                                if os.path.exists(pdf_candidate):
                                    try:
                                        with open(pdf_candidate, 'rb') as f:
                                            pdf_bytes_fallback = f.read()
                                        if len(pdf_bytes_fallback) > 0:
                                            logger.info('PDF generation success after font fallback (found at %s), size=%d bytes', 
                                                      pdf_candidate, len(pdf_bytes_fallback))
                                            logger.warning('Font %s could not be loaded, using system font instead', font_name)
                                            PandocPDFGenerator._last_error = None  # 清除错误，因为回退成功
                                            return pdf_bytes_fallback, True
                                    except Exception as e:
                                        logger.debug('Failed to read PDF at %s: %s', pdf_candidate, e)
                                        continue
                            
                            if not pdf_found:
                                # PDF 未找到，检查编译是否成功
                                if xelatex_process_fallback.returncode == 0:
                                    logger.error('Font fallback: XeLaTeX returned 0 but PDF not found in any expected location')
                                else:
                                    logger.warning('Font fallback: XeLaTeX compilation failed (return code %d)', 
                                                 xelatex_process_fallback.returncode)
                        else:
                            logger.warning('Font fallback Pandoc LaTeX generation failed (return code %d)', 
                                         process_tex_fallback.returncode)
                    except Exception as e:
                        logger.warning('Font fallback attempt failed: %s', e)
                        import traceback
                        logger.debug('Font fallback traceback: %s', traceback.format_exc())
                
                # 如果不是字体错误，或回退失败，提供详细诊断
                detailed_error = error_msg
                # 重新检查是否是字体错误（用于错误诊断）
                is_font_error_for_diagnosis = (
                    has_font_keyword or  # 明确的字体错误关键词
                    (font_name and xelatex_process.returncode == 1 and not is_syntax_error)
                )
                if is_font_error_for_diagnosis:
                    # 如果是字体加载错误，提供更详细的诊断
                    font_diagnosis = []
                    if font_name:
                        font_diagnosis.append(f"Font name: {font_name}")
                        # 尝试查找字体文件路径
                        from app.services.font_helper import get_font_file_path
                        font_path = get_font_file_path(font_name)
                        if font_path:
                            font_diagnosis.append(f"Font file path: {font_path}")
                            if os.path.exists(font_path):
                                font_diagnosis.append("Font file exists")
                            else:
                                font_diagnosis.append("Font file NOT found")
                        else:
                            font_diagnosis.append("Font file path not found - using system font")
                    else:
                        font_diagnosis.append("No font name specified - using system font")
                    
                    detailed_error = f"Font loading error. {'; '.join(font_diagnosis)}. LaTeX error: {error_msg[:500]}"
                    logger.error('Font loading error - check font name: %s', font_name)
                    logger.error('Font diagnosis: %s', '; '.join(font_diagnosis))
                elif "package" in error_lower and ("not found" in error_lower or "missing" in error_lower):
                    detailed_error = f"LaTeX package missing - may need to install packages. {error_msg}"
                    logger.error('LaTeX package missing - may need to install packages')
                elif "emergency stop" in error_lower:
                    detailed_error = f"LaTeX emergency stop - check syntax errors. {error_msg}"
                    logger.error('LaTeX emergency stop - check syntax errors')
                elif "file ended" in error_lower:
                    detailed_error = f"LaTeX file ended unexpectedly - check for unmatched braces. {error_msg}"
                    logger.error('LaTeX file ended unexpectedly - check for unmatched braces')
                elif "undefined control sequence" in error_lower:
                    detailed_error = f"LaTeX undefined command - check for typos or missing packages. {error_msg}"
                    logger.error('LaTeX undefined command - check for typos or missing packages')
                
                PandocPDFGenerator._last_error = detailed_error
                return None, False
        except subprocess.TimeoutExpired as e:
            error_msg = f'Pandoc PDF generation timeout after {getattr(e, "timeout", "unknown")} seconds. Content length: {len(markdown_content)} bytes, may need longer timeout'
            logger.error('Pandoc PDF generation timeout after %s seconds', getattr(e, 'timeout', 'unknown'))
            logger.error('Content length: %d bytes, may need longer timeout', len(markdown_content))
            PandocPDFGenerator._last_error = error_msg
            return None, False
        except FileNotFoundError as e:
            error_msg = f'File not found during PDF generation: {e}. Check if pandoc and xelatex are properly installed'
            logger.error('File not found during PDF generation: %s', e)
            logger.error('Check if pandoc and xelatex are properly installed')
            PandocPDFGenerator._last_error = error_msg
            return None, False
        except PermissionError as e:
            error_msg = f'Permission denied during PDF generation: {e}. Check file permissions and temp directory access'
            logger.error('Permission denied during PDF generation: %s', e)
            logger.error('Check file permissions and temp directory access')
            PandocPDFGenerator._last_error = error_msg
            return None, False
        except UnicodeEncodeError as e:
            error_msg = f'Encoding error during PDF generation: {e}. Content may contain invalid characters'
            logger.error('Encoding error during PDF generation: %s', e)
            logger.error('Content may contain invalid characters')
            PandocPDFGenerator._last_error = error_msg
            return None, False
        except Exception as e:
            error_msg = f'Pandoc PDF generation exception: {e}'
            logger.error('Pandoc PDF generation exception: %s', e, exc_info=True)
            logger.error('Unexpected error - check logs for details')
            PandocPDFGenerator._last_error = error_msg
            return None, False
        finally:
            # 清理临时目录
            if temp_dir_obj:
                try:
                    temp_dir_obj.cleanup()
                except Exception as e:
                    logger.debug('Failed to cleanup temp directory: %s', e)


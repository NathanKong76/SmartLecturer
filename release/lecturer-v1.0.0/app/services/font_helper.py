"""
字体辅助工具模块
用于检测和管理 Windows 系统中的中文字体
"""

import os
import sys
from typing import List, Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)

# 常见中文字体的映射（显示名称 -> LaTeX 字体名称）
FONT_NAME_MAPPING = {
    "黑体": "SimHei",
    "SimHei": "SimHei",
    "宋体": "SimSun",
    "SimSun": "SimSun",
    "微软雅黑": "Microsoft YaHei",
    "Microsoft YaHei": "Microsoft YaHei",
    "微软正黑体": "Microsoft JhengHei",
    "Microsoft JhengHei": "Microsoft JhengHei",
    "楷体": "KaiTi",
    "KaiTi": "KaiTi",
    "仿宋": "FangSong",
    "FangSong": "FangSong",
    "思源黑体": "Source Han Sans SC",
    "Source Han Sans SC": "Source Han Sans SC",
    "思源宋体": "Source Han Serif SC",
    "Source Han Serif SC": "Source Han Serif SC",
    "Noto Sans SC": "Noto Sans SC",
    "Noto Serif SC": "Noto Serif SC",
    "文泉驿正黑": "WenQuanYi Zen Hei",
    "WenQuanYi Zen Hei": "WenQuanYi Zen Hei",
    "文泉驿微米黑": "WenQuanYi Micro Hei",
    "WenQuanYi Micro Hei": "WenQuanYi Micro Hei",
}

# 常见中文字体的文件名称模式（用于识别）
CJK_FONT_PATTERNS = [
    "simhei", "simsun", "simkai", "simfang",  # 中文简体字体
    "msyh", "msjh",  # 微软雅黑、微软正黑
    "kaiti", "fangsong",  # 楷体、仿宋
    "sourcehansans", "sourcehanserif",  # 思源字体
    "notosans", "notoserif",  # Noto 字体
    "wenquanyi",  # 文泉驿字体
]


def get_windows_cjk_fonts() -> List[Tuple[str, Optional[str]]]:
    """
    获取 Windows 系统中已安装的中文字体列表
    
    返回:
        List[Tuple[str, Optional[str]]]: 字体列表，每个元素为 (显示名称, 字体文件路径)
        显示名称用于 UI 显示，字体文件路径用于 PyMuPDF 加载
    """
    fonts = []
    
    if sys.platform != 'win32':
        logger.warning('Font detection is only supported on Windows. Using default font list.')
        return _get_default_fonts()
    
    try:
        # 方法1: 尝试使用 win32api 枚举字体
        try:
            import win32api
            import win32con
            
            def enum_font_callback(lf, tm, font_type, data):
                """字体枚举回调函数"""
                font_name = lf.lfFaceName
                if _is_cjk_font(font_name):
                    # 获取字体文件路径
                    font_path = _get_font_file_path(font_name)
                    fonts.append((font_name, font_path))
                return 1  # 继续枚举
            
            # 枚举所有字体
            win32api.EnumFontFamilies(None, None, enum_font_callback, None)
            
            if fonts:
                logger.debug(f'Found {len(fonts)} CJK fonts using win32api')
                return _process_font_list(fonts)
        
        except ImportError:
            logger.debug('win32api not available, trying alternative method')
        
        # 方法2: 扫描 Windows Fonts 目录
        fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
        if os.path.exists(fonts_dir):
            fonts = _scan_fonts_directory(fonts_dir)
            if fonts:
                logger.debug(f'Found {len(fonts)} CJK fonts by scanning directory')
                return _process_font_list(fonts)
        
    except Exception as e:
        logger.warning(f'Error detecting fonts: {e}', exc_info=True)
    
    # 如果检测失败，返回默认字体列表
    logger.info('Using default font list')
    return _get_default_fonts()


def _is_cjk_font(font_name: str) -> bool:
    """判断是否为中文字体"""
    font_name_lower = font_name.lower()
    
    # 检查是否匹配已知的中文字体模式
    for pattern in CJK_FONT_PATTERNS:
        if pattern in font_name_lower:
            return True
    
    # 检查是否在字体名称映射中
    if font_name in FONT_NAME_MAPPING:
        return True
    
    # 检查是否包含常见中文字体关键词
    cjk_keywords = ['hei', 'song', 'kai', 'fang', 'yahei', 'jhenghei', 
                    'source', 'noto', 'wenquan', 'han', 'cjk']
    for keyword in cjk_keywords:
        if keyword in font_name_lower:
            return True
    
    return False


def _get_font_file_path(font_name: str) -> Optional[str]:
    """根据字体名称获取字体文件路径"""
    fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
    
    # 尝试常见的字体文件扩展名
    extensions = ['.ttf', '.ttc', '.otf', '.ttc']
    
    # 尝试不同的文件名格式
    possible_names = [
        font_name,
        font_name.replace(' ', ''),
        font_name.replace(' ', '-'),
        font_name.replace(' ', '_'),
    ]
    
    for name in possible_names:
        for ext in extensions:
            font_path = os.path.join(fonts_dir, f"{name}{ext}")
            if os.path.exists(font_path):
                return font_path
        
        # 尝试小写
        for ext in extensions:
            font_path = os.path.join(fonts_dir, f"{name.lower()}{ext}")
            if os.path.exists(font_path):
                return font_path
    
    # 如果找不到，尝试扫描所有字体文件
    if os.path.exists(fonts_dir):
        for filename in os.listdir(fonts_dir):
            if filename.lower().endswith(('.ttf', '.ttc', '.otf')):
                # 尝试从文件名推断字体名称
                base_name = os.path.splitext(filename)[0]
                if font_name.lower() in base_name.lower() or base_name.lower() in font_name.lower():
                    return os.path.join(fonts_dir, filename)
    
    return None


def _scan_fonts_directory(fonts_dir: str) -> List[Tuple[str, Optional[str]]]:
    """扫描字体目录，查找中文字体"""
    fonts = []
    seen_names = set()
    
    try:
        for filename in os.listdir(fonts_dir):
            if not filename.lower().endswith(('.ttf', '.ttc', '.otf')):
                continue
            
            # 尝试从文件名提取字体名称
            base_name = os.path.splitext(filename)[0]
            
            # 移除常见后缀
            base_name = base_name.replace('_', ' ').replace('-', ' ')
            
            # 检查是否匹配中文字体模式
            if _is_cjk_font(base_name):
                font_path = os.path.join(fonts_dir, filename)
                if base_name not in seen_names:
                    fonts.append((base_name, font_path))
                    seen_names.add(base_name)
    except Exception as e:
        logger.warning(f'Error scanning fonts directory: {e}')
    
    return fonts


def _process_font_list(fonts: List[Tuple[str, Optional[str]]]) -> List[Tuple[str, Optional[str]]]:
    """处理字体列表：去重、排序、设置默认值"""
    # 去重（基于字体名称）
    unique_fonts = {}
    for font_name, font_path in fonts:
        if font_name not in unique_fonts:
            unique_fonts[font_name] = font_path
    
    # 转换为列表并排序
    font_list = [(name, path) for name, path in unique_fonts.items()]
    font_list.sort(key=lambda x: x[0])
    
    # 确保黑体（SimHei）在列表前面
    simhei_fonts = [f for f in font_list if 'simhei' in f[0].lower() or 'hei' in f[0].lower() and 'sim' in f[0].lower()]
    other_fonts = [f for f in font_list if f not in simhei_fonts]
    
    # 将黑体放在前面
    result = simhei_fonts + other_fonts
    
    return result if result else _get_default_fonts()


def _get_default_fonts() -> List[Tuple[str, Optional[str]]]:
    """返回默认字体列表（当检测失败时使用）"""
    default_fonts = [
        ("SimHei", None),  # 黑体
        ("SimSun", None),  # 宋体
        ("Microsoft YaHei", None),  # 微软雅黑
        ("KaiTi", None),  # 楷体
        ("FangSong", None),  # 仿宋
    ]
    
    # 尝试为默认字体查找文件路径
    fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
    if os.path.exists(fonts_dir):
        result = []
        for font_name, _ in default_fonts:
            font_path = _get_font_file_path(font_name)
            result.append((font_name, font_path))
        return result
    
    return default_fonts


def get_font_file_path(font_name: str) -> Optional[str]:
    """
    根据字体名称获取字体文件路径
    
    参数:
        font_name: 字体名称（显示名称或 LaTeX 名称）
    
    返回:
        字体文件路径，如果找不到则返回 None
    """
    # 首先尝试直接查找
    fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
    if not os.path.exists(fonts_dir):
        return None
    
    # 获取字体列表
    available_fonts = get_windows_cjk_fonts()
    for name, path in available_fonts:
        if name == font_name or name.lower() == font_name.lower():
            return path
    
    # 如果找不到，尝试直接查找文件
    return _get_font_file_path(font_name)


def get_latex_font_name(font_name: str) -> str:
    """
    获取 LaTeX 使用的字体名称
    
    参数:
        font_name: 字体显示名称
    
    返回:
        LaTeX 字体名称
    """
    return FONT_NAME_MAPPING.get(font_name, font_name)


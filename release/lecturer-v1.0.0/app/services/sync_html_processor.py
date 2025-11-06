#!/usr/bin/env python3
"""
同步HTML处理器
集成增强版HTML生成器与现有系统，实现PDF-讲解同步功能
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from app.services.logger import get_logger
from app.services.enhanced_html_generator import EnhancedHTMLGenerator

logger = get_logger()


class SyncHTMLProcessor:
    """同步HTML处理器"""
    
    def __init__(self, output_dir: str = "sync_html_output"):
        """
        初始化同步HTML处理器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.generator = EnhancedHTMLGenerator()
    
    def generate_sync_view(
        self,
        pdf_content: str,
        explanations: Dict[int, str],
        total_pages: int = 1,
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2,
        filename: str = "sync_view.html"
    ) -> str:
        """
        生成同步视图HTML文件
        
        Args:
            pdf_content: PDF文件路径
            explanations: 页码到讲解内容的映射
            total_pages: 总页数
            font_name: 字体名称
            font_size: 字号大小
            line_spacing: 行距倍数
            filename: 输出文件名
            
        Returns:
            生成的HTML文件路径
        """
        try:
            html_content = self.generator.generate_sync_html(
                pdf_content=pdf_content,
                explanations=explanations,
                total_pages=total_pages,
                font_name=font_name,
                font_size=font_size,
                line_spacing=line_spacing
            )
            
            output_path = self.output_dir / filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"同步视图HTML已生成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"生成同步视图HTML失败: {e}")
            raise
    
    def generate_navigation_index(
        self,
        explanations: Dict[int, str],
        total_pages: int = 1,
        pdf_filename: str = "document.pdf",
        font_name: str = "SimHei",
        font_size: int = 14,
        filename: str = "index.html"
    ) -> str:
        """
        生成导航索引页面
        
        Args:
            explanations: 页码到讲解内容的映射
            total_pages: 总页数
            pdf_filename: PDF文件名
            font_name: 字体名称
            font_size: 字号大小
            filename: 输出文件名
            
        Returns:
            生成的HTML文件路径
        """
        try:
            nav_content = self.generator.create_navigation_html(
                total_pages=total_pages,
                explanations=explanations,
                pdf_filename=pdf_filename,
                font_name=font_name,
                font_size=font_size
            )
            
            output_path = self.output_dir / filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(nav_content)
            
            logger.info(f"导航索引页面已生成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"生成导航索引页面失败: {e}")
            raise
    
    def generate_complete_sync_package(
        self,
        pdf_content: str,
        explanations: Dict[int, str],
        total_pages: int = 1,
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2,
        pdf_filename: str = "document.pdf"
    ) -> Dict[str, str]:
        """
        生成完整的同步HTML包，包含所有文件
        
        Args:
            pdf_content: PDF文件路径
            explanations: 页码到讲解内容的映射
            total_pages: 总页数
            font_name: 字体名称
            font_size: 字号大小
            line_spacing: 行距倍数
            pdf_filename: PDF文件名
            
        Returns:
            包含所有生成文件路径的字典
        """
        try:
            generated_files = {}
            
            # 1. 生成主同步视图
            sync_view_path = self.generate_sync_view(
                pdf_content=pdf_content,
                explanations=explanations,
                total_pages=total_pages,
                font_name=font_name,
                font_size=font_size,
                line_spacing=line_spacing,
                filename="sync_view.html"
            )
            generated_files['sync_view'] = sync_view_path
            
            # 2. 生成导航索引页面
            index_path = self.generate_navigation_index(
                explanations=explanations,
                total_pages=total_pages,
                pdf_filename=pdf_filename,
                font_name=font_name,
                font_size=font_size,
                filename="index.html"
            )
            generated_files['index'] = index_path
            
            # 3. 复制PDF文件到输出目录（如果需要）
            if os.path.exists(pdf_content) and pdf_content != str(self.output_dir / pdf_filename):
                import shutil
                pdf_dest = self.output_dir / pdf_filename
                shutil.copy2(pdf_content, pdf_dest)
                generated_files['pdf'] = str(pdf_dest)
            
            # 4. 生成配置文件
            config = {
                'total_pages': total_pages,
                'pdf_filename': pdf_filename,
                'explanations_count': len(explanations),
                'font_settings': {
                    'font_name': font_name,
                    'font_size': font_size,
                    'line_spacing': line_spacing
                }
            }
            
            config_path = self.output_dir / "config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            generated_files['config'] = str(config_path)
            
            # 5. 生成说明文档
            readme_content = self._generate_readme(
                total_pages=total_pages,
                pdf_filename=pdf_filename,
                explanations_count=len(explanations)
            )
            
            readme_path = self.output_dir / "README.md"
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            generated_files['readme'] = str(readme_path)
            
            logger.info(f"完整的同步HTML包已生成，包含 {len(generated_files)} 个文件")
            return generated_files
            
        except Exception as e:
            logger.error(f"生成完整同步HTML包失败: {e}")
            raise
    
    def _generate_readme(
        self,
        total_pages: int,
        pdf_filename: str,
        explanations_count: int
    ) -> str:
        """生成说明文档"""
        return f"""# PDF讲解同步视图

## 文件说明

- `index.html` - 导航索引页面，提供页面概览和快速跳转
- `sync_view.html` - 主要的PDF-讲解同步视图
- `{pdf_filename}` - PDF文档文件
- `config.json` - 配置文件
- `README.md` - 说明文档（本文件）

## 使用方法

### 1. 导航索引模式
打开 `index.html` 可以看到所有页面的概览，点击"打开同步模式"按钮可以直接跳转到对应页面。

### 2. 同步阅读模式
打开 `sync_view.html` 可以进行PDF和讲解的同步阅读：

#### 操作方式：
- **鼠标操作**: 点击PDF下方的"上一页"/"下一页"按钮
- **键盘操作**: 
  - `←` `↑` - 上一页
  - `→` `↓` `空格` - 下一页
  - `Home` - 第一页
  - `End` - 最后一页

#### 功能特性：
- 📖 **实时同步**: PDF页面变化时，右侧讲解内容自动切换
- 🎨 **优雅界面**: 现代化的分栏布局，支持响应式设计
- ⌨️ **键盘导航**: 支持键盘快捷键操作
- 📱 **移动端友好**: 在手机上也能良好显示和操作
- 🖨️ **打印支持**: 支持打印输出

## 技术特性

- **总页数**: {total_pages} 页
- **讲解页面**: {explanations_count} 页有内容
- **字体设置**: 支持自定义字体和字号
- **布局适配**: 自动适配桌面和移动设备

## 浏览器兼容性

- ✅ Chrome 70+
- ✅ Firefox 65+
- ✅ Safari 12+
- ✅ Edge 79+

## 故障排除

### PDF无法显示
1. 检查PDF文件路径是否正确
2. 确保浏览器支持PDF插件
3. 尝试刷新页面

### 讲解内容不更新
1. 检查JavaScript是否启用
2. 查看浏览器控制台是否有错误信息
3. 尝试刷新页面

### 键盘快捷键不工作
1. 确保页面获得了焦点
2. 检查是否与其他浏览器扩展冲突

## 文件结构

```
sync_html_output/
├── index.html          # 导航索引页
├── sync_view.html      # 同步视图页
├── {pdf_filename}         # PDF文件
├── config.json          # 配置文件
└── README.md           # 说明文档
```

---
*生成时间: {self._get_current_time()}*
*PDF讲解同步视图系统*
"""
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 便捷函数
def create_sync_html(
    pdf_path: str,
    explanations: Dict[int, str],
    total_pages: int,
    output_dir: str = "sync_html_output",
    **kwargs
) -> Dict[str, str]:
    """
    创建同步HTML视图的便捷函数
    
    Args:
        pdf_path: PDF文件路径
        explanations: 页码到讲解内容的映射
        total_pages: 总页数
        output_dir: 输出目录
        **kwargs: 其他参数（font_name, font_size, line_spacing等）
        
    Returns:
        包含生成文件路径的字典
    """
    processor = SyncHTMLProcessor(output_dir)
    return processor.generate_complete_sync_package(
        pdf_content=pdf_path,
        explanations=explanations,
        total_pages=total_pages,
        pdf_filename=os.path.basename(pdf_path),
        **kwargs
    )


def generate_simple_sync_view(
    pdf_path: str,
    explanations: Dict[int, str],
    total_pages: int,
    output_path: str = "simple_sync.html"
) -> str:
    """
    生成简单同步视图的便捷函数
    
    Args:
        pdf_path: PDF文件路径
        explanations: 页码到讲解内容的映射
        total_pages: 总页数
        output_path: 输出文件路径
        
    Returns:
        生成的HTML文件路径
    """
    processor = SyncHTMLProcessor()
    return processor.generate_sync_view(
        pdf_content=pdf_path,
        explanations=explanations,
        total_pages=total_pages,
        filename=os.path.basename(output_path)
    )


if __name__ == "__main__":
    # 示例使用
    import tempfile
    
    # 模拟数据
    sample_explanations = {
        1: "这是第一页的讲解内容。本页主要介绍文档的基本结构和内容概览。",
        2: "第二页讲解了主要概念和理论基础。这些概念是理解后续内容的基础。",
        3: "第三页展示了具体的应用案例。通过实例可以更好地理解理论知识的实际应用。"
    }
    
    # 创建临时PDF文件（实际使用时应替换为真实PDF路径）
    pdf_content = b"%PDF-1.4\n%Sample PDF content\n"
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
        tmp_pdf.write(pdf_content)
        pdf_path = tmp_pdf.name
    
    try:
        # 生成同步HTML
        result = create_sync_html(
            pdf_path=pdf_path,
            explanations=sample_explanations,
            total_pages=3,
            output_dir="test_sync_output"
        )
        
        print("同步HTML生成完成:")
        for file_type, file_path in result.items():
            print(f"  {file_type}: {file_path}")
            
    finally:
        # 清理临时文件
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)

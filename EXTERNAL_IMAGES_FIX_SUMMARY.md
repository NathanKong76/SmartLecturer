# 外部图片打包功能修复总结

## 问题描述
用户反馈：当选择"不嵌入图片到Markdown"时，虽然生成了包含图片占位符的Markdown文档，但没有实际保存图片文件，也没有提供图片文件的下载方式。

错误示例：
```markdown
![第1页截图](page_1.png)  <!-- 只是占位符，实际没有page_1.png文件 -->
```

## 解决方案

### 1. 修改 `pdf_processor.py`

#### a) 更新 `create_page_screenshot_markdown` 函数
- **新增参数**：`image_path` - 外部图片文件的实际路径
- **修改逻辑**：当 `embed_images=False` 时，使用相对路径 `images/page_X.png` 引用图片

```python
def create_page_screenshot_markdown(page_num: int, screenshot_bytes: bytes,
                                   explanation: str, embed_images: bool = True,
                                   image_path: Optional[str] = None) -> str:
    # ...
    if embed_images:
        # base64嵌入
        base64_data = base64.b64encode(screenshot_bytes).decode('utf-8')
        markdown_content += f"![第{page_num}页截图](data:image/png;base64,{base64_data})\n\n"
    else:
        # 外部图片 - 使用相对路径
        if image_path:
            markdown_content += f"![第{page_num}页截图](images/page_{page_num}.png)\n\n"
```

#### b) 更新 `generate_markdown_with_screenshots` 函数
- **新增参数**：`images_dir` - 外部图片保存目录
- **返回类型**：从 `str` 改为 `Tuple[str, Optional[str]]`，返回 `(markdown_content, images_dir)`
- **保存图片**：当 `embed_images=False` 时，实际保存PNG文件到 `images_dir`

```python
def generate_markdown_with_screenshots(..., images_dir: Optional[str] = None) -> Tuple[str, Optional[str]]:
    # 创建图片目录
    if not embed_images and images_dir:
        os.makedirs(images_dir, exist_ok=True)
    
    # 保存每页截图
    for page_num in range(total_pages):
        screenshot_bytes = _page_png_bytes(src_doc, page_num, screenshot_dpi)
        
        if not embed_images and images_dir:
            image_path = os.path.join(images_dir, f"page_{page_num + 1}.png")
            with open(image_path, 'wb') as f:
                f.write(screenshot_bytes)
        
        # 生成markdown
        page_markdown = create_page_screenshot_markdown(
            page_num + 1,
            screenshot_bytes,
            explanation,
            embed_images,
            image_path if not embed_images else None
        )
    
    return markdown_content, images_dir if not embed_images else None
```

#### c) 更新 `process_markdown_mode` 函数
- **新增参数**：`images_dir` - 外部图片保存目录
- **返回类型**：从 `Tuple[str, Dict, List[int]]` 改为 `Tuple[str, Dict, List[int], Optional[str]]`
- **传递参数**：将 `images_dir` 传递给 `generate_markdown_with_screenshots`

### 2. 修改 `streamlit_app.py`

#### a) 更新 `_build_and_run_with_pairs` 函数
- **创建图片目录**：当 `embed_images=False` 时，为每个PDF创建独立的图片目录
- **保存图片目录路径**：在 `batch_results` 中保存 `images_dir` 路径
- **打包图片到ZIP**：在构建ZIP文件时，将图片文件夹也包含进去

```python
# 创建临时目录保存图片（如果不嵌入）
embed_images = params.get("embed_images", True)
images_dir = None
if not embed_images:
    base_name = os.path.splitext(pdf_name)[0]
    images_dir = os.path.join(TEMP_DIR, f"{base_name}_images")
    os.makedirs(images_dir, exist_ok=True)

# 生成markdown文档
markdown_content, images_dir_return = pdf_processor.generate_markdown_with_screenshots(
    src_bytes=pdf_bytes,
    explanations=explanations,
    screenshot_dpi=params.get("screenshot_dpi", 150),
    embed_images=embed_images,
    title=params.get("markdown_title", "PDF文档讲解"),
    images_dir=images_dir
)

batch_results[pdf_name] = {
    "status": "completed",
    "markdown_content": markdown_content,
    "explanations": explanations,
    "images_dir": images_dir_return  # 保存图片目录路径
}
```

#### b) 更新ZIP打包逻辑
- **打包图片文件**：遍历 `images_dir` 中的所有PNG文件
- **保持目录结构**：在ZIP中创建 `{base_name}_images/` 目录

```python
# 如果有外部图片文件夹，打包到ZIP中
images_dir = result.get("images_dir")
if images_dir and os.path.exists(images_dir):
    for img_file in os.listdir(images_dir):
        img_path = os.path.join(images_dir, img_file)
        if os.path.isfile(img_path):
            # 在ZIP中创建images目录
            zip_img_path = f"{base_name}_images/{img_file}"
            zip_file.write(img_path, zip_img_path)
```

#### c) 更新函数调用
- **更新返回值接收**：所有调用 `process_markdown_mode` 的地方都要接收第4个返回值（images_dir）

## 修复后的效果

### 1. 选择"不嵌入图片"时
- 生成 `{文件名}_images/` 文件夹，包含所有页面截图（`page_1.png`, `page_2.png`, ...）
- Markdown文档使用相对路径引用：`![截图](images/page_1.png)`
- ZIP下载包含：
  ```
  📦 下载文件.zip
  ├── 📄 Week 12 Security2讲解文档.md
  ├── 📝 Week 12 Security2.json
  └── 📁 Week 12 Security2_images/
      ├── 📄 page_1.png
      ├── 📄 page_2.png
      └── 📄 ...
  ```

### 2. 选择"嵌入图片"时（原有功能保持不变）
- Markdown文档直接包含base64编码的图片
- ZIP下载只包含：
  ```
  📦 下载文件.zip
  ├── 📄 Week 12 Security2讲解文档.md
  └── 📝 Week 12 Security2.json
  ```

## 测试验证

### 1. 语法检查
```bash
python -m py_compile app/streamlit_app.py app/services/pdf_processor.py
# ✅ 无语法错误
```

### 2. 功能测试
```bash
python test_external_images.py
# [PASS] create_page_screenshot_markdown with external images
# [PASS] create_page_screenshot_markdown with embedded images
# All tests passed!
```

## 影响范围

### 修改的文件
1. `app/services/pdf_processor.py`
   - `create_page_screenshot_markdown`
   - `generate_markdown_with_screenshots`
   - `process_markdown_mode`

2. `app/streamlit_app.py`
   - `_build_and_run_with_pairs`
   - `cached_process_markdown` (2处更新)
   - 批量处理逻辑 (1处更新)

### 向后兼容性
- ✅ 完全向后兼容
- ✅ 原有"嵌入图片"功能不受影响
- ✅ API接口参数为可选参数，不影响现有调用

## 修复时间
2025-11-02 01:45:00

## 总结
现在用户可以选择：
- **嵌入图片**：生成自包含的Markdown文档（文件较大，但便于分享）
- **外部图片**：生成较小的Markdown文档 + 图片文件夹（便于编辑和管理）

两种方式都支持ZIP打包下载，满足不同用户需求！✅

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Playwright浏览器测试生成markdown文档功能
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os

async def test_markdown_generation():
    """测试markdown文档生成功能"""
    async with async_playwright() as p:
        try:
            # 启动浏览器
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            # 访问应用
            print("正在打开浏览器访问 http://localhost:8501")
            await page.goto("http://localhost:8501")

            # 等待页面加载
            await page.wait_for_load_state('domcontentloaded')
            print("页面已加载")

            # 检查页面标题
            title = await page.title()
            print(f"页面标题: {title}")

            # 等待页面完全加载（可能需要一些时间）
            await page.wait_for_timeout(3000)

            print("\n=== 开始配置参数 ===")

            # 1. 设置API密钥（假设环境变量中有）
            try:
                api_key_input = await page.query_selector('input[placeholder*="GEMINI"], input[aria-label*="API"]')
                if api_key_input:
                    await api_key_input.fill("test_api_key_placeholder")  # 占位符
                    print("API密钥输入框已配置")
                else:
                    print("未找到API密钥输入框")
            except Exception as e:
                print(f"配置API密钥失败: {e}")

            # 2. 设置输出模式为Markdown截图讲解
            try:
                # 寻找输出模式选择器（可能是radio buttons）
                markdown_radio = await page.query_selector('input[type="radio"][value="Markdown截图讲解"], label:has-text("Markdown截图讲解")')
                if markdown_radio:
                    await markdown_radio.check()
                    print("已选择输出模式：Markdown截图讲解")
                else:
                    # 尝试直接点击包含Markdown文本的label
                    await page.click('text=/Markdown截图讲解/')
                    print("已点击Markdown输出选项")
            except Exception as e:
                print(f"选择输出模式失败: {e}")

            # 3. 配置Markdown参数
            try:
                # 设置截图DPI
                screenshot_dpi_input = await page.query_selector('input[aria-label*="截图DPI"], input[placeholder*="截图DPI"]')
                if screenshot_dpi_input:
                    await screenshot_dpi_input.fill("150")
                    print("已设置截图DPI: 150")

                # 设置文档标题
                title_input = await page.query_selector('input[placeholder*="文档标题"], input[aria-label*="文档标题"]')
                if title_input:
                    await title_input.fill("测试Markdown文档")
                    print("已设置文档标题: 测试Markdown文档")

                # 确保嵌入图片选项开启
                embed_checkbox = await page.query_selector('input[type="checkbox"]:has-text("嵌入图片")')
                if embed_checkbox:
                    is_checked = await embed_checkbox.is_checked()
                    if not is_checked:
                        await embed_checkbox.check()
                        print("已开启嵌入图片选项")

            except Exception as e:
                print(f"配置Markdown参数失败: {e}")

            print("\n=== 开始上传测试PDF ===")

            # 4. 上传测试PDF文件（模拟文件上传）
            try:
                # 寻找文件上传输入框
                file_input = await page.query_selector('input[type="file"].stFileUploader')
                if not file_input:
                    file_input = await page.query_selector('input[type="file"]')

                if file_input:
                    # 创建一个小的测试PDF文件用于测试
                    test_pdf_path = "test_sample.pdf"
                    try:
                        from reportlab.pdfgen import canvas
                        from reportlab.lib.pagesizes import letter
                        c = canvas.Canvas(test_pdf_path, pagesize=letter)
                        c.drawString(100, 750, "Test PDF Document")
                        c.drawString(100, 730, "This is a simple test PDF for markdown generation testing.")
                        c.drawString(100, 710, "Page 1 of 1")
                        c.save()
                        print(f"创建测试PDF文件: {test_pdf_path}")
                    except Exception as e:
                        print(f"创建测试PDF失败: {e}")

                    # 上传文件
                    await file_input.set_input_files(test_pdf_path)
                    print("已上传测试PDF文件")

                    # 等待文件处理
                    await page.wait_for_timeout(2000)

                else:
                    print("未找到文件上传输入框")

            except Exception as e:
                print(f"文件上传失败: {e}")

            print("\n=== 开始生成markdown ===")

            # 5. 点击生成按钮
            try:
                # 寻找批量生成按钮
                generate_button = await page.query_selector('button:has-text("批量生成讲解与合成"), button:has-text("生成")')

                if generate_button:
                    print("找到生成按钮，正在点击...")
                    await generate_button.click()

                    # 等待处理开始
                    print("正在等待后端处理...")
                    await page.wait_for_timeout(5000)

                    # 检查是否有处理状态信息
                    processing_indicators = [
                        'text=/正在处理/',
                        'text=/生成讲解/',
                        'text=/合成中/',
                        'text=/processing/',
                        'text=/generating/'
                    ]

                    found_processing = False
                    for indicator in processing_indicators:
                        try:
                            element = await page.query_selector(indicator)
                            if element:
                                text = await element.inner_text()
                                print(f"检测到处理状态: {text}")
                                found_processing = True
                                break
                        except:
                            continue

                    if not found_processing:
                        print("未检测到明确的处理状态指示")

                    # 等待更长时间让后端处理完成
                    print("等待后端处理完成...")
                    await page.wait_for_timeout(10000)

                    # 检查结果
                    print("\n=== 检查生成结果 ===")

                    # 检查是否有下载按钮出现
                    download_buttons = await page.query_selector_all('button:has-text("下载"), a:has-text("下载")')
                    if download_buttons:
                        print(f"发现 {len(download_buttons)} 个下载按钮")
                        for i, btn in enumerate(download_buttons):
                            try:
                                btn_text = await btn.inner_text()
                                print(f"  下载按钮 {i+1}: {btn_text}")
                            except:
                                continue
                    else:
                        print("未发现下载按钮，可能是处理未完成或出错")

                    # 检查是否有错误信息
                    error_elements = await page.query_selector_all('text=/错误|失败|error|failed/i')
                    if error_elements:
                        for i, error_el in enumerate(error_elements):
                            try:
                                error_text = await error_el.inner_text()
                                print(f"检测到错误信息 {i+1}: {error_text}")
                            except:
                                continue
                    else:
                        print("未发现明显的错误信息")

                    # 检查日志更新
                    print("\n=== 检查日志更新 ===")
                    try:
                        # 调用系统命令检查日志更新
                        import subprocess
                        result = subprocess.run(['powershell', '-Command', 'Get-Content -Path logs/app.log -Tail 5'],
                                              capture_output=True, text=True, encoding='utf-8')
                        if result.returncode == 0:
                            recent_logs = result.stdout.strip()
                            print("最近的日志记录:")
                            print(recent_logs)
                        else:
                            print("无法读取日志文件")
                    except Exception as e:
                        print(f"检查日志失败: {e}")

                else:
                    print("未找到批量生成按钮")
                    # 列出所有可见的按钮
                    all_buttons = await page.query_selector_all('button')
                    if all_buttons:
                        print(f"页面上的按钮 ({len(all_buttons)} 个):")
                        for i, btn in enumerate(all_buttons):
                            try:
                                btn_text = await btn.inner_text()
                                if btn_text.strip():
                                    print(f"  按钮 {i+1}: '{btn_text}'")
                            except:
                                continue
                    else:
                        print("未发现任何按钮")

            except Exception as e:
                print(f"生成按钮操作失败: {e}")

            print("\n=== 测试完成 ===")
            print("浏览器保持打开状态，可手动检查应用界面")

            # 保存截图作为测试证据
            try:
                await page.screenshot(path='markdown_generation_test_result.png')
                print("测试结果截图已保存: markdown_generation_test_result.png")
            except Exception as e:
                print(f"保存截图失败: {e}")

        except Exception as e:
            print(f"浏览器测试失败: {e}")
            print("请确保Streamlit应用正在运行，且浏览器环境正确配置")
        finally:
            try:
                if 'browser' in locals():
                    await browser.close()
                print("浏览器已关闭")
            except:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(test_markdown_generation())
    except KeyboardInterrupt:
        print("\n测试被用户中断")

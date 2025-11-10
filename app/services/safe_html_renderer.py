import asyncio
import sys
import threading
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import time
from .logger import get_logger
logger = get_logger()

def safe_render_html_to_pdf_fragment(html: str, width_pt: float, height_pt: float,
                                   css: Optional[str] = None, background: str = "white",
                                   mathjax: bool = True, prism: bool = True,
                                   timeout: int = 30):
    """
    在Streamlit环境中安全渲染HTML到PDF的包装器函数
    使用独立的线程和事件循环，避免与Streamlit冲突
    """
    logger.info('Safe render html to pdf fragment, html_len=%d, width_pt=%.1f, height_pt=%.1f, timeout=%d', len(html or ''), width_pt, height_pt, timeout)
    # 检测是否在Streamlit环境中（使用安全的检测方式，避免触发 ScriptRunContext 检查）
    streamlit_env = False
    try:
        import streamlit as st
        # 使用更安全的方式检测 Streamlit 环境，避免在后台线程中触发 ScriptRunContext 检查
        # 检查模块是否存在，而不是调用 runtime.exists()（这会触发上下文检查）
        streamlit_env = hasattr(st, 'runtime') and hasattr(st.runtime, 'exists')
        # 只有在主线程中才调用 exists()，避免后台线程中的警告
        if streamlit_env:
            try:
                from streamlit.runtime.scriptrunner import get_script_run_ctx
                ctx = get_script_run_ctx()
                # 只有在有有效上下文且在主线程时才调用 exists()
                if ctx is not None and hasattr(ctx, 'session_id') and ctx.session_id is not None:
                    streamlit_env = st.runtime.exists()
                else:
                    # 在后台线程中，假设 Streamlit 环境存在（但不调用 exists()）
                    # 使用更保守的检查
                    streamlit_env = False  # 在后台线程中，假设不在Streamlit环境中以避免警告
            except (ImportError, AttributeError, RuntimeError, TypeError):
                # 无法获取上下文，假设不在 Streamlit 环境中
                streamlit_env = False
    except ImportError:
        pass

    if not streamlit_env:
        logger.debug('Non-Streamlit env, call html_renderer.HtmlRenderer.render_html_to_pdf_fragment')
        # 非Streamlit环境，直接调用原始函数
        from .html_renderer import HtmlRenderer
        return HtmlRenderer.render_html_to_pdf_fragment(
            html=html,
            width_pt=width_pt,
            height_pt=height_pt,
            css=css,
            background=background,
            mathjax=mathjax,
            prism=prism
        )

    # Streamlit环境下的特殊处理：使用独立的线程执行渲染
    result = [None]
    exception = [None]

    def _render_in_thread():
        """在独立线程中执行渲染"""
        try:
            # 为当前线程创建新的独立事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 设置Windows兼容的事件循环策略
            if sys.platform.startswith("win"):
                try:
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                except Exception:
                    pass

            # 执行渲染
            from .html_renderer import HtmlRenderer
            pdf_bytes = HtmlRenderer.render_html_to_pdf_fragment(
                html=html,
                width_pt=width_pt,
                height_pt=height_pt,
                css=css,
                background=background,
                mathjax=mathjax,
                prism=prism
            )
            result[0] = pdf_bytes
            logger.debug('Threaded HTML render success')

        except Exception as e:
            logger.error('Threaded HTML render failed: %s', e, exc_info=True)
            exception[0] = e
        finally:
            try:
                if loop and not loop.is_closed():
                    loop.close()
            except Exception:
                pass

    # 使用线程池执行渲染，带超时
    try:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="pdf_render") as executor:
            future = executor.submit(_render_in_thread)
            # 等待完成，最多等待timeout秒
            future.result(timeout=timeout)

        if exception[0]:
            logger.error('HTML render raised exception: %s', exception[0], exc_info=True)
            raise exception[0]
        if result[0] is None:
            logger.error('Thread render result is None')
            raise RuntimeError("渲染函数返回空结果")
        logger.info('Safe render html to pdf fragment finished')
        return result[0]

    except FutureTimeoutError:
        logger.error('HTML渲染超时(%d秒)', timeout)
        raise RuntimeError(f"HTML渲染超时({timeout}秒)，可能是Playwright卡住")
    except Exception as e:
        logger.error('HTML渲染失败：%s', e, exc_info=True)
        raise

# 为了向后兼容，保留原始函数并添加安全包装器

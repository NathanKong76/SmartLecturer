import asyncio
import sys
from .logger import get_logger
logger = get_logger()

def sync_batch_recompose_from_json(pdf_files, json_files, font_size, **kwargs):
    logger.info('Sync batch recompose from json, pdf_files=%d, json_files=%d', len(pdf_files), len(json_files))
    try:
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from app.services import pdf_processor
            logger.debug('Calling async batch_recompose_from_json')
            return loop.run_until_complete(
                pdf_processor.batch_recompose_from_json_async(pdf_files, json_files, font_size, **kwargs)
            )
        finally:
            loop.close()
    except Exception as e:
        logger.error('Sync batch recompose failed: %s', e, exc_info=True)
        print(f"同步执行失败: {e}，尝试其他方法...")
        raise

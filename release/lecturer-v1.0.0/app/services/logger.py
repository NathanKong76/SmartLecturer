import logging
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'logs')
LOG_PATH = os.path.join(LOG_DIR, 'app.log')

os.makedirs(LOG_DIR, exist_ok=True)

# 保证文件用utf-8无BOM写入
class UTF8NoBOMFileHandler(logging.FileHandler):
    def _open(self):
        return open(self.baseFilename, self.mode, encoding='utf-8', newline='')

formatter = logging.Formatter(
    fmt='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

handler = UTF8NoBOMFileHandler(LOG_PATH, mode='a', encoding='utf-8')
handler.setFormatter(formatter)

logger = logging.getLogger('app_log')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.propagate = False

def get_logger():
    return logger

import time

from app import db
from app.oxford import Pronunciation, WordNotFound
from app.config import get_logger, get_settings


LOG = get_logger()
settings = get_settings()


def __download_pronunciation():
    word = db.redis_connection.lpop(settings.REDIS_PRONUNCIATION_QUEUE_KEY)
    if word is None:
        time.sleep(1)
        LOG.info(f"[worker] queue is empty")
        return
    try:  # download pronunciation
        pronunciation = Pronunciation(word, settings.PRONUNCIATION_DIR)
        pronunciation.download("us")
        pronunciation.download("uk")
        LOG.info(f"[worker] finish download pronunciation: {word}")
    except WordNotFound:
        LOG.info(f"[worker] word pronunciation not found: {word}")
    except:
        LOG.info(f"[worker] get word pronunciation failed: {word}")


def run_worker():
    while True:
        __download_pronunciation()

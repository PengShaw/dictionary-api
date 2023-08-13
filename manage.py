import fire
from sqlmodel import Session

from app import db
from app.oxford import Oxford, WordNotFound, Pronunciation
from app.config import get_logger, get_settings


LOG = get_logger()
settings = get_settings()


def run_server():
    from app.server import app

    db.init_database()
    app.run(
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        debug=settings.DEBUG,
    )


def run_worker():
    from app.worker import run_worker

    run_worker()


def init_database_data(input_filepath="./tests/words.txt"):
    db.init_database()
    with open(input_filepath, "r") as f:
        lines = f.readlines()
        words = [line.strip() for line in lines]
    with Session(db.engine) as session:
        for word in words:
            vocabulary = db.vocabulary_crud.get_by_word(session, word=word)
            if vocabulary is not None:
                continue
            try:  # insert word into db
                oxford_word = Oxford(word)
                LOG.info(f"finish get from oxford: {word}")
                vocabulary = db.vocabulary_crud.create_by_oxford_word(
                    session, word=oxford_word
                )
                LOG.info(f"finish insert to db: {word}")
            except WordNotFound:
                LOG.info(f"word not found: {word}")
            except:
                LOG.info(f"get word failed: {word}")
            try:  # download pronunciation
                pronunciation = Pronunciation(
                    oxford_word.word, settings.PRONUNCIATION_DIR
                )
                pronunciation.download("us")
                pronunciation.download("uk")
                LOG.info(f"finish download pronunciation: {word}")
            except WordNotFound:
                LOG.info(f"word pronunciation not found: {word}")
            except:
                LOG.info(f"get word pronunciation failed: {word}")


if __name__ == "__main__":
    fire.Fire(
        {
            "init_database_data": init_database_data,
            "run_server": run_server,
            "run_worker": run_worker,
        }
    )

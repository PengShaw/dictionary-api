from typing import Optional

from sqlmodel import create_engine, SQLModel, Session, select, func
import redis

from app.config import get_settings, get_logger
from app.models import Vocabulary, VocabularyDefinition, Wordform
from app.oxford import Oxford

LOG = get_logger()

engine = create_engine(get_settings().SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
redis_connection = redis.Redis(
    host=get_settings().REDIS_HOST,
    port=get_settings().REDIS_PORT,
    password=get_settings().REDIS_PASSWORD,
    db=get_settings().REDIS_DB_QUEUE,
    decode_responses=True,
)


def init_database():
    SQLModel.metadata.create_all(engine)
    LOG.debug("Finish database initation")


class CRUDVocabulary:
    def get_by_word(self, db: Session, *, word: str) -> Optional[Vocabulary]:
        return db.query(Vocabulary).filter(Vocabulary.word == word).first()

    def __get_wordform_id(self, db: Session, *, wordform: str | None) -> int | None:
        if wordform is None:  # if not wordform, then wordform_id is None
            return None
        wordform_db: Wordform = (
            db.query(Wordform).filter(Wordform.wordform == wordform).first()
        )
        if wordform_db is None:  # if not wordform in db, then create it
            LOG.debug(f"wordform[{wordform}] is not found in db, create it now")
            wordform_db = Wordform(wordform=wordform)
            db.add(wordform_db)
            wordform_db = (
                db.query(Wordform).filter(Wordform.wordform == wordform).first()
            )
        return wordform_db.id

    def create_by_oxford_word(self, db: Session, *, word: Oxford) -> Vocabulary:
        # add vocabulary to db
        vocabulary_db = Vocabulary(
            headword=word.headword,
            word=word.word,
            us_phonetic=word.us_phonetic,
            uk_phonetic=word.uk_phonetic,
        )
        db.add(vocabulary_db)
        vocabulary_db = self.get_by_word(db, word=word.word)
        for definition in word.definitions:
            wordform_id = self.__get_wordform_id(db, wordform=definition["wordform"])
            # add definition to db
            vocabulary_definition_db = VocabularyDefinition(
                namespace=definition["namespace"],
                property=definition["property"],
                description=definition["description"],
                vocabulary_id=vocabulary_db.id,
                wordform_id=wordform_id,
            )
            db.add(vocabulary_definition_db)
        LOG.debug(f"create vocabulary[{word.word}] into db, commit it now")
        db.commit()
        return self.get_by_word(db, word=word.word)

    def count_all(self, db: Session) -> int:
        return db.exec(select(func.count(Vocabulary.id))).one()


vocabulary_crud = CRUDVocabulary()

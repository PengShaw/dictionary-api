from typing import List, Optional

from flask import Flask, jsonify, render_template, send_from_directory, abort
from sqlmodel import Session, SQLModel, Field

from app import db
from app.config import get_settings
from app.oxford import Oxford, WordNotFound, Pronunciation


settings = get_settings()

app = Flask(__name__)


class WordforReadSchema(SQLModel):
    id: int = Field(default=None, primary_key=True)
    wordform: str = Field(unique=True, index=True)


class VocabularyDefinitionReadSchema(SQLModel):
    id: int = Field(default=None, primary_key=True)
    namespace: Optional[str]
    property: Optional[str]
    description: Optional[str]
    wordform: Optional["WordforReadSchema"]


class VocabularyReadSchema(SQLModel):
    id: int = Field(default=None, primary_key=True)
    headword: str = Field(unique=True, index=True)
    word: str = Field(index=True)
    us_phonetic: str
    uk_phonetic: str
    us_pronunciation: Optional[str]
    uk_pronunciation: Optional[str]
    vocabulary_definitions: List["VocabularyDefinitionReadSchema"] = []


@app.route("/")
def home():
    with Session(db.engine) as session:
        count = db.vocabulary_crud.count_all(session)
        example_word = "hello"
        vocabuldry_db = db.vocabulary_crud.get_by_word(session, word=example_word)
        base_url = settings.BASE_HOSTNAME_URL
        if not base_url.endswith("/"):
            base_url += "/"
        example_url = f"{base_url}api/v1{example_word}"
        example_result: VocabularyReadSchema = VocabularyReadSchema.from_orm(
            vocabuldry_db
        ).json()
        example_result.uk_pronunciation = (
            f"{base_url}/api/v1/pronunciation/uk/{example_word}"
        )
        example_result.us_pronunciation = (
            f"{base_url}api/v1/pronunciation/us/{example_word}"
        )
    return render_template(
        "index.html",
        count=count,
        example_url=example_url,
        example_result=example_result,
    )


@app.route("/api/v1/<word>")
def get_word(word):
    base_url = settings.BASE_HOSTNAME_URL
    if not base_url.endswith("/"):
        base_url += "/"

    with Session(db.engine) as session:
        vocabuldry_db = db.vocabulary_crud.get_by_word(session, word=word)
        if vocabuldry_db is None:
            oxford_word = Oxford(word)
            vocabuldry_db = db.vocabulary_crud.create_by_oxford_word(
                session, word=oxford_word
            )
            # insert to redis for updating pronounceation
            db.redis_connection.rpush(
                settings.REDIS_PRONUNCIATION_QUEUE_KEY, vocabuldry_db.word
            )
        vocabuldry_db = VocabularyReadSchema.from_orm(vocabuldry_db)
        vocabuldry_db.uk_pronunciation = (
            f"{base_url}/api/v1/pronunciation/uk/{vocabuldry_db.word}"
        )
        vocabuldry_db.us_pronunciation = (
            f"{base_url}api/v1/pronunciation/us/{vocabuldry_db.word}"
        )
    return jsonify(vocabuldry_db.json())


@app.route("/api/v1/pronunciation/<country>/<word>")
def get_pronunciation(country, word):
    if country not in ["us", "uk"]:
        abort(404)
    pronunciation = Pronunciation(word, settings.PRONUNCIATION_DIR)
    if country == "us":
        dir = pronunciation.us_dir
    else:
        dir = pronunciation.uk_dir
    return send_from_directory(dir, f"{word}.mp3")


@app.errorhandler(500)
def server_error(error):
    return "Server Error..."


@app.errorhandler(404)
def page_not_found(error):
    return "Page Not Found..."


@app.errorhandler(WordNotFound)
def word_not_found(error):
    return jsonify({"code": 404, "msg": "word not found"})

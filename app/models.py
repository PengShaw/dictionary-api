from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship


class Vocabulary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    headword: str = Field(unique=True, index=True)
    word: str = Field(index=True)
    us_phonetic: str
    uk_phonetic: str

    vocabulary_definitions: List["VocabularyDefinition"] = Relationship(
        back_populates="vocabulary"
    )


class Wordform(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    wordform: str = Field(unique=True, index=True)

    vocabulary_definitions: List["VocabularyDefinition"] = Relationship(
        back_populates="wordform"
    )


class VocabularyDefinition(SQLModel, table=True):
    __tablename__: str = "vocabulary_definition"

    id: Optional[int] = Field(default=None, primary_key=True)
    namespace: Optional[str]
    property: Optional[str]
    description: Optional[str]

    wordform_id: Optional[int] = Field(default=None, foreign_key="wordform.id")
    wordform: Optional[Wordform] = Relationship(back_populates="vocabulary_definitions")

    vocabulary_id: Optional[int] = Field(default=None, foreign_key="vocabulary.id")
    vocabulary: Optional["Vocabulary"] = Relationship(
        back_populates="vocabulary_definitions"
    )

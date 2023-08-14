import os
import logging
from typing import TypedDict, List

import requests
from bs4 import BeautifulSoup, ResultSet, Tag

from app.config import get_logger


LOG = get_logger()


class WordNotFound(Exception):
    """word not found in dictionary"""

    pass


class WordDefinitionType(TypedDict):
    wordform: str | None
    namespace: str | None
    property: str | None
    description: str | None


class Oxford:
    __request_headers = {
        "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    __request_time_out = 5
    __base_url = "https://www.oxfordlearnersdictionaries.com/definition/english/"

    def __init__(self, word: str):
        self.word = word.lower()
        self.headword: str = None
        self.us_phonetic: str = None
        self.uk_phonetic: str = None
        self.definitions: List[WordDefinitionType] = []
        self.__init_data()

    def __init_data(self):
        i = 1
        # query word_1, word_2, and so on
        while True:
            LOG.debug(f"begin to get word: {self.word}_{i}")
            url = f"{self.__base_url}{self.word}_{i}"
            req = requests.get(
                url, timeout=self.__request_time_out, headers=self.__request_headers
            )
            # stop loop when page not found
            if req.status_code != 200:
                break
            # init data
            soup = BeautifulSoup(req.content, "html.parser")
            if i == 1:  # init headword, us_phonetic, uk_phonetic only once
                self.headword = self.__parse_headword(soup)
                self.us_phonetic = self.__parse_us_phonetic(soup)
                self.uk_phonetic = self.__parse_uk_phonetic(soup)
            self.__init_definitions(soup)
            i += 1

        # word not found, raise Exception
        if i == 1:
            raise WordNotFound
        return

    def __parse_headword(self, soup: BeautifulSoup) -> str:
        selector = ".top-container .headword"
        res = soup.select(selector)[0].text
        LOG.debug(f"get {self.word} headword: {res}")
        return res

    def __parse_us_phonetic(self, soup: BeautifulSoup) -> str:
        selector = "[geo=n_am] .phon"
        res = soup.select(selector)[0].text
        LOG.debug(f"get {self.word} us_phonetic: {res}")
        return res

    def __parse_uk_phonetic(self, soup: BeautifulSoup) -> str:
        selector = "[geo=br] .phon"
        res = soup.select(selector)[0].text
        LOG.debug(f"get {self.word} uk_phonetic: {res}")
        return res

    def __init_definitions(self, soup: BeautifulSoup):
        # get wordform data
        try:
            wordform = soup.select(".top-container .pos")[0].text
        except IndexError:
            # some words do not wordform, e.g. time_3
            wordform = None
        LOG.debug(f"get {self.word} wordform: {wordform}")
        # get sense data from senses_multiple or sense_single class
        sense_tag = soup.find(attrs={"class": "senses_multiple"}) or soup.find(
            attrs={"class": "sense_single"}
        )
        if sense_tag is None:  # some words without definitions, e.g. accustom
            LOG.debug(f"get {self.word} without definitions")
            return
        # some words (e.g. run_1) have similar definitions grouped in a multiple namespaces
        namespaces_tags = sense_tag.select(".shcut-g")
        for namespace_tag in namespaces_tags:
            namespace = namespace_tag.select("h2.shcut")[0].text
            LOG.debug(f"get {self.word} namespace: {namespace}")
            senses_tags = namespace_tag.select(".sense")
            self.definitions.extend(
                self.__parse_definitions(senses_tags, namespace, wordform)
            )
        # some words (e.g. woman) do not have a namespace
        if len(namespaces_tags) == 0:
            senses_tags = sense_tag.select(".sense")
            self.definitions.extend(
                self.__parse_definitions(senses_tags, None, wordform)
            )
        return

    def __parse_definitions(
        self, senses_tags: ResultSet[Tag], namespace: str, wordform: str
    ) -> List[WordDefinitionType]:
        definitions = []
        for sense_tag in senses_tags:
            definition: WordDefinitionType = {}
            definition["wordform"] = wordform
            definition["namespace"] = namespace

            try:  # property (countable, transitive, plural,...)
                definition["property"] = sense_tag.select(".grammar")[0].text
            except IndexError:
                definition["property"] = None

            try:  # sometimes, it just refers to other page without having a definition
                definition["description"] = sense_tag.select(".def")[0].text
            except IndexError:
                definition["description"] = None

            LOG.debug(f"get {self.word} definition: {definition}")
            definitions.append(definition)

        return definitions


class Pronunciation:
    def __init__(self, word: str, data_dir: str):
        self.word = word.lower()
        if not data_dir.endswith("/"):
            data_dir += "/"
        self.us_dir = data_dir + "us/"
        self.uk_dir = data_dir + "uk/"
        if not os.path.exists(self.us_dir):
            os.makedirs(self.us_dir)
        if not os.path.exists(self.uk_dir):
            os.makedirs(self.uk_dir)
        self.us_filepath = data_dir + "us/" + self.word + ".mp3"
        self.uk_filepath = data_dir + "uk/" + self.word + ".mp3"

    def download(self, country: str):
        if country not in ["us", "uk"]:
            raise f"country[{country}] is not us or uk"
        if country == "us":
            url = "http://dict.youdao.com/dictvoice?type=0&audio="
            filepath = self.us_filepath
        else:
            url = "http://dict.youdao.com/dictvoice?type=1&audio="
            filepath = self.uk_filepath

        if os.path.exists(filepath):
            LOG.debug(
                f"{self.word} {country} pronunciation exists, not update: {filepath}"
            )
            return

        req = requests.get(
            url + self.word,
            headers={
                "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            },
        )
        if req.status_code != 200:
            raise WordNotFound
        with open(filepath, "wb") as f:
            f.write(req.content)
        LOG.debug(f"save {self.word} {country} pronunciation: {filepath}")


if __name__ == "__main__":
    import sys

    LOG = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    LOG.addHandler(handler)

    # LOG.setLevel(logging.DEBUG)
    # word = Oxford("accustom")
    # word = Oxford("amount")

    LOG.setLevel(logging.INFO)
    with open("./tests/words.txt", "r") as f:
        lines = f.readlines()
        words = [line.strip() for line in lines]

    for word in words:
        try:
            Oxford(word)
            LOG.info(f"finish: {word}")
        except WordNotFound:
            LOG.info(f"word not found: {word}")
        except:
            LOG.info(f"get word failed: {word}")

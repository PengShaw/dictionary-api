# docker build -t dictionary-api .
FROM python:3.11

WORKDIR /dictionary-api
COPY ./requirements.lock /dictionary-api/
RUN sed '/-e/d' requirements.lock > requirements.txt
RUN pip install -r requirements.txt

COPY ./app /dictionary-api/app
COPY ./manage.py /dictionary-api/

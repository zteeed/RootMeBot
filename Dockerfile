FROM python:3.7

COPY ./requirements.txt .
RUN pip install -r requirements.txt
COPY ./ .

ENV BOT_CHANNEL root-me-news
ENV TOKEN token

CMD python3 main.py

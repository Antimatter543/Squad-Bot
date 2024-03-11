FROM python:3.10-alpine as compile-image

# update and install environment dependancies
RUN apk update \
    && apk add --no-cache --virtual build-deps gcc python3-dev py3-virtualenv py3-pip musl-dev \
    && apk del build-deps \
    && rm -rf /var/cache/apk/*

# create virtual environment

RUN python3 -m venv /opt/venv
ENV PATH "/opt/venv/bin:$PATH"

# install python requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

FROM python:3.10-alpine

# update and install environment dependancies
RUN apk update \
    && apk add --no-cache --virtual py3-virtualenv py3-pip \
    && rm -rf /var/cache/apk/*

COPY --from=compile-image /opt/venv /opt/venv

RUN adduser -D discord
USER discord
WORKDIR /home/discord

ENV VIRTUAL_ENV /opt/venv
ENV PATH "/opt/venv/bin:$PATH"  
# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "${PYTHONPATH}:/home/discord/bot"

COPY bot /home/discord/bot/
COPY run.py /home/discord/

ENTRYPOINT [ "python3","./run.py" ]
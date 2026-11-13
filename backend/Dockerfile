FROM python:3.12-slim-bookworm AS base

LABEL maintainer Udayan Manna <udayan.m@deductiveclouds.com>

ENV PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /code

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
    libpq-dev \
    gcc \
    file \
    make \
    libc-dev && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

ADD ./requirements/base.txt /tmp
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r /tmp/base.txt

EXPOSE 80

FROM base AS dev

ADD ./requirements/dev.txt /tmp
RUN pip3 install --no-cache-dir -r /tmp/dev.txt

FROM dev AS test

COPY ./ ./

FROM base AS dist

COPY ./ ./
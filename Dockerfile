FROM ubuntu:18.04

# At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
ENV LANG C.UTF-8

ENV PYTHONUNBUFFERED 1

# Requirements have to be pulled and installed here, otherwise caching won't work
COPY ./requirements /requirements

# Install Python OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-dev \
        python3-pip \
        python3-setuptools \
        locales \
        tzdata

# Setup locales
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen

# Setup timezone
ENV TZ=Asia/Bangkok
RUN echo "Asia/Bangkok" > /etc/timezone && \
    rm /etc/localtime && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Upgrade PIP to latest version
RUN pip3 install --upgrade pip
RUN pip3 install -r /requirements/base.txt

WORKDIR /app



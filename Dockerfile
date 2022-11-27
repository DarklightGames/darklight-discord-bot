# syntax=docker/dockerfile:1.2

ARG PYTHON_VERSION=3.11

# STAGE 1: Build dependencies

FROM python:${PYTHON_VERSION}-alpine as builder

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apk update \
    && apk add --no-cache --upgrade gcc musl-dev python3-dev

WORKDIR /wheels

COPY ./requirements.txt /wheels/
RUN echo uvloop >> /wheels/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip wheel -r requirements.txt

# STAGE 2: Final image

FROM python:${PYTHON_VERSION}-alpine

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install dependencies
COPY --from=builder /wheels /wheels
RUN pip install --upgrade pip \
    && pip install --no-cache -r /wheels/requirements.txt -f /wheels \
    && rm -rf /wheels

# Create the app user
ENV APP_USER=app
RUN addgroup -S $APP_USER && adduser -S $APP_USER -G $APP_USER
USER $APP_USER

# Copy the app files and link secrets
ENV APP_HOME=/home/${APP_USER}/src
WORKDIR $APP_HOME
COPY --chown=${APP_USER}:${APP_USER} . $APP_HOME
RUN ln -s /run/secrets ${APP_HOME}/secrets

CMD [ "python3", "-OO", "-m", "bot"]
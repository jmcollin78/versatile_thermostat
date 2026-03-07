FROM python:3.14-bookworm

USER root
RUN apt update && apt install -y ffmpeg libturbojpeg0-dev git curl jq vim && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash vscode
USER vscode

ENV PATH=/home/vscode/.local/bin:$PATH

WORKDIR /workspace

FROM python:3.14-bookworm

USER root
RUN apt update && apt install -y ffmpeg libturbojpeg0-dev git gh curl jq vim ca-certificates && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash vscode
USER vscode

ENV PATH=/home/vscode/.local/bin:$PATH

RUN curl -fsSL https://openspec.dev/cli/install.sh | sh \
    && curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh \
    && openspec --version \
    && rtk --version

WORKDIR /workspace

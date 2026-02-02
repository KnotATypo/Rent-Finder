FROM ghcr.io/astral-sh/uv:debian-slim

RUN apt update && \
    apt install -y --no-install-recommends chromium chromium-driver xvfb xauth x11-utils && \
    apt autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /rent-finder
WORKDIR /rent-finder
COPY . .

ENTRYPOINT ["/rent-finder/entrypoint.sh"]
CMD ["uv", "run", "--env-file", ".env", "search"]
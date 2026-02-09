FROM ghcr.io/astral-sh/uv:debian-slim

RUN apt update && \
    apt install -y --no-install-recommends chromium chromium-driver && \
    apt autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir /rent-finder

WORKDIR /rent-finder
COPY . .

ENV PYTHONBUFFERED=1

ENTRYPOINT ["uv", "run", "host"]
# See entrypoint.sh for comment
#ENTRYPOINT ["/rent-finder/entrypoint.sh"]
#CMD ["uv", "run", "host"]
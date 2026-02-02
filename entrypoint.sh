#!/bin/sh

# Unsure why, but running "xvfb-run -a" as the entrypoint breaks it
xvfb-run -a "$@"
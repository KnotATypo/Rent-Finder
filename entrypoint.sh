#!/bin/sh

# The display needs to be create manually since the scheduler runs the "search" process outside of the "host" process
Xvfb :99 -screen 0 1920x1080x24 -ac &
exec "$@"
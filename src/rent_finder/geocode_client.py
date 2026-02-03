import os
import re
import time

import requests

from rent_finder.logger import logger


class StatusException(Exception):
    pass


class GeocodeClient:
    last_request: float
    api_key = os.getenv("GEOCODE_API_KEY")

    def __init__(self):
        self.last_request = time.time()

    def get_coordinate(self, address: str) -> tuple[None, None] | tuple[float, float]:
        if "/" in address:
            address = address[address.index("/") + 1 :]
        elif re.match(r"^\d+ \d", address):
            address = address[address.index(" ") + 1 :]

        response = requests.get(f"https://geocode.maps.co/search?q={address}&api_key={self.api_key}")
        self.last_request = time.time()

        if response.status_code != 200:
            raise StatusException(f"{response.status_code}: {response.text}")

        response = response.json()
        if len(response) == 0:
            logger.error(f"{address} - Geocode: No results found")
            return None, None
        elif len(response) == 1:
            return float(response[0]["lat"]), float(response[0]["lon"])
        else:
            for location in response:
                if "suburb" not in location["address"]:
                    continue
                if location["address"]["suburb"].lower() in address.lower():
                    return float(location["lat"]), float(location["lon"])
            logger.error(f"{address} - Geocode: Multiple results found")
            return None, None

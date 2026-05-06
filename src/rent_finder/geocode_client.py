import os
import re
from datetime import datetime, timedelta
from time import sleep

import requests

from rent_finder.logger import logger


class StatusException(Exception):
    pass


class GeocodeClient:
    """
    Client to forward geocode addresses to coordinates using https://geocode.maps.co/.
    """

    api_key: str
    rate_limit_start: datetime
    last_request: datetime

    def __init__(self) -> None:
        key = os.getenv("GEOCODE_API_KEY")
        if key is None:
            raise RuntimeError("GEOCODE_API_KEY not set")

        self.api_key = key
        self.rate_limit_start = datetime.min
        self.last_request = datetime.min

    def get_coordinate(self, address: str) -> tuple[None, None] | tuple[float, float]:
        """
        Get the coordinates for a given address.

        :param address: A standard street address.
        :return: Returns a tuple (lat, lon) of the coordinate or (None, None) if no coordinates found.
        """
        if "/" in address:
            address = address[address.index("/") + 1 :]
        elif re.match(r"^\d+ \d", address):
            address = address[address.index(" ") + 1 :]

        if self.rate_limit_start > datetime.now() - timedelta(hours=12):
            # If it has been less than 12 hours since we hit a rate limit, make sure we respect limits
            sleep(1 - ((self.last_request - datetime.now()).microseconds / 1e-6))

        response = None
        while response is None:
            self.last_request = datetime.now()
            response = requests.get(f"https://geocode.maps.co/search?q={address}&api_key={self.api_key}")

            if response.status_code == 429:
                logger.warning("Geocode: Rate limit reached")
                self.rate_limit_start = datetime.now()
                sleep(1)
                response = None
            elif response.status_code == 503:
                logger.warning("Geocode: Service unavailable, retrying")
                # High server load, pause then try again
                sleep(5)
                response = None
            elif response.status_code != 200:
                raise StatusException(f"{response.status_code}: {response.text}")

        response = response.json()
        if len(response) == 0:
            logger.error(f"{address} - Geocode: No results found")
            return None, None
        elif len(response) == 1:
            return float(response[0]["lat"]), float(response[0]["lon"])
        else:
            logger.debug(f"{address} - Geocode: More than one results found")
            lat, long = self._resolve_duplicates(response, address)
            if lat is None or long is None:
                logger.error(f"{address} - Geocode: Could not resolve duplicate coordinates")
            return lat, long

    def _resolve_duplicates(self, locations, address: str) -> tuple[float, float] | tuple[None, None]:
        for location in locations:
            if "suburb" in location["address"]:
                if location["address"]["suburb"].lower() in address.lower():
                    return float(location["lat"]), float(location["lon"])
            elif "town" in location["address"]:
                if location["address"]["town"].lower() in address.lower():
                    return float(location["lat"]), float(location["lon"])
        return None, None

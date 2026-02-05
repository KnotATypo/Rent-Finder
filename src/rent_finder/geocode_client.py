import os
import re

import requests

from rent_finder.logger import logger


class StatusException(Exception):
    pass


class GeocodeClient:
    """
    Client to forward geocode addresses to coordinates using https://geocode.maps.co/.
    """

    api_key = os.getenv("GEOCODE_API_KEY")

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

        response = requests.get(f"https://geocode.maps.co/search?q={address}&api_key={self.api_key}")

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

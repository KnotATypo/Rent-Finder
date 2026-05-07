import json
import os
import re
from pathlib import Path
from time import sleep
from typing import Tuple, List

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from tqdm import tqdm

from rent_finder.geocode_client import GeocodeClient
from rent_finder.logger import configure_logging, logger
from rent_finder.model import Query, Address, Listing
from rent_finder.sites.domain import Domain
from rent_finder.util import new_browser

directory = str(Path(__file__).resolve().parents[2])

Domain = Domain()
geocode = GeocodeClient()


def main():
    configure_logging()
    populate_coordinates()
    return

    if not os.path.exists(f"{directory}/ranges.json"):
        find_ranges()
    with open(f"{directory}/ranges.json") as f:
        ranges = json.load(f)

    browser = new_browser()
    for beds in tqdm(ranges, desc="Bed counts"):
        for range in tqdm(ranges[beds], desc="Price ranges"):
            range_stack = [range]
            while range_stack:
                range = range_stack.pop()
                query = Query(lower_price=range[0], upper_price=range[1], beds=beds)
                count = Domain.get_listing_count(query, browser)
                if count > 1000:
                    range_stack.extend(bisect(range))
                else:
                    Domain.search(browser, query)
    browser.quit()


def populate_coordinates():
    addresses = Address.select().join(Listing).where(Address.updated == False)

    browser = new_browser()
    for address in tqdm(addresses, desc="Addresses"):
        browser.get(Domain.get_listing_link(address.listing_set[0].id))

        tags = browser.find_elements(By.TAG_NAME, "h1")
        if len(tags) > 1:
            logger.error(f"Found more than one h1 tag: {tags[0].text}")
            continue
        full_address = tags[0].text
        address.address = full_address

        lat, lon = coords_from_maps(address, browser)
        if lon < 110 or lon > 155 or lat < -45 or lat > -10:
            # Outside bounding box for Australia
            lat = None
            lon = None

        address.latitude = lat
        address.longitude = lon
        address.updated = True

        address.save()


def coords_from_maps(address: Address, browser: WebDriver) -> tuple[float, float]:
    address_str = address.address
    if "/" in address_str:
        address_str = address_str[address_str.index("/") + 1 :]
    address_str = address_str.replace(" ", "+")
    maps_url = "https://www.google.com/maps/place/" + address_str

    browser.get(maps_url)

    coords = None
    retries = 10
    while coords is None:
        matches = re.findall(r"-\d{2}\.\d+,\d{3}\.\d+", browser.current_url)
        if len(matches) > 0:
            coords = matches[0]
        else:
            # It takes a moment for the coordinates to populate
            sleep(0.5)
            retries -= 1
            if retries == 0:
                logger.error(f"Google Maps: Could not find any coordinates for {address.address}")
                return None, None

    lat, lon = coords.split(",")
    lat, lon = float(lat), float(lon)
    return lat, lon


def find_ranges():
    browser = new_browser()
    bed_searches = ["0", "1", "2", "3", "4", "5-any"]
    good_ranges = {x: [] for x in bed_searches}

    for beds in bed_searches:
        range_stack = [(0, 50000)]

        while range_stack:
            range = range_stack.pop()
            count = Domain.get_listing_count(Query(lower_price=range[0], upper_price=range[1], beds=beds), browser)
            if count > 1000:
                range_stack.extend(bisect(range))
            else:
                good_ranges[beds].append(range)

    browser.quit()
    with open(f"{directory}/ranges.json", "w+") as f:
        json.dump(good_ranges, f)


def bisect(range: Tuple[int, int]) -> List[Tuple[int, int]]:
    midpoint = (range[0] + range[1]) // 2
    return [(range[0], midpoint), (midpoint, range[1])]


if __name__ == "__main__":
    main()

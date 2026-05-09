import json
import os
import re
from pathlib import Path
from time import sleep
from typing import Tuple, List

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from rent_scraper.logger import logger, configure_logging
from rent_scraper.model import Listing, Query, Address, SimpleListing, SimpleAddress
from rent_scraper.sites.domain import Domain
from rent_scraper.util import new_browser

RANGE_FILE = Path(__file__).parent / "resources" / "ranges.json"

domain = Domain()


def search():
    """
    Get a range.
    Check availability of each listing in this range (?)
    Check count of range and compare against expected.
    Begin searching range until count matches expectations.
    Repeat ad infinitum
    """

    configure_logging()
    ranges = get_ranges()
    browser = new_browser(headless=False)

    query = ranges[0]

    if query.beds == "5-any":
        bed_match = SimpleAddress.beds >= 5
    else:
        bed_match = SimpleAddress.beds == query.beds
    get_available = (
        lambda: SimpleListing.select()
        .join(SimpleAddress)
        .where(
            SimpleListing.price > query.lower_price,
            SimpleListing.price < query.upper_price,
            bed_match,
            SimpleListing.available,
        )
    )

    listings = set(get_available())
    for listing in listings:
        domain.update_listing(listing, browser)

    listings = set(get_available())
    expected_count = len(listings)
    true_count = domain.get_listing_count(query, browser)

    if expected_count > true_count:
        logger.error(
            f"Beds {query.beds}: {query.lower_price} - {query.upper_price} was expecting {expected_count} but found {true_count}"
        )
        return

    page = 1
    # new = set()
    while true_count != len(listings):
        listings_from_page = set(domain.get_page(page, query, browser))
        page += 1
        # new.update(listings_from_page)
        listings.update(listings_from_page)

    for listing in listings:
        address = Address.select().join(Listing).where(Listing.id == listing.id).get()
        if address.latitude is not None:
            continue
        populate_coordinates(address, browser)

    browser.quit()


def populate_coordinates(address: Address, browser: WebDriver):
    browser.get(domain.get_listing_link(address.listing_set[0].id))

    tags = browser.find_elements(By.TAG_NAME, "h1")
    if len(tags) > 1:
        logger.error(f"Found more than one h1 tag: {tags[0].text}")
        return
    full_address = tags[0].text
    address.address = full_address

    lat, lon = coords_from_maps(address, browser)
    if lat is None or lon is None:
        return

    if lon < 110 or lon > 155 or lat < -45 or lat > -10:
        # Outside bounding box for Australia
        return

    address.latitude = lat
    address.longitude = lon

    address.save()


def coords_from_maps(address: Address, browser: WebDriver) -> tuple[float, float]:
    address_str = address.address
    if "/" in address_str:
        address_str = address_str[address_str.index("/") + 1 :]
    address_str = address_str.replace(" ", "+")
    maps_url = "https://www.google.com/maps/place/" + address_str

    browser.get(maps_url)

    coords = None
    retries = 20
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


def get_ranges() -> List[Query]:
    if os.path.exists(RANGE_FILE):
        # Return ranges from file if they exist
        with open(RANGE_FILE) as f:
            serialised = json.load(f)
            queries = []
            for q in serialised:
                queries.append(Query(**q))
            return queries

    browser = new_browser(headless=False)
    bed_searches = ["0", "1", "2", "3", "4", "5-any"]
    good_ranges = {x: [] for x in bed_searches}

    for beds in bed_searches:
        range_stack = [(0, 50000)]

        while range_stack:
            cur_range = range_stack.pop()
            count = domain.get_listing_count(
                Query(lower_price=cur_range[0], upper_price=cur_range[1], beds=beds), browser
            )
            if count > 1000:
                range_stack.extend(bisect(cur_range))
            else:
                good_ranges[beds].append(cur_range)

    browser.quit()
    queries = []
    with open(RANGE_FILE, "w+") as f:
        serialised = []
        for beds in good_ranges:
            for cur_range in good_ranges[beds]:
                query = Query(lower_price=cur_range[0], upper_price=cur_range[1], beds=beds)
                serialised.append(query.__dict__["__data__"])
                queries.append(query)
        json.dump(serialised, f)

    return queries


def bisect(cur_range: Tuple[int, int]) -> List[Tuple[int, int]]:
    midpoint = (cur_range[0] + cur_range[1]) // 2
    return [(cur_range[0], midpoint), (midpoint, cur_range[1])]


if __name__ == "__main__":
    search()

import json
import os
import re
from pathlib import Path
from typing import Tuple, List

from selenium.common import TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
from tqdm import tqdm

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

    for query in tqdm(ranges, desc="Queries", unit="query"):
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
        for listing in tqdm(listings, desc="Updating", unit="listing", leave=False):
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
        on_page = {None}
        while true_count != len(listings) and len(on_page) != 0:
            on_page = set(domain.get_page(page, query, browser))
            listings.update(on_page)
            page += 1

        for listing in tqdm(listings, desc="Mapping", unit="listing", leave=False):
            address = Address.select().join(Listing).where(Listing.id == listing.id).get()
            if address.latitude is not None:
                continue
            populate_coordinates(address, browser)

    browser.quit()


def populate_coordinates(address: Address, browser: WebDriver):
    lat, lon = coords_from_maps(address, browser)

    if lat is None or lon is None:
        pass
    elif lon < 110 or lon > 155 or lat < -45 or lat > -10:
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

    whole_url_match = re.compile(r"^.+-\d{2}\.\d+,\d{3}\.\d+.+$")
    try:
        browser.get("https://www.google.com/maps/place/" + address_str)
        WebDriverWait(browser, 10).until(lambda browser: re.match(whole_url_match, browser.current_url))
        if "place//" in browser.current_url:
            # Failed to find an actual address, will deal with them later
            raise TimeoutException
        matches = re.findall(r"-\d{2}\.\d+,\d{3}\.\d+", browser.current_url)
        coords = matches[0]
        lat, lon = coords.split(",")
        return float(lat), float(lon)
    except TimeoutException:
        logger.error(f"Google Maps: Could not find any coordinates for {address.address}")
        return None, None


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

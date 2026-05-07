import json
import os
from collections import Counter
from pathlib import Path
from typing import Tuple, List

from selenium.webdriver.common.by import By
from tqdm import tqdm

from rent_finder.geocode_client import GeocodeClient
from rent_finder.logger import configure_logging, logger
from rent_finder.model import Query, Address, Listing
from rent_finder.sites.domain import Domain
from rent_finder.util import new_browser

directory = str(Path(__file__).resolve().parents[2])

Domain = Domain()


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
    addresses = Address.select().join(Listing).where(Address.latitude.is_null())

    geocode = GeocodeClient()
    counter = Counter()
    browser = new_browser()
    for address in tqdm(addresses, desc="Addresses"):
        first_try = True
        lat, lon = geocode.get_coordinate(address.address)
        if lat is None or lon is None:
            first_try = False
            browser.get(Domain.get_listing_link(address.listing_set[0].id))

            tags = browser.find_elements(By.TAG_NAME, "h1")
            if len(tags) > 1:
                logger.error(f"Found more than one h1 tag: {tags[0].text}")
                continue
            full_address = tags[0].text
            address.address = full_address

            lat, lon = geocode.get_coordinate(address.address)
            if lat is None or lon is None:
                continue

        address.latitude = lat
        address.longitude = lon
        address.save()

        if first_try:
            counter["first_try"] += 1
        else:
            counter["second_try"] += 1
        print(counter)


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

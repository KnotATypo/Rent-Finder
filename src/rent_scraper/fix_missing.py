import re
from pathlib import Path

import line_profiler
from selenium.common import TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
from tqdm import tqdm

from rent_scraper.logger import configure_logging, logger
from rent_scraper.model import Address, Listing, ListingHistory, SimpleListing
from rent_scraper.sites.domain import Domain
from rent_scraper.util import new_browser

RANGE_FILE = Path(__file__).parent / "resources" / "ranges.json"

browser = new_browser()


def main():
    configure_logging()
    # fix_addresses()
    populate_coordinates()


def fix_addresses():
    addresses = Address.select().join(Listing).join(ListingHistory).where(ListingHistory.valid_until.is_null())
    domain = Domain()
    regex = re.compile(r"\d.+\d{4}$")
    for address in tqdm(addresses):
        if not (re.search(regex, address.address)):
            listing = SimpleListing.select().where(SimpleListing.address == address.id).get()
            try:
                domain.update_listing(listing, browser)
            except KeyError:
                print(listing.address)
                continue
            if listing.available:
                address.address = domain.details_from_page(browser)["address"]
        else:
            address.address = address.address.replace("\n", "")

        address.save()


def populate_coordinates():
    addresses = Address.select().join(Listing).where(Address.latitude.is_null(), Address.updated == False)

    for address in tqdm(addresses, desc="Addresses"):
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


if __name__ == "__main__":
    main()

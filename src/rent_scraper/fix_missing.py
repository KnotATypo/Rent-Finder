import re
from pathlib import Path
from time import sleep

from selenium.webdriver.chrome.webdriver import WebDriver
from tqdm import tqdm

from rent_scraper.logger import configure_logging, logger
from rent_scraper.model import Address, Listing, ListingHistory, SimpleListing
from rent_scraper.sites.domain import Domain
from rent_scraper.util import new_browser

RANGE_FILE = Path(__file__).parent / "resources" / "ranges.json"

browser = new_browser()


def main():
    configure_logging()
    fix_addresses()
    populate_coordinates()


def fix_addresses():
    addresses = Address.select().join(Listing).join(ListingHistory).where(ListingHistory.valid_until.is_null())
    domain = Domain()
    for address in tqdm(addresses):
        if not (re.search(r"\d.+\d{4}$", address.address)):
            listing = SimpleListing.select().where(SimpleListing.address == address.id).get()
            domain.update_listing(listing, browser)
            if listing.available:
                address.address = domain.details_from_page(browser)["address"]
        else:
            address.address = address.address.replace("\n", "")

        address.save()


def populate_coordinates():
    addresses = Address.select().join(Listing).where(Address.latitude.is_null())

    for address in tqdm(addresses, desc="Addresses"):
        lat, lon = coords_from_maps(address, browser)
        if lat is None or lon is None:
            continue

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


if __name__ == "__main__":
    main()

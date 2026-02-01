import re
from typing import List

from bs4 import BeautifulSoup, Tag

from geocode_client import GeocodeClient
from logger import logger
from model import Listing, Suburb, Address
from util import new_browser


class Site:
    geocode_client: GeocodeClient

    def __init__(self):
        self.geocode_client = GeocodeClient()

    def search(self, suburb: Suburb) -> List[Listing]:
        listings = []
        page_number = 0
        browser = new_browser()
        while True:
            page_number += 1
            page = self.get_page(page_number, browser, suburb)
            if not page:
                break

            listings.extend(page)
        browser.close()

        return listings

    def get_page(self, page_num: int, browser, suburb: Suburb) -> List[Listing]:
        raise NotImplementedError

    def create_listing(self, page_element: Tag) -> Listing:
        raise NotImplementedError

    def page_exists(self, driver, location: str) -> bool:
        raise NotImplementedError

    def get_suburb_id(self, suburb: Suburb) -> str:
        raise NotImplementedError


class Domain(Site):
    def __init__(self):
        super().__init__()

    def get_page(self, page_num: int, browser, suburb: Suburb) -> List[Listing]:
        listings = []

        search_id = self.get_suburb_id(suburb)
        browser.get(f"https://www.domain.com.au/rent/{search_id}/?excludedeposittaken=1&page={page_num}&ssubs=0")
        soup = BeautifulSoup(browser.page_source, "html.parser")
        cards = soup.find_all(attrs={"data-testid": re.compile(r"^listing-card-wrapper")})

        for card in cards:
            try:
                listing = self.create_listing(card)
                listings.append(listing)
            except Exception as e:
                logger.warning(f"{search_id} - {type(e).__name__}: {e}")

        return listings

    def create_listing(self, card: Tag) -> Listing:
        address = card.find(attrs={"data-testid": "address-wrapper"})
        address = (
            address.find(attrs={"data-testid": "address-line1"}).text
            + address.find(attrs={"data-testid": "address-line2"}).text
        )
        address = address.replace(" ", " ")
        features = card.find(attrs={"data-testid": "property-features-wrapper"})
        listing_id = card.parent.attrs["data-testid"][8:]

        if (listing := Listing.get_or_none(Listing.id == listing_id)) is not None:
            return listing

        beds, baths, cars = None, None, None
        for feature in features:
            try:
                text = feature.text.lower()
                num = text.split(" ")[0]
                num = 0 if num == "−" else num
                if "bed" in text:
                    beds = int(num)
                elif "bath" in text:
                    baths = int(num)
                elif "car" in text or "park" in text:
                    cars = int(num)
            except Exception as e:
                logger.warning(f"{features} - {type(e).__name__}: {e}")

        price = card.find(attrs={"data-testid": "listing-card-price-wrapper"}).text
        price_list = re.findall(r"\$\d?,?\d+", price)
        if not price_list:
            price = 0
        else:
            price = int(price_list[0].replace(",", "").replace("$", ""))

        if (address_obj := Address.get_or_none(address=address)) is None:
            lat, lon = self.geocode_client.get_coordinate(address)
            address_obj = Address.create(
                address=address, beds=beds, baths=baths, cars=cars, latitude=lat, longitude=lon
            )

        return Listing.create(id=listing_id, address_id=address_obj.id, price=price)

    def get_suburb_id(self, suburb: Suburb) -> str:
        return f"{suburb.name.lower().replace(' ', '-')}-qld-{suburb.postcode}"

    def page_exists(self, driver, location: str) -> bool:
        driver.get(f"https://www.domain.com.au/rent/{location}/?excludedeposittaken=1&page=1&ssubs=0")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        summary = soup.find_all(attrs={"data-testid": "summary"})
        return len(summary) > 0

    @staticmethod
    def get_link(listing: Listing) -> str:
        address = (
            listing.address.lower()
            .replace(" ", "-")
            .replace("/", "-")
            .replace(":", "-")
            .replace(",", "-")
            .replace("--", "-")
        )
        return f"https://www.domain.com.au/{address}-{listing.domain_id}"

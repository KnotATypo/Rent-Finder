import re
from typing import List

from bs4 import BeautifulSoup, Tag

from rent_finder.logger import logger
from rent_finder.model import Suburb, Listing, Address
from rent_finder.sites.site import Site


class Domain(Site):
    def __init__(self):
        super().__init__()

    def get_page(self, page_num: int, browser, suburb: Suburb) -> List[Listing]:
        listings = []

        search_link = self.get_search_link(browser, page_num)
        browser.get(search_link)
        soup = BeautifulSoup(browser.page_source, "html.parser")
        cards = soup.find_all(attrs={"data-testid": re.compile(r"^listing-card-wrapper")})

        for card in cards:
            try:
                listing = self.create_listing(card)
                listings.append(listing)
            except Exception as e:
                logger.warning(f"{search_link} - {type(e).__name__}: {e}")

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

    def get_search_link(self, suburb: Suburb, page_number: int) -> str:
        suburb_id = f"{suburb.name.lower().replace(' ', '-')}-qld-{suburb.postcode}"
        return f"https://www.domain.com.au/rent/{suburb_id}/?excludedeposittaken=1&page={page_number}&ssubs=0"

    def get_listing_link(self, listing: Listing) -> str:
        address = Address.get(Address.id == listing.address_id)
        new_addresses = re.sub(r"[/ ,]+", "-", address.address)
        return f"https://www.domain.com.au/{new_addresses}-{listing.id}"

    def page_exists(self, driver, location: str) -> bool:
        driver.get(f"https://www.domain.com.au/rent/{location}/?excludedeposittaken=1&page=1&ssubs=0")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        summary = soup.find_all(attrs={"data-testid": "summary"})
        return len(summary) > 0

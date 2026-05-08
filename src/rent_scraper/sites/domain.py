import datetime
import re
from typing import List

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from rent_scraper.logger import logger
from rent_scraper.model import Listing, Address, Query
from rent_scraper.sites.site import Site

PARSER = "html.parser"


class Domain(Site):
    def __init__(self):
        super().__init__()

    def get_page(self, page_num: int, browser: webdriver.Chrome, query: Query) -> List[Listing]:
        listings = []

        search_link = self._get_search_link(query, page_num)
        browser.get(search_link)
        soup = BeautifulSoup(browser.page_source, PARSER)
        cards = soup.find_all(attrs={"data-testid": re.compile(r"^listing-card-wrapper")})

        for card in cards:
            try:
                listing = self._create_listing(card)
                if listing is not None:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"{search_link} - {type(e).__name__}: {e}")

        return listings

    def _create_listing(self, card: Tag) -> Listing | None:
        address = card.find(attrs={"data-testid": "address-wrapper"}).text
        address = address.replace(" ", " ")
        listing_id = card.parent.attrs["data-testid"][8:]

        if (address_obj := Address.get_or_none(address=address)) is None:
            features = card.find(attrs={"data-testid": "property-features-wrapper"})
            if features is None:
                logger.warning(f"{address} - Has no features")
                return None

            beds, baths, cars = 0, 0, 0
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

            logger.debug(f"Saved new address: {address}")
            address_obj = Address.create(address=address, beds=beds, baths=baths, cars=cars)

        if (listing := Listing.get_or_none(Listing.id == listing_id)) is not None:
            return listing

        price = card.find(attrs={"data-testid": "listing-card-price-wrapper"}).text
        price_list = re.findall(r"\$\d?,?\d+", price)
        if not price_list:
            price = 0
        else:
            price = int(price_list[0].replace(",", "").replace("$", ""))

        logger.debug(f"New listing {listing_id} created for {address}")
        return Listing.create(id=listing_id, address=address_obj, price=price, available=datetime.datetime.now())

    def listing_available(self, listing: Listing, browser: WebDriver) -> bool:
        link = self.get_listing_link(listing.id)
        browser.get(link)

        available = True
        try:
            # Check for the normal details column of the listing page
            browser.find_element(By.CSS_SELECTOR, 'div[data-testid="listing-details__summary-left-column"]')
        except NoSuchElementException:
            available = False

        try:
            # Sometimes the listing page still exists but has a tag indicating it is under contract or leased
            browser.find_element(By.CSS_SELECTOR, 'span[data-testid="listing-details__listing-tag"]')
            available = False
        except NoSuchElementException:
            pass

        return available

    def _get_search_link(self, query: Query, page_number: int) -> str:
        if query.suburb is not None:
            suburb_id = f"{query.suburb.name.lower().replace(' ', '-')}-{query.suburb.state}-{query.suburb.postcode}/"
        else:
            suburb_id = ""
        if query.lower_price is not None and query.upper_price is not None:
            price = f"price={query.lower_price}-{query.upper_price}&"
        else:
            price = ""
        if query.beds:
            beds = f"bedrooms={query.beds}&"
        else:
            beds = ""
        # "ssubs" removes surrounding suburbs when the suburb is specified
        # The sort is provided to avoid being given a "featured" property at the top of the search
        return f"https://www.domain.com.au/rent/{suburb_id}?{price}{beds}page={page_number}&excludedeposittaken=1&ssubs=0&sort=dateupdated-desc"

    def get_listing_link(self, listing_id: str) -> str:
        return f"https://www.domain.com.au/{listing_id}"

    def page_exists(self, driver, location: str) -> bool:
        driver.get(f"https://www.domain.com.au/rent/{location}/?excludedeposittaken=1&page=1&ssubs=0")
        soup = BeautifulSoup(driver.page_source, PARSER)
        summary = soup.find_all(attrs={"data-testid": "summary"})
        return len(summary) > 0

    def get_listing_count(self, query: Query, browser: WebDriver) -> int:
        link = self._get_search_link(query, 1)
        browser.get(link)
        count_text = browser.find_element(By.CSS_SELECTOR, 'h1[data-testid="summary"]').text
        count = int(re.findall(r"^\d+", count_text)[0])
        return count

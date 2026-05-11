import datetime
import re
from typing import List, Dict

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from rent_scraper.logger import logger
from rent_scraper.model import Listing, Address, Query, SimpleListing, AddressHistory, ListingHistory
from rent_scraper.sites.site import Site

PARSER = "html.parser"


class Domain(Site):
    def __init__(self):
        super().__init__()

    def get_page(self, page_num: int, query: Query, browser: webdriver.Chrome) -> List[Listing]:
        listings = []

        search_link = self._get_search_link(query, page_num)
        browser.get(search_link)
        soup = BeautifulSoup(browser.page_source, PARSER)
        cards = soup.find_all(attrs={"data-testid": re.compile(r"^listing-card-wrapper")})

        for card in cards:
            try:
                listing = self._create_listing(card, browser)
                if listing is not None:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"{search_link} - {type(e).__name__}: {e}")

        return listings

    def _create_listing(self, card: Tag, browser: WebDriver) -> SimpleListing | None:
        listing_id = card.parent.attrs["data-testid"][8:]
        if (listing := SimpleListing.get_or_none(SimpleListing.id == listing_id)) is not None:
            return listing

        details = self.details_from_page(browser, listing_id)
        if details is None:
            return None
        address = details["address"]

        if not re.search(r"\d.+\d{4}$", address):
            # The only numbers in the address are the postcode, meaning it isn't a legit address
            pass

        if (address_obj := Address.get_or_none(address=address)) is None:
            address_obj = Address.create(address=address)
            AddressHistory.create(
                address=address_obj,
                beds=details["beds"],
                baths=details["baths"],
                cars=details["cars"],
                valid_from=datetime.datetime.now(),
            )
            logger.debug(f"Saved new address: {address}")

        listing_obj = Listing.create(id=listing_id, address=address_obj)
        ListingHistory.create(listing=listing_obj, price=details["price"], valid_from=datetime.datetime.now())
        logger.debug(f"New listing {listing_id} created for {address}")
        return SimpleListing.get_by_id(listing_id)

    def listing_available(self, listing: Listing | SimpleListing, browser: WebDriver) -> bool:
        link = self.get_listing_link(listing.id)
        browser.get(link)

        available = True
        try:
            # If the property page exists, the "heading" on the page will be the address, which should be in the browser title
            tags = browser.find_elements(By.TAG_NAME, "h1")
            assert len(tags) == 1
            full_address = tags[0].text.replace(",", "")
            assert full_address in browser.title.replace(",", "")
            # Some properties will be redirected to a "property profile" page if they aren't for rent
            assert "property-profile" not in browser.current_url
        except AssertionError:
            available = False

        browser.implicitly_wait(0)
        try:
            # Sometimes the listing page still exists but has a tag indicating it is under contract or leased
            browser.find_element(By.CSS_SELECTOR, 'span[data-testid="listing-details__listing-tag"]')
            available = False
        except NoSuchElementException:
            pass
        browser.implicitly_wait(1)

        return available

    def _get_search_link(self, query: Query, page_number: int) -> str:
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
        return f"https://www.domain.com.au/rent/?{price}{beds}page={page_number}&excludedeposittaken=1&ssubs=0&sort=dateupdated-desc"

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

    def update_listing(self, listing: SimpleListing, browser: WebDriver) -> None:
        """
        Updates the listing price and address details in-place.
        This takes advantage of the "history" tables to retain old details as well.

        :param listing:
        :param browser:
        :return:
        """
        if not self.listing_available(listing, browser):
            listing.available = False
            listing.save()
            return

        details = self.details_from_page(browser)
        if details is None:
            return
        if details["price"] != listing.price:
            listing.price = details["price"]
        if details["beds"] != listing.address.beds:
            listing.address.beds = details["beds"]
        if details["baths"] != listing.address.baths:
            listing.address.baths = details["baths"]
        if details["cars"] != listing.address.cars:
            listing.address.cars = details["cars"]

        listing.save()
        listing.address.save()

    def details_from_page(self, browser, listing_id="") -> Dict[str, int | str] | None:
        """
        Retrieves price and bed, bath and car counts, and full address from a listing. By default, this acts on the
        current page but the listing_id can be provided.

        :param listing_id:
        :param browser:
        :return:
        """
        if listing_id != "":
            browser.get(self.get_listing_link(listing_id))

        details = {}

        price_text = browser.find_element(
            By.CSS_SELECTOR, 'div[data-testid="listing-details__listing-summary-title-name"]'
        ).text
        price_list = re.findall(r"\$\d{0,2},?\d+", price_text)
        if price_list:
            price = int(price_list[0].replace(",", "").replace("$", ""))
            details["price"] = price
        else:
            return None
        features_wrapper = browser.find_element(By.CSS_SELECTOR, 'div[data-testid="property-features-wrapper"]')
        features = features_wrapper.find_elements(By.CSS_SELECTOR, 'span[data-testid="property-features-feature"]')

        for feature in features:
            try:
                text = feature.text.lower()
                if "m²" in text or "ha" in text:
                    # We currently aren't recording area
                    continue
                num = text.split("\n")[0]
                num = 0 if num == "−" else int(num)
                if "bed" in text:
                    details["beds"] = num
                elif "bath" in text:
                    details["baths"] = num
                elif "car" in text or "park" in text:
                    details["cars"] = num
            except Exception as e:
                logger.warning(f"{features} - {type(e).__name__}: {e}")

        for element in ["beds", "baths", "cars"]:
            if element not in details:
                details[element] = 0

        tags = browser.find_elements(By.TAG_NAME, "h1")
        assert len(tags) == 1
        details["address"] = tags[0].text.replace("\n", " ")

        return details

import datetime
import re
from time import sleep
from typing import List

import requests
from bs4 import BeautifulSoup, Tag
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from rent_finder.logger import logger
from rent_finder.model import Suburb, Listing, Address
from rent_finder.sites.site import Site


class Domain(Site):
    def __init__(self):
        super().__init__()

    def get_page(self, page_num: int, browser, suburb: Suburb) -> List[Listing]:
        listings = []

        search_link = self._get_search_link(suburb, page_num)
        browser.get(search_link)
        soup = BeautifulSoup(browser.page_source, "html.parser")
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
        address = card.find(attrs={"data-testid": "address-wrapper"})
        address_line1 = address.find(attrs={"data-testid": "address-line1"})
        if address_line1 is None:
            # No viable address
            return None
        address = (
            address.find(attrs={"data-testid": "address-line1"}).text
            + address.find(attrs={"data-testid": "address-line2"}).text
        )
        address = address.replace(" ", " ")
        features = card.find(attrs={"data-testid": "property-features-wrapper"})
        listing_id = card.parent.attrs["data-testid"][8:]

        if (listing := Listing.get_or_none(Listing.id == listing_id)) is not None:
            return listing

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

    def download_blurb_and_images(self, listing: Listing, browser: WebDriver):
        link = self._get_listing_link(listing)
        browser.get(link)

        # Update status of listing and exit early if delisted
        try:
            browser.find_element(By.CSS_SELECTOR, 'div[data-testid="listing-details__summary-left-column"]')
        except NoSuchElementException:
            listing.unavailable = datetime.datetime.now()
            listing.save()
            return

        try:
            browser.implicitly_wait(1)
            browser.find_element(By.CSS_SELECTOR, 'span[data-testid="listing-details__listing-tag"]')
            browser.implicitly_wait(10)
            listing.unavailable = datetime.datetime.now()
            listing.save()
            return
        except NoSuchElementException:
            browser.implicitly_wait(10)

        browser.find_element(By.CSS_SELECTOR, 'button[data-testid="listing-details__description-button"]').click()
        soup = BeautifulSoup(browser.page_source, features="html.parser")
        tag = soup.find("div", attrs={"data-testid": "listing-details__description"})

        objects_to_save = {listing.id + "/blurb.html": tag.contents[1].prettify()}

        try:
            browser.find_element(
                By.CSS_SELECTOR, 'div[data-testid="listing-details__gallery-preview three-image-fixed"]'
            ).click()
        except NoSuchElementException:
            # Some listings only have a single image at the top of the page
            try:
                browser.find_element(
                    By.CSS_SELECTOR, 'div[data-testid="listing-details__gallery-preview single-image-full"]'
                ).click()
            except NoSuchElementException:
                # There must be no image - consider it unavailable
                listing.unavailable = datetime.datetime.now()
                listing.save()
                return
        sleep(1)

        soup = BeautifulSoup(browser.page_source, features="html.parser")
        footer = soup.find("div", attrs={"data-testid": "pswp-thumbnails-carousel"})
        total_page = int(footer.text.split(" / ")[1])
        for i in range(total_page):
            soup = BeautifulSoup(browser.page_source, features="html.parser")
            tag = soup.find("div", attrs={"data-testid": "pswp-current-item"})
            images = tag.find_all("img")
            # Some listings contain videos and won't return any images
            if images:
                # There are two images typically, one of which is the thumbnail marked by "--placeholder"
                image = [image for image in images if "--placeholder" not in str(image)][0]
                if image["src"] != "":
                    objects_to_save[listing.id + f"/{i}.webp"] = requests.get(image["src"]).content

            browser.find_element(By.CSS_SELECTOR, 'button[title="Next (arrow right)"]').click()

        self.s3_client.put_objects(objects_to_save)

    def _get_search_link(self, suburb: Suburb, page_number: int) -> str:
        suburb_id = f"{suburb.name.lower().replace(' ', '-')}-qld-{suburb.postcode}"
        return f"https://www.domain.com.au/rent/{suburb_id}/?excludedeposittaken=1&page={page_number}&ssubs=0"

    def _get_listing_link(self, listing: Listing) -> str:
        address = Address.get(Address.id == listing.address)
        new_addresses = re.sub(r"[/ ,]+", "-", address.address)
        return f"https://www.domain.com.au/{new_addresses}-{listing.id}"

    def page_exists(self, driver, location: str) -> bool:
        driver.get(f"https://www.domain.com.au/rent/{location}/?excludedeposittaken=1&page=1&ssubs=0")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        summary = soup.find_all(attrs={"data-testid": "summary"})
        return len(summary) > 0

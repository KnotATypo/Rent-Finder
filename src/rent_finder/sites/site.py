from typing import List

from bs4 import Tag
from selenium.webdriver.chrome.webdriver import WebDriver

from rent_finder.geocode_client import GeocodeClient
from rent_finder.model import Listing, Suburb
from rent_finder.s3_client import S3Client


class Site:
    geocode_client: GeocodeClient

    def __init__(self):
        self.geocode_client = GeocodeClient()
        self.s3_client = S3Client()

    def search(self, browser, suburb: Suburb) -> List[Listing]:
        listings = []
        page_number = 0
        while True:
            page_number += 1
            page = self.get_page(page_number, browser, suburb)
            if not page:
                break

            listings.extend(page)

        return listings

    def _get_search_link(self, suburb: Suburb, page_number: int) -> str:
        raise NotImplementedError

    def get_listing_link(self, listing: Listing) -> str:
        raise NotImplementedError

    def get_page(self, page_num: int, browser, suburb: Suburb) -> List[Listing]:
        raise NotImplementedError

    def _create_listing(self, page_element: Tag) -> Listing:
        raise NotImplementedError

    def listing_available(self, listing: Listing, browser: WebDriver) -> bool:
        raise NotImplementedError

    def page_exists(self, driver, location: str) -> bool:
        raise NotImplementedError

from typing import List

from bs4 import Tag
from selenium.webdriver.chrome.webdriver import WebDriver

from rent_scraper.model import Listing, Query


class Site:
    def __init__(self):
        pass

    def search(self, browser, query: Query) -> List[Listing]:
        listings = []
        page_number = 0
        while True:
            page_number += 1
            page = self.get_page(page_number, query, browser)
            if not page:
                break

            listings.extend(page)

        return listings

    def _get_search_link(self, query: Query, page_number: int) -> str:
        raise NotImplementedError

    def get_listing_link(self, listing: Listing) -> str:
        raise NotImplementedError

    def get_page(self, page_num: int, query: Query, browser) -> List[Listing]:
        raise NotImplementedError

    def _create_listing(self, page_element: Tag) -> Listing:
        raise NotImplementedError

    def listing_available(self, listing: Listing, browser: WebDriver) -> bool:
        raise NotImplementedError

    def page_exists(self, driver, location: str) -> bool:
        raise NotImplementedError

    def get_listing_count(self, query: Query, browser: WebDriver) -> int:
        """
        Get the number of listings found with the given query

        :param query: Query to search for
        :param browser: WebDriver to use for search
        :return:
        """
        raise NotImplementedError

import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth

from rent_finder.model import Listing


def get_listing_data_path(listing: Listing) -> str:
    return os.getenv("DATA_DIR") + "/" + listing.id


def new_browser(headless=True) -> webdriver.Chrome:
    """
    Creates a new Chrome browser instance with the selenium_stealth additions

    headless -- Sets the headless options for the browser (default True)
    """
    options = Options()
    if headless:
        options.add_argument("--headless")

    # Flag needed to run in Docker
    options.add_argument("--no-sandbox")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)

    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    driver.implicitly_wait(10)
    return driver

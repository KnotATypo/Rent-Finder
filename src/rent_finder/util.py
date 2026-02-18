import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth

# Ensure the virtual display is used when running in Docker
if os.getenv("DISPLAY") is None:
    os.environ["DISPLAY"] = ":99"


def new_browser() -> webdriver.Chrome:
    """
    Creates a new Chrome browser instance with the selenium_stealth additions
    """
    options = Options()

    options.add_argument("--headless")

    # Flags needed to run in Docker
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

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
    driver.set_window_size(1024, 768)
    return driver

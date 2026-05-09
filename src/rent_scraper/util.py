from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth


def new_browser(headless=True) -> webdriver.Chrome:
    """
    Creates a new Chrome browser instance with the selenium_stealth additions
    """
    options = Options()

    if headless:
        options.add_argument("--headless=new")

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

    driver.set_page_load_timeout(60)
    driver.set_script_timeout(60)
    driver.implicitly_wait(1)
    driver.set_window_size(1024, 768)

    return driver

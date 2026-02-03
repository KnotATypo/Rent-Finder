import math
from time import sleep
from typing import Dict, Set

from bs4 import BeautifulSoup
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from rent_finder.model import TravelMode


def get_travel_times(lat1, lon1, lat2, lon2, travel_modes: Set[TravelMode], browser) -> Dict[TravelMode, int]:
    link = f"https://www.google.com/maps/dir/{lat1},{lon1}/{lat2},{lon2}"
    browser.get(link)
    times = {}
    for travel_mode in travel_modes:
        match travel_mode:
            case TravelMode.PT:
                times[travel_mode] = calculate_pt_travel_time(browser)
            case TravelMode.BIKE:
                times[travel_mode] = calculate_bike_travel_time(browser)
            case _:
                raise ValueError(f"Unknown travel mode: {travel_mode}")
    return times


def calculate_bike_travel_time(browser) -> int:
    browser.find_element(By.CSS_SELECTOR, 'div[aria-label="Cycling"]').click()
    sleep(1)

    time = get_min_time(browser)

    return time


def calculate_pt_travel_time(browser) -> int:
    browser.find_element(By.CSS_SELECTOR, 'div[aria-label="Public transport"]').click()
    browser.find_element(By.XPATH, '//span[text()="Leave now"]').click()
    browser.find_element(By.CSS_SELECTOR, 'div[data-index="1"]').click()
    time_field = browser.find_element(By.CSS_SELECTOR, 'input[name="transit-time"]')
    time_field.clear()
    time_field.send_keys("9:00 am")

    def pick_dates(initial_open=False) -> int:
        times = []
        open_picker = initial_open
        # Check monday and tuesday just in case
        for i in range(2):
            if not open_picker:
                browser.find_element(By.CSS_SELECTOR, 'button[aria-live="polite"]').click()
            else:
                open_picker = False
            browser.find_elements(By.CSS_SELECTOR, 'td[class="goog-date-picker-date"]')[i].click()
            times.append(get_min_time(browser))
        return min(times)

    # current month
    time = pick_dates()

    # move to next month then pick (picker will already be open)
    browser.find_element(By.CSS_SELECTOR, 'button[aria-live="polite"]').click()
    browser.find_element(By.CSS_SELECTOR, 'button[class="goog-date-picker-btn goog-date-picker-nextMonth"]').click()
    time = min(pick_dates(initial_open=True), time)

    return time


def get_min_time(browser: WebDriver) -> int:
    WebDriverWait(browser, 10).until(ec.presence_of_element_located((By.CSS_SELECTOR, 'div[data-trip-index="0"]')))
    soup = BeautifulSoup(browser.page_source, features="html.parser")

    times = []
    index = 0
    while True:
        tag = soup.find("div", attrs={"data-trip-index": f"{index}"})
        index += 1
        if tag is None:
            break
        time_field = tag.find("div", attrs={"class": "fontHeadlineSmall"})
        time = time_field.text
        minutes = 0
        if "hr" in time:
            i = time.index("hr")
            hours = int(time[:i].strip())
            minutes = hours * 60
            time = time[i + 3 :]
        if "min" in time:
            minutes += int(time.split(" ")[0])
        times.append(minutes)

    return min(times) if times else math.inf

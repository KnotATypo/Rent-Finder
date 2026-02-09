import math
from time import sleep
from typing import Dict, Set, List

from bs4 import BeautifulSoup
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from rent_finder.model import TravelMode


def get_travel_times(lat1, lon1, lat2, lon2, travel_modes: Set[TravelMode], browser) -> Dict[TravelMode, int]:
    """
    Get travel times between two locations using the given travel modes. Currently supported travel modes are Bike and PT.

    :param lat1:
    :param lon1:
    :param lat2:
    :param lon2:
    :param travel_modes: Set of travel modes
    :param browser: WebDriver to use for the search
    :return: Dictionary of (travel mode, travel time)
    """
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
    """
    Navigate to and grab the bike travel time.

    :param browser: WebDriver to use for the search
    :return: Travel time in minutes
    """
    browser.find_element(By.CSS_SELECTOR, 'div[aria-label="Cycling"]').click()
    sleep(1)

    time = get_min_time(browser)

    return time


def calculate_pt_travel_time(browser) -> int:
    """
    Navigate to and grab the public transport travel time. This checks the first two weekdays of the current month and
    next month.

    :param browser: WebDriver to use for the search
    :return: Minimum travel time across checked dates in minutes
    """
    browser.find_element(By.CSS_SELECTOR, 'div[aria-label="Public transport"]').click()
    # Occasionally this will error when the PT info doesn't load. Not catching the error here is intentional
    browser.find_element(By.XPATH, '//span[text()="Leave now"]').click()
    browser.find_element(By.CSS_SELECTOR, 'div[data-index="1"]').click()
    time_field = browser.find_element(By.CSS_SELECTOR, 'input[name="transit-time"]')
    time_field.clear()
    time_field.send_keys("9:00 am")

    def pick_dates(initial_open=True) -> List[int]:
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
        return times

    # Originally we were checking the current month and the next, but Google Maps has trouble with doing PT too far into the past
    # Now we just check the next two months
    time = []
    for _ in range(2):
        browser.find_element(By.CSS_SELECTOR, 'button[aria-live="polite"]').click()
        browser.find_element(By.CSS_SELECTOR, 'button[class="goog-date-picker-btn goog-date-picker-nextMonth"]').click()
        time.extend(pick_dates())

    return min(time)


def get_min_time(browser: WebDriver) -> int:
    """
    Gets the minimum travel time between the displayed options.

    :param browser: WebDriver to use for the search
    :return: Minimum travel time in minutes
    """
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

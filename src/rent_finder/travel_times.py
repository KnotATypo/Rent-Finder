import math

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from rent_finder.util import new_browser


def get_travel_time(lat1, lon1, lat2, lon2) -> int:
    link = f"https://www.google.com/maps/dir/{lat1},{lon1}/{lat2},{lon2}"
    return calculate_travel_time(link)


def calculate_travel_time(link: str) -> int:
    browser = new_browser()
    browser.get(link)
    browser.maximize_window()
    browser.implicitly_wait(10)

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
            WebDriverWait(browser, 10).until(
                ec.presence_of_element_located((By.CSS_SELECTOR, 'div[data-trip-index="0"]'))
            )
            soup = BeautifulSoup(browser.page_source, features="html.parser")
            times.append(get_times(soup))
        return min(times)

    # current month
    time = pick_dates()

    # move to next month then pick (picker will already be open)
    browser.find_element(By.CSS_SELECTOR, 'button[aria-live="polite"]').click()
    browser.find_element(By.CSS_SELECTOR, 'button[class="goog-date-picker-btn goog-date-picker-nextMonth"]').click()
    time = min(pick_dates(initial_open=True), time)

    browser.close()
    return time


def get_times(soup: BeautifulSoup) -> int:
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

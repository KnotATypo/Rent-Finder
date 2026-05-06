import json
import os
from pathlib import Path
from typing import Tuple, List

from tqdm import tqdm

from rent_finder.logger import configure_logging
from rent_finder.model import Query
from rent_finder.sites.domain import Domain
from rent_finder.util import new_browser

directory = str(Path(__file__).resolve().parents[2])

Domain = Domain()


def main():
    configure_logging()

    if not os.path.exists(f"{directory}/ranges.json"):
        find_ranges()
    with open(f"{directory}/ranges.json") as f:
        ranges = json.load(f)

    browser = new_browser(headless=False)
    for beds in tqdm(ranges, desc="Bed counts"):
        for range in tqdm(ranges[beds], desc="Price ranges"):
            range_stack = [range]
            while range_stack:
                range = range_stack.pop()
                query = Query(lower_price=range[0], upper_price=range[1], beds=beds)
                count = Domain.get_listing_count(query, browser)
                if count > 1000:
                    range_stack.extend(bisect(range))
                else:
                    Domain.search(browser, query)
    browser.quit()


def find_ranges():
    browser = new_browser(headless=False)
    bed_searches = ["0", "1", "2", "3", "4", "5-any"]
    good_ranges = {x: [] for x in bed_searches}

    for beds in bed_searches:
        range_stack = [(0, 50000)]

        while range_stack:
            range = range_stack.pop()
            count = Domain.get_listing_count(Query(lower_price=range[0], upper_price=range[1], beds=beds), browser)
            if count > 1000:
                range_stack.extend(bisect(range))
            else:
                good_ranges[beds].append(range)

    browser.quit()
    with open(f"{directory}/ranges.json", "w+") as f:
        json.dump(good_ranges, f)


def bisect(range: Tuple[int, int]) -> List[Tuple[int, int]]:
    midpoint = (range[0] + range[1]) // 2
    return [(range[0], midpoint), (midpoint, range[1])]


if __name__ == "__main__":
    main()

import requests
from geopy.distance import geodesic
from tqdm import tqdm

from rent_finder.sites.domain import Domain
from rent_finder.model import Suburb
from rent_finder.logger import logger, configure_logging
from rent_finder.util import new_browser


def main():
    """
    Populates the database with suburbs. Currently configured for Queensland.
    TODO - Make configurable
    """
    configure_logging()
    domain = Domain()

    suburbs = list(Suburb.select())
    if len(suburbs) != 0:
        starting_postcode = list(Suburb.select().order_by(-Suburb.postcode).limit(1))[0].postcode
    else:
        starting_postcode = 4000
    logger.info(f"Starting at postcode {starting_postcode}")

    browser = new_browser()
    for postcode in tqdm(range(starting_postcode, 5000), desc="Postcodes"):
        if postcode >= 5000:
            break
        response = requests.get(
            f"http://v0.postcodeapi.com.au/suburbs/{postcode}.json", headers={"Accept": "application/json"}
        )
        if response.status_code != 200:
            logger.error("Error:", response.status_code)
            continue
        data = response.json()
        for location in tqdm(data, desc=f"{postcode} Locations", leave=False):
            if Suburb.get_or_none(name=location["name"]) is not None:
                continue
            domain_id = f"{location['name'].lower().replace(' ', '-')}-qld-{postcode}"
            listings = domain.page_exists(browser, domain_id)
            if listings:
                coord = location["latitude"], location["longitude"]
                dist = geodesic(coord, (-27.4681, 153.0265)).km
                Suburb.create(
                    name=location["name"],
                    postcode=postcode,
                    latitude=coord[0],
                    longitude=coord[1],
                    distance_to_source=round(dist, 2),
                )
        logger.info(f"Finished postcode {postcode}")

    browser.close()
    print(f"Stopping at postcode {postcode}")


if __name__ == "__main__":
    main()

import os.path

from tqdm import tqdm

from rent_finder.logger import configure_logging
from rent_finder.logger import logger
from rent_finder.model import Suburb, TravelTime, SavedLocations, Address, TravelMode, Listing
from rent_finder.sites.domain import Domain
from rent_finder.travel_times import get_travel_time
from rent_finder.util import get_listing_data_path, new_browser


def main():
    configure_logging()
    logger.info("Starting search")
    # get_rentals()
    # populate_travel_times()
    download_extras()
    logger.info("Finished search")


def get_rentals():
    domain = Domain()

    listings = []
    suburbs = list(Suburb.select().where(Suburb.distance_to_source < 15))
    for suburb in tqdm(suburbs, desc="Searching suburbs", unit="location"):
        listings.append(domain.search(suburb))


def populate_travel_times():
    saved_locations: list[SavedLocations] = list(SavedLocations.select())
    for location in saved_locations:
        all_addresses = set(Address.select())
        done_addresses = set(Address.select().join(TravelTime).where(TravelTime.to_location == location))
        need_to_do = all_addresses - done_addresses
        for address in tqdm(need_to_do, desc="Calculating travel times", unit="addresses"):
            time = get_travel_time(address.latitude, address.longitude, location.latitude, location.longitude)
            TravelTime.create(address_id=address, travel_time=time, travel_mode=TravelMode.PT, to_location=location)


def download_extras():
    domain = Domain()
    listings = [
        listing for listing in Listing.select() if not os.path.exists(get_listing_data_path(listing) + "/0.webp")
    ]
    browser = new_browser(headless=False)
    for listing in tqdm(listings, desc="Downloading extras", unit="listings", total=len(listings)):
        domain.download_blurb_and_images(listing, browser)
    browser.close()


if __name__ == "__main__":
    main()

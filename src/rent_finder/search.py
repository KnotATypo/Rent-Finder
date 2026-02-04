from tqdm import tqdm

from rent_finder.logger import configure_logging
from rent_finder.logger import logger
from rent_finder.model import Suburb, TravelTime, SavedLocations, Address, TravelMode, Listing
from rent_finder.s3_client import S3Client
from rent_finder.sites.domain import Domain
from rent_finder.travel_times import get_travel_times
from rent_finder.util import new_browser


def main():
    configure_logging()
    logger.info("Starting search")
    get_rentals()
    populate_travel_times()
    update_listings()
    logger.info("Finished search")


def get_rentals():
    logger.info("Getting rentals")

    domain = Domain()

    listings = []
    suburbs = list(Suburb.select().where(Suburb.distance_to_source < 15))
    browser = new_browser(headless=False)
    logger.info(f"Found {len(suburbs)} suburbs")
    for suburb in tqdm(suburbs, desc="Searching suburbs", unit="location"):
        listings.append(domain.search(browser, suburb))
    browser.close()


def populate_travel_times():
    logger.info("Populating travel times")

    modes = {TravelMode.PT, TravelMode.BIKE}
    saved_locations: list[SavedLocations] = list(SavedLocations.select())

    browser = new_browser(headless=False)
    for location in tqdm(saved_locations, desc="Populating travel times", unit="locations", leave=False):

        done_address_sets = []
        for mode in modes:
            done_address_sets.append(
                set(
                    Address.select()
                    .join(TravelTime)
                    .where(TravelTime.to_location == location, TravelTime.travel_mode == mode)
                )
            )
        addresses_with_all_modes = set.intersection(*done_address_sets)
        need_to_do = set(Address.select()) - addresses_with_all_modes

        logger.info(f"Need to do: {len(need_to_do)} addresses for {location.name}")
        for address in tqdm(need_to_do, desc="Calculating travel times", unit="addresses", leave=False):
            existing_modes = list(
                TravelTime.select().join(Address).where(TravelTime.to_location == location, Address.id == address.id)
            )
            existing_modes = {mode.travel_mode for mode in existing_modes}
            try:
                times = get_travel_times(
                    address.latitude,
                    address.longitude,
                    location.latitude,
                    location.longitude,
                    modes - existing_modes,
                    browser,
                )
                for mode, time in times.items():
                    TravelTime.create(address_id=address, travel_time=time, travel_mode=mode, to_location=location)
            except Exception as e:
                logger.error(f"Address {address}, {type(e).__name__}: {e}")
                browser.close()
                browser = new_browser(headless=False)


def update_listings():
    """
    Update the status and download blurbs and images for listings
    :return:
    """
    logger.info("Updating listings")

    domain = Domain()
    s3 = S3Client()
    listings = [
        listing for listing in Listing.select().where(Listing.available) if not s3.object_exists(listing.id + "/0.webp")
    ]
    browser = new_browser(headless=False)
    logger.info(f"{len(listings)} listings to update")
    for listing in tqdm(listings, desc="Downloading extras", unit="listings", total=len(listings)):
        try:
            domain.download_blurb_and_images(listing, browser)
        except Exception as e:
            logger.error(f"Listing {listing}, {type(e).__name__}: {e}")
            browser.close()
            browser = new_browser(headless=False)
    browser.close()


if __name__ == "__main__":
    main()

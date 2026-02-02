from tqdm import tqdm

from rent_finder.logger import configure_logging
from rent_finder.model import Suburb, TravelTime, SavedLocations, Address, TravelMode, Listing
from rent_finder.sites.domain import Domain
from rent_finder.travel_times import get_travel_time


def main():
    configure_logging()
    # get_rentals()
    # populate_travel_times()
    domain = Domain()
    domain.download_blurb(list(Listing.select())[0])


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


if __name__ == "__main__":
    main()

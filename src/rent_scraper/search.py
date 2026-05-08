import datetime

from tqdm import tqdm

from rent_scraper.logger import logger, configure_logging, progress_bars
from rent_scraper.model import Listing, db
from rent_scraper.sites.domain import Domain
from rent_scraper.util import new_browser


def search():
    with db.connection_context():
        configure_logging()
        logger.info("Starting search")
        get_rentals()
        update_unavailable()
        logger.info("Finished search")


def get_rentals():
    """
    Populate the database with information regarding rentals within the given suburbs.
    """
    logger.info("Getting rentals")
    domain = Domain()

    # TODO


def update_unavailable():
    """
    Checks each available listing to confirm it is still available
    """
    listings = list(Listing.select().where(Listing.unavailable.is_null()))

    browser = new_browser()
    browser.implicitly_wait(0)

    domain = Domain()
    for listing in tqdm(listings, desc="Updating unavailable", unit="listings", disable=not progress_bars):
        try:
            if not domain.listing_available(listing, browser):
                listing.unavailable = datetime.datetime.now()
                listing.save()
                logger.info(f"Listing {listing} unavailable")
        except Exception as e:
            logger.error(f"Listing {listing}, {type(e).__name__}: {e}")
            browser.close()
            browser = new_browser()
    browser.close()


if __name__ == "__main__":
    search()

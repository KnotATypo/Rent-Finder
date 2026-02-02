import os

from flask import Flask, render_template
from flask import send_from_directory, url_for, abort
from rent_finder.logger import logger, configure_logging
from rent_finder.model import Address, Listing
from rent_finder.util import get_listing_path
from waitress import serve

app = Flask(__name__)
app.secret_key = "super secret key"

DATA_DIR = os.getenv("DATA_DIR")


@app.route("/")
def index():
    # Filtering out the listings that haven't had their images downloaded (for now)
    listings = [listing for listing in Listing.select().join(Address) if os.path.exists(get_listing_path(listing.id))]
    return render_template("index.html", listings=listings)


@app.route("/listing/<listing_id>")
def listing(listing_id):
    listing_path = get_listing_path(listing_id)

    with open(listing_path + "/blurb.html", "r", encoding="utf-8") as f:
        blurb_html = f.read()

    # Find first image file by numeric prefix
    images = []
    for fname in os.listdir(listing_path):
        if fname == "blurb.html":
            continue
        base, _ = os.path.splitext(fname)
        idx = int(base)
        images.append((idx, fname))

    images.sort(key=lambda x: x[0])

    image_urls = [url_for("serve_data", listing_id=listing_id, filename=image[1]) for image in images]
    listing = Listing.get(Listing.id == listing_id)

    return render_template(
        "listing.html", listing=listing, blurb_html=blurb_html, image_urls=image_urls
    )


@app.route("/data/<listing_id>/<path:filename>")
def serve_data(listing_id, filename):
    return send_from_directory(get_listing_path(listing_id), filename)


def host():
    logger.info("Starting Flask app...")
    serve(app, host="0.0.0.0", port=4321)


if __name__ == "__main__":
    configure_logging()
    host()

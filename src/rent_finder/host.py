from flask import Flask, render_template
from flask import url_for
from waitress import serve

from rent_finder.logger import logger, configure_logging
from rent_finder.model import Address, Listing
from rent_finder.s3_client import S3Client

app = Flask(__name__)
app.secret_key = "super secret key"

s3_client = S3Client()
listings = [listing for listing in Listing.select().join(Address) if s3_client.object_exists(listing.id + "/0.webp")]

@app.route("/")
def index():
    # Filtering out the listings that haven't had their images downloaded (for now)
    return render_template("index.html", listings=listings)


@app.route("/listing/<listing_id>")
def listing(listing_id):
    blurb_html = s3_client.get_object(listing_id + "/blurb.html")

    # Find first image file by numeric prefix
    images = s3_client.get_image_names(listing_id)
    images.sort(key=lambda x: int(x.split(".")[0]))

    image_urls = [url_for("serve_data", listing_id=listing_id, filename=image) for image in images]
    listing = Listing.get(Listing.id == listing_id)

    return render_template(
        "listing.html", listing=listing, blurb_html=blurb_html, image_urls=image_urls
    )


@app.route("/data/<listing_id>/<path:filename>")
def serve_data(listing_id, filename):
    return s3_client.get_object(listing_id + "/" + filename)


def host():
    logger.info("Starting Flask app...")
    serve(app, host="0.0.0.0", port=4321)


if __name__ == "__main__":
    configure_logging()
    host()

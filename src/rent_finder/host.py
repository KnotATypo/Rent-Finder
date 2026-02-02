import os

from flask import Flask, render_template
from flask import send_from_directory, url_for, abort
from rent_finder.logger import logger, configure_logging
from waitress import serve

app = Flask(__name__)
app.secret_key = "super secret key"

DATA_DIR = os.getenv("DATA_DIR")


@app.route("/")
def index():
    # list available listing ids (folders in data)
    listings = []
    for name in sorted(os.listdir(DATA_DIR)):
        path = DATA_DIR + f"/{name}"
        if os.path.isdir(path):
            listings.append(name)
    return render_template("index.html", listings=listings)


@app.route("/listing/<listing_id>")
def listing(listing_id):
    # Build path to listing folder
    listing_path = DATA_DIR + f"/{listing_id}"
    if not os.path.isdir(listing_path):
        abort(404)

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

    image_urls = [url_for("serve_data", listing_id=listing_id, filename=f) for f in [t[1] for t in images]]

    return render_template("listing.html", listing_id=listing_id, blurb_html=blurb_html, image_urls=image_urls)


@app.route("/data/<listing_id>/<path:filename>")
def serve_data(listing_id, filename):
    listing_path = DATA_DIR + f"/{listing_id}"
    if not os.path.isdir(listing_path):
        abort(404)

    file_path = listing_path + f"/{filename}"
    if not os.path.isfile(file_path):
        abort(404)

    return send_from_directory(listing_path, filename)


def host():
    logger.info("Starting Flask app...")
    serve(app, host="0.0.0.0", port=4321)


if __name__ == "__main__":
    configure_logging()
    host()

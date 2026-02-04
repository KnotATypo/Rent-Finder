import os
from functools import wraps

from flask import Flask, render_template, session, jsonify, request, redirect
from flask import url_for
from waitress import serve

from rent_finder.logger import logger, configure_logging
from rent_finder.model import Address, Listing, TravelTime, SavedLocations, AddressStatus, UserStatus, User
from rent_finder.s3_client import S3Client

app = Flask(__name__)
app.secret_key = os.urandom(24)

s3_client = S3Client()
# Filtering out the listings that haven't had their images downloaded (for now)
listings = [listing for listing in Listing.select().join(Address) if s3_client.object_exists(listing.id + "/0.webp")]

@app.route("/set_username")
def set_username():
    users = [user.username for user in User.select().order_by(User.id)]
    return render_template("set_username.html", users=users)


def require_user(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for("set_username"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/login", methods=["POST"])
def login_post():
    username = request.form.get("username")
    if not username:
        return redirect(url_for("set_username"))

    user_q = list(User.select().where(User.username == username))
    if not user_q:
        return redirect(url_for("set_username"))

    user = user_q[0]
    session["user_id"] = user.id
    session["username"] = user.username

    return redirect(url_for("index"))


def get_current_user():
    username = session.get("username")
    user_id = session.get("user_id")
    if not username and not user_id:
        return None
    return username, user_id


@app.route("/")
def index():
    return render_template("index.html", listings=listings)


@app.route("/listing/<listing_id>")
def listing(listing_id):
    blurb_html = s3_client.get_object(listing_id + "/blurb.html")

    # Find first image file by numeric prefix
    images = s3_client.get_image_names(listing_id)
    images.sort(key=lambda x: int(x.split(".")[0]))

    image_urls = [url_for("serve_data", listing_id=listing_id, filename=image) for image in images]
    listing = Listing.get(Listing.id == listing_id)

    travel_times = TravelTime.select().join(SavedLocations).where(TravelTime.address == listing.address)

    return render_template(
        "listing.html", listing=listing, blurb_html=blurb_html, image_urls=image_urls, travel_times=travel_times
    )


@app.route("/listing/<listing_id>/status/<status>")
@require_user
def listing_status(listing_id, status):
    status = UserStatus(status)
    listing = Listing.get(Listing.id == listing_id)
    _, user_id = get_current_user()
    addr_status = AddressStatus.select().where(
        AddressStatus.address == listing.address, AddressStatus.user.id == user_id
    )
    if addr_status:
        addr_status.status = status
        addr_status.save()
    else:
        AddressStatus.create(address=listing.address, user=user_id, status=status)

    return jsonify({"status": "success"}), 200


@app.route("/data/<listing_id>/<path:filename>")
def serve_data(listing_id, filename):
    return s3_client.get_object(listing_id + "/" + filename)


def host():
    logger.info("Starting Flask app...")
    serve(app, host="0.0.0.0", port=4321)


if __name__ == "__main__":
    configure_logging()
    host()

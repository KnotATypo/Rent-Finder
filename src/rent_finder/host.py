import os
from functools import wraps

from flask import Flask, render_template, session, request, redirect
from flask import url_for
from waitress import serve

from rent_finder.logger import logger, configure_logging
from rent_finder.model import Listing, TravelTime, SavedLocations, AddressStatus, UserStatus, User, Address
from rent_finder.s3_client import S3Client

app = Flask(__name__)
app.secret_key = os.urandom(24)

s3_client = S3Client()


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
@require_user
def index():
    return render_template("index.html")


@app.route("/listing/")
@app.route("/listing/<listing_id>")
@require_user
def listing(listing_id=None):
    _, user_id = get_current_user()
    if listing_id is None:
        checked_addresses = [addr.address for addr in AddressStatus.select().where(AddressStatus.user == user_id)]
        listing = list(
            Listing.select().where(Listing.unavailable.is_null(), Listing.address.not_in(checked_addresses))
        )[0]
        return redirect(url_for("listing", listing_id=listing.id))

    listing = Listing.get(Listing.id == listing_id)
    blurb_html = s3_client.get_object(listing_id + "/blurb.html")

    # Find first image file by numeric prefix
    images = s3_client.get_image_names(listing_id)
    images.sort(key=lambda x: int(x.split(".")[0]))

    image_urls = [url_for("serve_data", listing_id=listing_id, filename=image) for image in images]
    travel_times = TravelTime.select().join(SavedLocations).where(TravelTime.address == listing.address)

    return render_template(
        "listing.html", listing=listing, blurb_html=blurb_html, image_urls=image_urls, travel_times=travel_times
    )


@app.route("/listing/<listing_id>/status/<status>", methods=["POST"])
@require_user
def listing_status(listing_id, status):
    status = UserStatus(status)
    listing = Listing.get(Listing.id == listing_id)
    _, user_id = get_current_user()
    addr_status = list(
        AddressStatus.select()
        .join(User)
        .where(AddressStatus.address == listing.address, AddressStatus.user.id == user_id)
    )
    if addr_status:
        addr_status[0].status = status
        addr_status[0].save()
    else:
        AddressStatus.create(address=listing.address, user=user_id, status=status)

    return redirect(url_for("listing"))


@app.route("/interested")
@require_user
def interested():
    _, user_id = get_current_user()
    listing = list(
        Listing.select()
        .join(Address)
        .join(AddressStatus)
        .join(User)
        .where(
            AddressStatus.address == Listing.address,
            AddressStatus.status == UserStatus.INTERESTED,
            AddressStatus.user.id == user_id,
        )
    )
    return render_template("interested.html", listing=listing)


@app.route("/data/<listing_id>/<path:filename>")
def serve_data(listing_id, filename):
    return s3_client.get_object(listing_id + "/" + filename)


def host():
    logger.info("Starting Flask app...")
    serve(app, host="0.0.0.0", port=4321)


if __name__ == "__main__":
    configure_logging()
    host()

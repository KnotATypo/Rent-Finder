import atexit
import os
from functools import wraps

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, session, request, redirect, jsonify
from flask import url_for
from waitress import serve

from rent_finder.logger import logger, configure_logging
from rent_finder.model import (
    Listing,
    TravelTime,
    SavedLocations,
    AddressStatus,
    UserStatus,
    User,
    Address,
    Filter,
    FilterType,
    Operator,
)
from rent_finder.s3_client import S3Client
from rent_finder.search import search
from rent_finder.sites.domain import Domain

app = Flask(__name__)
app.secret_key = os.urandom(24)

s3_client = S3Client()

scheduler = BackgroundScheduler(daemon=True)

with open("src/rent_finder/static/img/no_image.png", "rb") as f:
    no_image = f.read()


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
    return session.get("user_id")


@app.route("/")
@require_user
def index():
    return render_template("index.html")


@app.route("/listing/")
@app.route("/listing/<listing_id>")
@require_user
def listing(listing_id=None):
    """
    Serve the given listing or redirect to the next listing following the user's filters.

    :param listing_id:
    """
    if listing_id is None:
        user_id = get_current_user()
        checked_addresses = [addr.address for addr in AddressStatus.select().where(AddressStatus.user == user_id)]
        listings = list(
            Listing.select().where(Listing.unavailable.is_null(), Listing.address.not_in(checked_addresses))
        )
        filters = list(Filter.select().where(Filter.user == user_id))
        filtered_listings = []
        for listing in listings:
            if all(pass_filter(filter, listing) for filter in filters):
                filtered_listings.append(listing)

        return redirect(url_for("listing", listing_id=filtered_listings[0].id, source="listing"))

    listing = Listing.get(Listing.id == listing_id)
    if s3_client.object_exists(listing_id + "/blurb.html"):
        blurb_html = s3_client.get_object(listing_id + "/blurb.html")
        images = s3_client.get_image_names(listing_id)
        images.sort(key=lambda x: int(x.split(".")[0]))
    else:
        blurb_html = ""
        images = ["none"]
    listing.blurb = blurb_html

    image_urls = [url_for("serve_data", listing_id=listing_id, filename=image) for image in images]
    travel_times = TravelTime.select().join(SavedLocations).where(TravelTime.address == listing.address)

    source = request.args.get("source")

    return render_template(
        "listing.html", listing=listing, image_urls=image_urls, travel_times=travel_times, source=source
    )


def pass_filter(filter: Filter, listing: Listing):
    listing_value = filter.type.function()(listing)
    op_fn = filter.operator.function()

    return op_fn(listing_value, filter.value)


@app.route("/listing/<listing_id>/status/<status>", methods=["POST"])
@require_user
def listing_status(listing_id, status):
    """
    Updates or creates the status of the given listing for the logged-in user.

    :param listing_id:
    :param status:
    """
    status = UserStatus(status)
    listing = Listing.get(Listing.id == listing_id)
    user_id = get_current_user()
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

    source = request.form.get("source", "index")

    return redirect(url_for(source))


@app.route("/interested")
@require_user
def interested():
    """
    Serves the page containing all the listings that the user has marked as interested.
    """
    user_id = get_current_user()
    listings = list(
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
    domain = Domain()
    for listing in listings:
        listing.source = domain.get_listing_link(listing)

    return render_template("interested.html", listing=listings)


@app.route("/saved_locations")
def saved_locations():
    """
    Serves the page containing the list of locations which travel time is calculated to.
    """
    return render_template("saved_locations.html", saved_locations=list(SavedLocations.select()))


@app.route("/set_filters")
@require_user
def set_filters():
    user_id = get_current_user()
    filters = list(Filter.select().where(Filter.user == user_id))
    return render_template("set_filters.html", filters=filters)


@app.route("/filter_update", methods=["POST"])
@require_user
def filter_update():
    """
    Creates or deletes a filter.
    """
    user_id = get_current_user()
    if request.form.get("_method") == "DELETE":
        Filter.delete().where(Filter.id == request.form.get("filter_id")).execute()
        return redirect(url_for("set_filters"))

    filter_type = request.form.get("type")
    filter_operator = request.form.get("operator")
    filter_value = request.form.get("value")
    Filter.create(type=FilterType(filter_type), operator=Operator(filter_operator), value=filter_value, user=user_id)
    return redirect(url_for("set_filters"))


@app.route("/health_check")
def health_check():
    return jsonify({"status": "ok"})


@app.route("/data/<listing_id>/<path:filename>")
def serve_data(listing_id, filename):
    object_name = listing_id + "/" + filename
    if s3_client.object_exists(object_name):
        return s3_client.get_object(object_name)
    return no_image


def host():
    scheduler.add_job(search, "cron", hour=16, minute=0)
    atexit.register(lambda: scheduler.shutdown())
    scheduler.start()
    logger.info("Starting Flask app...")
    serve(app, host="0.0.0.0", port=4321)


if __name__ == "__main__":
    configure_logging()
    host()

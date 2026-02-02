from flask import Flask, render_template
from rent_finder.logger import logger, configure_logging
from waitress import serve

app = Flask(__name__)
app.secret_key = "super secret key"

@app.route("/")
def index():
    return render_template("index.html")


def host():
    logger.info("Starting Flask app...")
    serve(app, host="0.0.0.0", port=4321)


if __name__ == "__main__":
    configure_logging()
    host()

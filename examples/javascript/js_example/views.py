import math

from flask import jsonify
from flask import render_template
from flask import request

from . import app


@app.route("/", defaults={"js": "fetch"})
@app.route("/<any(xhr, jquery, fetch):js>")
def index(js):
    return render_template(f"{js}.html", js=js)


def parse_number(name):
    """Read a form field as a finite number.

    Raises ValueError with a message meant to be shown to the user if the
    field is missing, blank, not a number, or not finite (inf/nan).
    """
    value = request.form.get(name, "").strip()

    if not value:
        raise ValueError(f"{name} is required.")

    try:
        number = float(value)
    except ValueError:
        raise ValueError(f"{name} must be a number.") from None

    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number.")

    return number


@app.route("/add", methods=["POST"])
def add():
    try:
        a = parse_number("a")
        b = parse_number("b")
    except ValueError as error:
        return jsonify(error=str(error)), 400

    result = a + b

    if not math.isfinite(result):
        return jsonify(error="The result is out of range."), 400

    return jsonify(result=result)

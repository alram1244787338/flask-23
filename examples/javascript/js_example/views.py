import math

from flask import jsonify
from flask import render_template
from flask import request

from . import app


@app.route("/", defaults={"js": "fetch"})
@app.route("/<any(xhr, jquery, fetch):js>")
def index(js):
    return render_template(f"{js}.html", js=js)


def _parse_float(raw, label):
    """Validate and convert a raw form value to float.

    Returns ``(value, None)`` on success or ``(None, error_message)`` on
    failure.  Empty / whitespace-only values, non-numeric strings, ``NaN``
    and ``Infinity`` are all rejected.
    """
    value = raw.strip() if raw else ""
    if not value:
        return None, f"Please enter a value for {label}."
    try:
        number = float(value)
    except ValueError:
        return None, f"'{value}' is not a valid number for {label}."
    if not math.isfinite(number):
        return None, f"'{value}' is not a valid number for {label}."
    return number, None


@app.route("/add", methods=["POST"])
def add():
    raw_a = request.form.get("a", "")
    raw_b = request.form.get("b", "")

    a, error_a = _parse_float(raw_a, "a")
    b, error_b = _parse_float(raw_b, "b")

    errors = [e for e in (error_a, error_b) if e]
    if errors:
        return jsonify(error=" ".join(errors)), 400

    return jsonify(result=a + b)

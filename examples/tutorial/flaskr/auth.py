import functools

from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")


def normalize_username(username):
    """Return a canonical form of ``username``.

    Leading and trailing whitespace is stripped and the result is
    case-folded, so inputs like ``" Alice "``, ``"alice"`` and ``"ALICE"``
    all map to the same value. Registration, lookup and login normalize
    the same way, so a name that *looks* the same always behaves the same.
    ``casefold`` is used instead of ``lower`` because it folds case more
    correctly for non-ASCII text. Whitespace-only or missing input becomes
    an empty string so callers can report a "required" error.
    """
    if not username:
        return ""

    return username.strip().casefold()


def login_required(view):
    """View decorator that redirects anonymous users to the login page."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view


@bp.before_app_request
def load_logged_in_user():
    """If a user id is stored in the session, load the user object from
    the database into ``g.user``."""
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = (
            get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        )


@bp.route("/register", methods=("GET", "POST"))
def register():
    """Register a new user.

    Validates that the username is not already taken. Hashes the
    password for security.
    """
    if request.method == "POST":
        # Normalize so trailing spaces or odd casing can't create a
        # second account that looks identical to an existing one. The
        # password is never normalized; spaces there may be intentional.
        username = normalize_username(request.form["username"])
        password = request.form["password"]
        db = get_db()
        error = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."

        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except db.IntegrityError:
                # The username was already taken, which caused the
                # commit to fail. Show a validation error.
                error = f"User {username} is already registered."
            else:
                # Success, go to the login page.
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    """Log in a registered user by adding the user id to the session."""
    if request.method == "POST":
        # Normalize the same way registration does so a name that looks
        # the same always resolves to the same stored account.
        username = normalize_username(request.form["username"])
        password = request.form["password"]
        db = get_db()
        error = None
        user = None

        if not username:
            # Distinguish "you didn't enter a username" from a username
            # that simply isn't registered, so the hint is actionable.
            error = "Username is required."

        if error is None:
            user = db.execute(
                "SELECT * FROM user WHERE username = ?", (username,)
            ).fetchone()

            if user is None:
                error = "Incorrect username."
            elif not check_password_hash(user["password"], password):
                error = "Incorrect password."

        if error is None:
            # store the user id in a new session and return to the index
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    """Clear the current session, including the stored user id."""
    session.clear()
    return redirect(url_for("index"))

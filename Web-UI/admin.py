from flask import Blueprint, request
import secrets, json

from email_controller import Email_Controller
import db

# re-generated on each run
key = secrets.token_urlsafe(18)
open("admin_key", "w").write(key)

bp = Blueprint("Admin-APIs", __name__)


def ensure_auth(request):
    if not request.headers.get("admin-key") == key:
        raise Exception("Not authenticated!")

@bp.route("/list-games")
def list_games():
    ensure_auth(request)

    res_str = "State   | Teacher registration path          | Name"
    for (name, running, dl) in db.get_games():
        res_str += "\n" + ("Running" if running else "Stopped") \
            + " | " + "/register/" + dl + " | " + name

    return res_str

@bp.route("/create-game", methods=["POST"])
def create_game():
    ensure_auth(request)

    maybe_deeplink = db.create_game(str(request.get_data(), encoding="utf-8"))
    if not maybe_deeplink is None:
        return "Game up and running, with teacher registration deeplink: /register/" \
                + maybe_deeplink
    else:
        return "An Error occured. Does a game with the same name already exist?"

@bp.route("/pause-game", methods=["POST"])
def pause_game():
    ensure_auth(request)
    name = str(request.get_data(), encoding="utf-8")
    db.set_game_state(name, False)

    return "Successfully paused game"

@bp.route("/resume-game", methods=["POST"])
def resume_game():
    ensure_auth(request)
    name = str(request.get_data(), encoding="utf-8")
    db.set_game_state(name, True)

    return "Successfully resumed game"

@bp.route("/export-game", methods=["POST"])
def export_game():
    ensure_auth(request)
    name = str(request.get_data(), encoding="utf-8")

    return db.export_game(name)

@bp.route("/import-game", methods=["POST"])
def import_game():
    ensure_auth(request)
    # here, we expect multipart/form-data

    try:
        db.import_game(request.form["game"], json.load(request.files["content"]))
        return "Successfully imported game (:"
    except Exception as e:
        return "An unknown error occured. Maybe a game with the same name already exists? error: " + str(e)

@bp.route("/dump-db")
def dump():
    ensure_auth(request)

    return {game: db.export_game(game, full=True) for (game, _, _) in db.get_games()}

@bp.route("/clear-game", methods=["POST"])
def clear_game():
    ensure_auth(request)
    name = str(request.get_data(), encoding="utf-8")

    try:
        db.clear_game(name)
        return "Cleared accounts & regenerated deeplinks"
    except:
        return "An unknown error occured. Does this game exist? error: " + str(e)

@bp.route("/delete-game", methods=["POST"])
def delete_game():
    ensure_auth(request)
    name = str(request.get_data(), encoding="utf-8")

    try:
        db.delete_game(name)
        return "Successfully deleted game"
    except:
        return "An unknown error occured. Does this game exist? error: " + str(e)

@bp.route("/email-settings", methods=["POST"])
def update_email_settings():
    ensure_auth(request)

    sender = request.form.get("address")
    host = request.form.get("host")
    port = request.form.get("port")
    if isinstance(port, str):
        port = int(port)

    Email_Controller.update_settings(
        sender=sender,
        host=host,
        port=port
    )

    if (sender, host, port) == (None, None, None):
        return "Settings: " + str(Email_Controller.get_settings())
    else:
        return "Successfully changed settings. The new settings are: " \
            + str(Email_Controller.get_settings())

import secrets
from flask import Flask, request, redirect, flash, session

from lehrkraft_apis import bp as lehrkraft_bp
from sus_apis import bp as sus_bp
from admin import bp as admin_bp
import db

from os import environ

try:
    seckey = open("session_key").read()
except FileNotFoundError:
    seckey = secrets.token_urlsafe(18)
    open("session_key", "w").write(seckey)

app = Flask(__name__)
app.secret_key = seckey
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
)

app.register_blueprint(lehrkraft_bp)
app.register_blueprint(sus_bp)
app.register_blueprint(admin_bp)

@app.route("/logout")
def logout():
    url = request.args.get("return", "/")
    session.clear()

    flash("You have been logged out successfully :)", "success")
    return redirect(url)


if environ.get("TEST_DATA") == "1":
    db.setup_test_data()

# quick loading of server
# if __name__ == "__main__":
#     app.run(debug=True)
#     db.setup_test_data()

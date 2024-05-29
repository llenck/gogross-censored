import json, base64, magic
import werkzeug as wk
from flask import Blueprint, render_template, request, flash, url_for, redirect, session, Response
from email_controller import Email_Controller
import db
from datetime import date
bp = Blueprint("SuS-APIs", __name__)


# TODO: API über die großhändler-bilder zu den sus kommen

@bp.errorhandler(db.SusAuthException)
def sus_auth_error(e):
    flash(e.message)

    if e.shop != None and e.deeplink != None:
        return redirect(url_for("SuS-APIs.sus_login",
                                **{"return": e.request.url, "shop": e.shop,
                                   "deeplink": e.deeplink}))
    elif e.deeplink != None:
        return redirect(url_for("SuS-APIs.sus_list", deeplink=e.deeplink))
    else:
        # wenn kein deeplink angegeben ist, haben wir nicht wirklich einen ort
        # für den nutzer... :(
        return redirect(url_for("Lehrkraft-APIs.lehrkraft_login"))


@bp.route("/<deeplink>/list")
def sus_list(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)

    vendors = db.show_vendors_of_country(cc)
    for vendor in vendors:
        vendor["categories"] = db.get_categories(vendor["id"])

    return render_template("sus/list.html", vendors=vendors)


@bp.route("/<deeplink>/register", methods=["GET", "POST"])
def sus_register(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)
    vendor_id = request.args["shop"]
    if vendor_id is None:
        raise wk.exceptions.BadRequest("Missing key: shop")

    vendor = db.get_vendor(vendor_id)
    if vendor["country_code"] != cc:
        raise wk.exceptions.Forbidden("Bad vendor country")

    if request.method == "GET":
        return render_template("sus/registration.html", vendor=vendor)

    elif request.method == "POST":
        name = request.form["company_name"]
        email = request.form["email"]
        pw = request.form["password"]

        if db.sus_register(vendor_id, name, email, pw):
            return redirect(url_for("SuS-APIs.sus_login", deeplink=deeplink,
                                    shop=vendor_id))
        else:
            flash("Could not create account. Does one with the same e-mail " \
                + "already exist at this vendor?")
            return redirect(url_for("SuS-APIs.sus_register", deeplink=deeplink,
                                    shop=vendor_id))


@bp.route("/<deeplink>/login", methods=["GET", "POST"])
def sus_login(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)  # wofür brauchen wir das nur umd die richtigen vendor in der html zu zeigen?
    vendor_id = request.args["shop"]

    vendor = db.get_vendor(vendor_id)
    if vendor["country_code"] != cc:
        raise wk.exceptions.Forbidden("Bad vendor country")

    next_url = url_for("SuS-APIs.sus_home", deeplink=deeplink)

    if request.method == "POST":
        email = request.form["email"]
        pw = request.form["password"]
        if db.login_sus(email, pw, vendor_id, session):
            return redirect(next_url)
        else:
            flash("Invalid credentials")
            return redirect(url_for("SuS-APIs.sus_login", deeplink=deeplink, shop=vendor_id))

    else:
        # we're dealing with a GET-request. If the sus is authenticated already at this
        # vendor, redirect, otherwise display login form.
        try:
            if db.authenticate_sus(request, session)["vendor"] == int(vendor_id):
                return redirect(next_url)
        except db.SusAuthException:
            pass

        return render_template("sus/login.html", vendor=vendor)


@bp.route("/<deeplink>/pw-reset", methods=["GET", "POST"])
def sus_pw_reset(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)

    if request.method == "GET":
        return render_template("sus/sus_password_reset.html")
    elif request.method == "POST":
        email = request.json["email"]
        vendor_id = int(request.args['shop'])

        if db.is_mail(email, vendor_id):
            content = ("Dear Customer,\n You may reset your password with this link:\n"
                       + request.json["origin"] + "/" + deeplink + "/change-pw/"
                       + db.get_pw_reset_token(email, vendor_id=vendor_id)
                       + "\nit will expire in about 30 minutes\n\nHappy shopping :)")
            if Email_Controller.send(email, "GoGross password reset", content):
                return {"status": "success", "message": "Email was sent. Please check your inbox."}
            else:
                return {"status": "error", "message": "An unknown error occured in the backend."}
        else:
            return {"status": "error", "message": "Invalid E-Mail and/or shop."}


@bp.route("/<deeplink>/change-pw/<token>", methods=["GET", "POST"])
def sus_change_pw(deeplink, token):
    error_str = db.is_change_pw_token(token)
    (game, cc) = db.is_sus_deeplink(request, deeplink)

    if request.method == "GET":
        if error_str is None:
            return render_template("sus/sus_change_password.html")
        else:
            flash(error_str)
            return redirect(url_for("SuS-APIs.sus_list",
                                   vendor=db.show_vendors_of_country(cc), deeplink= deeplink))

    elif request.method == "POST":
        new_pw = request.form["password"]
        new_pw_repeat = request.form["repeat_password"]

        if new_pw != new_pw_repeat:
            flash("both passwords are different from each other")
            return redirect(url_for("SuS-APIs.sus_change_pw",
                                    token=token, deeplink=deeplink))
        else:
            v_id = db.get_tokens_vendor_id(token)
            db.change_pw(db.get_tokens_email(token), token, new_pw,
                         vendor=v_id)
            flash("password changed successfully")
            return redirect(url_for("SuS-APIs.sus_login",deeplink=deeplink, shop=v_id))

@bp.route("/<deeplink>/home")
def sus_home(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)
    sus_data = db.authenticate_sus(request, session)

    vendor = db.get_vendor(sus_data["vendor"])
    invoices = db.get_invoices(sus_data)

    return render_template("sus/home.html", sus=sus_data, vendor=vendor, invoices=invoices)


@bp.route("/<deeplink>/vendor-logo")
def sus_vendor_logo(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)

    try:
        vendor_id = request.args["shop"]
    except KeyError:
        sus_data = db.authenticate_sus(request, session)
        vendor_id = sus_data["vendor"]

    vendor = db.get_vendor(vendor_id)
    if vendor["country_code"] != cc:
        raise wk.exceptions.Forbidden("Bad vendor country")

    may_pic = vendor["logo"]
    if may_pic is None:
        return Response(":(", mimetype="text/plain")
    else:
        return Response(may_pic, mimetype=magic.from_buffer(may_pic, mime=True))


@bp.route("/<deeplink>/invoice", methods=["GET", "POST"])
def sus_invoice(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)
    sus_data = db.authenticate_sus(request, session)

    pdf_bytes = db.get_invoice_pdf(request.args["id"])

    return Response(pdf_bytes, mimetype="application/pdf")


@bp.route("/<deeplink>/catalog")
def sus_catalog(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)
    sus_data = db.authenticate_sus(request, session)

    vendor = db.get_vendor(sus_data["vendor"])
    categories = db.get_categories(sus_data["vendor"])
    items = db.get_vendor_items(sus_data["vendor"])

    return render_template("sus/catalog.html", vendor=vendor, categories=categories, products=items)


@bp.route("/<deeplink>/img")
def sus_img(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)

    product = db.get_item(request.args["product"])
    db.authenticate_sus(request, session, vendor=product["id_1"])

    may_pic = product.get("picture")

    if may_pic is None:
        return Response(":(", mimetype="text/plain")
    else:
        return Response(may_pic, mimetype=magic.from_buffer(may_pic, mime=True))


def ensure_cart(sus_data, session):
    session["cart_id"] = db.cart_epheremal_or_new(sus_data, session.get("cart_id"))

@bp.route("/<deeplink>/cart")
def sus_cart(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)
    sus_data = db.authenticate_sus(request, session)
    ensure_cart(sus_data, session)

    vendor = db.get_vendor(sus_data["vendor"])
    cart_items = db.get_cart(session["cart_id"])

    return render_template("sus/cart.html", vendor = vendor, invoice_lines=cart_items)


@bp.route("/<deeplink>/add-to-cart", methods=["POST"])
def sus_add_to_cart(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)

    product = db.get_item(request.form["product_id"])
    cnt = int(request.form["quantity"])

    sus_data = db.authenticate_sus(request, session, vendor=product["id_1"])

    if cnt <= 0:
        raise wk.exceptions.BadRequest("Lmao nix da") # leerkauf verhindern

    ensure_cart(sus_data, session)
    db.add_to_cart(session["cart_id"], product["id"], cnt)

    flash("Successfully added item to cart")
    may_cat = request.args.get("return-cat")
    if may_cat is None:
        return redirect(url_for("SuS-APIs.sus_catalog", deeplink=deeplink))
    else:
        return redirect(url_for("SuS-APIs.sus_catalog", deeplink=deeplink, category=may_cat))


@bp.route("/<deeplink>/del-from-cart", methods=["POST"])
def sus_del_from_cart(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)
    sus_data = db.authenticate_sus(request, session)
    ensure_cart(sus_data, session)

    if db.del_from_cart(session["cart_id"], request.form["invoice_line_id"]):
        flash("Successfully removed item from cart")
    else:
        flash("No such item in cart :/")

    return redirect(url_for("SuS-APIs.sus_cart", deeplink=deeplink))


@bp.route("/<deeplink>/checkout", methods=["POST"])
def sus_checkout(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)
    sus_data = db.authenticate_sus(request, session)
    ensure_cart(sus_data, session)

    vendor_id = sus_data["vendor"]
    vendor = db.get_vendor(vendor_id)

    cart_id = session["cart_id"]
    invoice_id = db.checkout_cart(cart_id)
    Email_Controller.send(sus_data["email"], "Your invoice (#%d)" % cart_id,
f"""
Dear customer,

attached you'll find the invoice for your last checkout at {vendor["name"]}.

""".strip(), attachments={"invoice.pdf": db.get_invoice_pdf(invoice_id)})

    return redirect(url_for("SuS-APIs.sus_invoice", deeplink=deeplink, id=invoice_id))


# Used by the app to verify links before opening a WebView
@bp.route("/<deeplink>/is_gogross")
def sus_app_check(deeplink):
    (game, cc) = db.is_sus_deeplink(request, deeplink)

    return "Ich bims, 1 gogross"

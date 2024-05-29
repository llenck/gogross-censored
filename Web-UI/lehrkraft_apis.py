import base64
import json, magic
import werkzeug as wk
from flask import Blueprint, render_template, request, flash, url_for, redirect, session, jsonify, Response

import db
from email_controller import Email_Controller

bp = Blueprint("Lehrkraft-APIs", __name__)
eu_laender = [
    {"Land": "Belgium", "Kürzel": "BE"},
    {"Land": "Bulgaria", "Kürzel": "BG"},
    {"Land": "Denmark", "Kürzel": "DK"},
    {"Land": "Germany", "Kürzel": "DE"},
    {"Land": "Estonia", "Kürzel": "EE"},
    {"Land": "Finland", "Kürzel": "FI"},
    {"Land": "France", "Kürzel": "FR"},
    {"Land": "Greece", "Kürzel": "GR"},
    {"Land": "Ireland", "Kürzel": "IE"},
    {"Land": "Italy", "Kürzel": "IT"},
    {"Land": "Croatia", "Kürzel": "HR"},
    {"Land": "Latvia", "Kürzel": "LV"},
    {"Land": "Lithuania", "Kürzel": "LT"},
    {"Land": "Luxembourg", "Kürzel": "LU"},
    {"Land": "Malta", "Kürzel": "MT"},
    {"Land": "Netherlands", "Kürzel": "NL"},
    {"Land": "Austria", "Kürzel": "AT"},
    {"Land": "Poland", "Kürzel": "PL"},
    {"Land": "Portugal", "Kürzel": "PT"},
    {"Land": "Romania", "Kürzel": "RO"},
    {"Land": "Sweden", "Kürzel": "SE"},
    {"Land": "Slovakia", "Kürzel": "SK"},
    {"Land": "Slovenia", "Kürzel": "SI"},
    {"Land": "Spain", "Kürzel": "ES"},
    {"Land": "Czech Republic", "Kürzel": "CZ"},
    {"Land": "Hungary", "Kürzel": "HU"},
    {"Land": "Cyprus", "Kürzel": "CY"}
]


@bp.errorhandler(db.LehrkraftAuthException)
def lehrkraft_auth_error(e):
    flash(e.message)

    return redirect(url_for("Lehrkraft-APIs.lehrkraft_login",
                            **{"return": e.request.url}))


@bp.route("/register/<deeplink>", methods=["GET", "POST"])
def lehrkraft_register(deeplink):
    game = db.is_teacher_deeplink(request, deeplink)

    if request.method == "GET":
        return render_template("teacher/teacher_registration.html", eu_laender=eu_laender)

    elif request.method == "POST":
        name = request.form["name"]
        country_code = request.form["country"]
        email = request.form["email"]
        pw = request.form["password"]
        if not db.lehrkraft_register(game, name, country_code, email, pw):
            flash("Already registered.")
        return redirect(url_for("Lehrkraft-APIs.lehrkraft_login"))


@bp.route("/", methods=["GET", "POST"])
def lehrkraft_login():
    next_url = request.args.get("return", url_for("Lehrkraft-APIs.lehrkraft_dashboard"))

    if request.method == "POST":
        # we have a login attempt
        email = request.form["email"]
        pw = request.form["password"]

        if db.login_teacher(email, pw, session):
            return redirect(next_url)
        else:
            flash("Invalid credentials")
            return redirect(url_for("Lehrkraft-APIs.lehrkraft_login"))

    else:
        # we're dealing with a GET-request. If the teacher is authenticated already,
        # redirect, otherwise display login form.
        try:
            _ = db.authenticate_teacher(request, session)
            return redirect(next_url)
        except db.LehrkraftAuthException:
            return render_template("teacher/teacher_login.html")


@bp.route("/pw-reset", methods=["GET", "POST"])
def lehrkraft_pw_reset():
    if request.method == "GET":
        return render_template("teacher/teacher_password-reset.html")
    elif request.method == "POST":
        email = request.json["email"]
        if db.is_mail(email):
            content = ("Dear Teacher,\nYou may reset your password with this link:\n"
                       + request.json["origin"] + "/change-pw/" + db.get_pw_reset_token(email)
                       + "\nit will expire in about 30 minutes.\n")

            if Email_Controller.send(email, "GoGross password reset", content):
                return {"status": "success", "message": "Email was sent. Please check your inbox."}
            else:
                return {"status": "error", "message": "An unknown error occured in the backend."}
        else:
            return {"status": "error", "message": "Email not found."}


@bp.route("/change-pw/<token>", methods=["GET", "POST"])
def lehrkraft_change_pw(token):
    error_str = db.is_change_pw_token(token)

    if request.method == "GET":
        if error_str is None:
            return render_template("teacher/teacher_change_password.html")
        else:
            flash(error_str)
            return render_template("teacher/teacher_login.html")

    elif request.method == "POST":
        # TODO: create password filter and implement it here and at sus too (may be frontends job)
        new_pw = request.form["password"]
        new_pw_repeat = request.form["repeat_password"]

        if new_pw != new_pw_repeat:
            flash("both passwords are different from each other")
            return redirect(url_for("Lehrkraft-APIs.lehrkraft_change_pw", token=token))
        else:
            db.change_pw(db.get_tokens_email(token), token, new_pw)
            flash("password changed successfully")
            return redirect(url_for("Lehrkraft-APIs.lehrkraft_login"))


@bp.route("/dashboard", methods=["GET", "POST"])
def lehrkraft_dashboard():
    teacher_data = db.authenticate_teacher(request, session)
    raw_shops = db.show_vendors_of_country_and_game(teacher_data["country_code"], teacher_data["game"])
    vendor_id = request.args.get('shop')

    if request.method == "GET":
        # backend calcs
        invoices = []
        cust_count = 0
        unpaid_count = 0

        if vendor_id is None:
            shop_ids = db.get_vendor_ids(raw_shops)
            for v_id in shop_ids:
                v_invoices = db.get_invoice_list_by_vendor(v_id)
                #TODO: design decision: are identical customers in 2 shops counted as 1 or 2 customers?
                # now counted as 2
                cust_count += db.get_customer_count(v_id)
                v_skonto_period = db.show_skonto_period(v_id)[0]["skonto_period"]
                for i in range(len(v_invoices)):
                    v_invoices[i]["discount_period"] = v_skonto_period
                invoices.extend(v_invoices)

        else:
            invoices = db.get_invoice_list_by_vendor(vendor_id)
            cust_count = db.get_customer_count(vendor_id)
            skonto_period = db.show_skonto_period(vendor_id)[0]["skonto_period"]
            #discount= db.get_discount(vendor_id)

        for i in range(len(invoices)):
            if not invoices[i]["paid"]:
                unpaid_count += 1
            invoices[i]["customer_name"], invoices[i]["email"] = (
                db.get_sus_data(invoices[i]["sus"])[0]
            )
            if vendor_id is not None:
                invoices[i]["discount_period"] = skonto_period

        return render_template("teacher/dashboard.html",
                               invoices=invoices, shops=raw_shops,
                               cust_count=cust_count, unpaid_count=unpaid_count)#, discount=discount)

    elif request.method == "POST":
        db.set_invoice_as_paid(request.form.get("id"), request.form.get("paid") == "on")
        return redirect(url_for("Lehrkraft-APIs.lehrkraft_dashboard", shop=vendor_id))


@bp.route("/products")
def lehrkraft_products():
    product_liste = []
    teacher_data = db.authenticate_teacher(request, session)
    vendor_id = request.args.get('shop')
    category_id = request.args.get('category')
    all_vendors_infos = db.show_vendors_of_country(teacher_data["country_code"])
    kategory_list = db.get_categories(vendor_id)
    if vendor_id is None:
        return render_template("teacher/teacher_products.html",
                               all_vendors_infos=all_vendors_infos)  # alle infos aller vendors in de
    else:
        if category_id is not None:
            cats = db.get_categories(vendor_id)
            if not int(category_id) in (cat["id"] for cat in cats):
                raise wk.exceptions.NotFound("No such category")

            product_liste_alle = db.show_products(teacher_data["game"], vendor_id)
            for product in product_liste_alle:
                if str(product["category"]) == str(category_id):
                    if "picture" in product and product["picture"] != None:
                        product["pic_b64"] = base64.b64encode(product["picture"])
                    product_liste.append(product)
                if "picture" in product and product["picture"] != None:
                    product["pic_b64"] = base64.b64encode(product["picture"])
            return render_template("teacher/teacher_products.html",
                                   product_liste=product_liste,
                                   all_vendors_infos=all_vendors_infos, kategory_list=kategory_list)
        game = teacher_data["game"]
        product_liste = db.show_products(game, vendor_id)
        for product in product_liste:
            if "picture" in product and product["picture"] != None:
                product["pic_b64"] = base64.b64encode(product["picture"])
        return render_template("teacher/teacher_products.html", product_liste=product_liste,
                               all_vendors_infos=all_vendors_infos,
                               kategory_list=kategory_list)  # product liste gibt alle infos aus db item zurück


@bp.route("/products/edit", methods=["GET", "POST"])
def lehrkraft_products_edit():
    teacher_data = db.authenticate_teacher(request, session)
    vendor_id = request.args.get('shop')
    item_id = request.args.get('product')
    if request.method == "GET":
        product_info = db.get_item(item_id)
        return render_template("teacher/products_edit.html", product_info=product_info)
    elif request.method == "POST":
        infos = request.json
        picture = infos.get("image")
        product_name = infos["name"]
        category = infos["category"]
        canon_id = infos["itemNumber"]
        product_manufacturer = infos["manufacturer"]
        price = infos["price"]
        description = infos["description"]
        result = db.edit_product(item_id, picture, product_name, category, canon_id, product_manufacturer, price,description)
        if result:
            return {"status": "success",
                    "message": "The product has been updated successfully"}
        else:
            return ({"status": "error",
                     "message": "There has been an error :("}, 400)


@bp.route("/products/img")
def lehrkraft_product_imgs():
    product = db.get_item(request.args["product"])
    db.authenticate_teacher(request, session, country_code=product["country_code"])

    may_pic = product.get("picture")

    if may_pic is None:
        return Response(":(", mimetype="text/plain")
    else:
        return Response(may_pic, mimetype=magic.from_buffer(may_pic, mime=True))


@bp.route("/products/import", methods=["POST"])
def lehrkraft_products_import():
    # FIXME: sometimes navigates to shop selection when import button is pressed, might be frontend issue
    teacher_data = db.authenticate_teacher(request, session)
    game = teacher_data["game"]
    vendor_id = request.args.get('shop')
    category = request.args.get('category')
    if request.method == "POST":
        data = request.get_json()
        # check for emptiness
        for product in data:
            for product_key in product:
                if product[product_key] is None or product[product_key] == "":
                    return {"status": "error",
                            "message": "Import unsuccessful, " + str(product_key) +
                                       " of this json product: " + str(product) + " is missing"}

        # importing itself
        unsuccessful_import_count = 0
        unsuccessful_import_products = []
        for product in data:
            result = db.add_product(game, product.get("picture"), product.get("name"),
                            category, product.get("canon_id"), product.get("manufacturer"),
                            product.get("price"), product.get("description"))
            if not result:
                unsuccessful_import_count += 1
                unsuccessful_import_products.append(product)

        if unsuccessful_import_count != 0:
            return {"status": "error",
                    "message": "Partially erroneous import: " +
                               str(unsuccessful_import_count) + " of " + str(len(data)) +
                               " products not imported, " + str(unsuccessful_import_count) +
                               " products were not added: " + str(unsuccessful_import_products) +
                               " due to already being in the database or other reasons."}
        else:
            return {"status": "success",
                    "message": str(len(data)) + " Products imported successfully"}


@bp.route("/products/add", methods=["GET", "POST"])
def lehrkraft_products_add():
    vendor_id = request.args.get('shop')
    teacher_data = db.authenticate_teacher(request, session)

    if request.method == "GET":
        if vendor_id is None:
            return redirect(url_for("Lehrkraft-APIs.lehrkraft_products"))
        else:
            list_categories = db.get_categories(vendor_id)
            return render_template("teacher/products_add.html", categories=list_categories)
    elif request.method == "POST":
        infos = request.json
        picture = infos.get("image")
        product_name = infos.get("name")
        category = infos.get("category")
        canon_id = infos.get("itemNumber")
        product_manufacturer = infos.get("manufacturer")
        price = infos.get("price")
        description = infos.get("description")
        game = teacher_data["game"]
        result = db.add_product(game, picture, product_name, category, canon_id, product_manufacturer, price,
                                description)
        if result:
            return {"status": "success",
                    "message": "The produkt has been added successfully"}
        else:
            return ({"status": "error",
                     "message": "There was an error :("}, 400)


@bp.route("/products/del", methods=["POST"])
def lehrkraft_products_del():
    if request.method == "POST":
        teacher_data = db.authenticate_teacher(request, session)
        data = request.get_json()
        canon_id = data.get("canon_id")
        category = data.get("category")
        # Delete the product from the database
        result = db.delete_product(canon_id, category)
        return jsonify({"success": result})


@bp.route("/category-management", methods=["GET", "POST"])
def lehrkraft_category_management():
    vendor_id = request.args["shop"]
    vendor = db.get_vendor(vendor_id)
    db.authenticate_teacher(request, session, country_code=vendor["country_code"])

    cat_names = [cat["name"] for cat in db.get_categories(vendor_id)]

    if request.method == "GET":
        return render_template("teacher/category-management.html", categories=cat_names)

    elif request.method == "POST":
        cats_old = set(cat_names)
        cats_new = set(request.json["categories"])

        cats_to_add = cats_new.difference(cats_old)
        cats_to_remove = cats_old.difference(cats_new)
        db.add_categories(vendor_id, cats_to_add)
        db.del_categories(vendor_id, cats_to_remove)

        return {"status": "success",
                "message": "The categories have been updated successfully"}


@bp.route("/administration", methods=["GET"])
def lehrkraft_administration():
    teacher_data = db.authenticate_teacher(request, session)
    country_code = teacher_data["country_code"]
    game = teacher_data["game"]
    sus_deeplink = db.get_sus_deeplink(game, country_code)
    sus_deeplink = sus_deeplink["link"]
    if request.method == "GET":
        all_vendors_infos = db.show_vendors_of_country(country_code)
        return render_template("teacher/teacher_administration.html",
                               all_vendors_infos=all_vendors_infos,
                               sus_deeplink=sus_deeplink,
                               teacher=teacher_data)
    raise NotImplementedError


@bp.route("/administration/add-vendor", methods=["GET", "POST"])
def lehrkraft_add_vendor():
    teacher_data = db.authenticate_teacher(request, session)
    if request.method == "GET":
        return render_template("teacher/add_vendor.html")
    elif request.method == "POST":
        infos = request.json
        game = teacher_data["game"]
        country_code = teacher_data["country_code"]
        name = infos["name"]
        iban = infos["iban"]
        skonto = infos["skonto"]
        skonto_period = infos["skonto_period"]
        invoice_notes = infos["invoice_notes"]
        logo = infos.get("img")
        result = db.add_vendor(game, name, country_code, iban, skonto, invoice_notes, logo, skonto_period)
        if result:
            flash("Vendor added successfully")
            return {"status": "success",
                    "message": "The vendor has been updated successfully"}
        else:
            flash("An error occurred while adding the vendor")
            return {"status": "error",
                    "message": "The vendor has not been updated successfully"}


@bp.route("/administration/delete-vendor", methods=["POST"])
def lehrkraft_delete_vendor():
    teacher_data = db.authenticate_teacher(request, session)
    if request.method == "POST":
        vendor_id = request.json.get("vendor_id")
        result = db.delete_vendor(vendor_id)
        if result:
            flash("Vendor deleted successfully")
            return {"status": "success",
                    "message": "The vendor has been updated successfully"}
        else:
            flash("An error occurred while deleting the vendor")
            return {"status": "error",
                    "message": "The vendor has not been updated successfully"}
    raise NotImplementedError


@bp.route("/administration/import-vendor", methods=["POST"])
def lehrkraft_import_vendor():
    teacher_data = db.authenticate_teacher(request, session)

    # trying to insert into db
    try:
        name = db.import_vendor(request.json, teacher_data["game"], teacher_data["country_code"])
        return {"status": "success",
                "message": "Successfully imported shop " + name}
    except Exception as e:
        return {"status": "error",
                "message": "An unknown error occured. Maybe a vendor or item with the same name "
                           "already exists? Maybe the formatting is off? error: \n" + str(e)}


@bp.route("/administration/export-vendor", methods=["GET"])
def lehrkraft_export_vendor():
    teacher_data = db.authenticate_teacher(request, session)
    vendor_id = request.args.get('shop')
    return db.export_vendor(vendor_id)


@bp.route("/administration/change_iban", methods=["GET", "POST"])
def lehrkraft_change_iban():
    teacher_data = db.authenticate_teacher(request, session)
    vendor_id = request.args.get('shop')
    if request.method == "GET":
        iban_dict = db.show_iban(vendor_id)[0]
        iban = iban_dict
        return render_template("teacher/iban_change.html", iban=iban)
    elif request.method == "POST":
        iban = request.json.get("iban")
        result = db.change_iban(vendor_id, iban)
        if result:
            flash("Iban changed successfully")
            return {"status": "success",
                    "message": "The vendor has been updated successfully"}
        else:
            flash("An error occurred while changing the iban")
            return {"status": "error",
                    "message": "The vendor has not been updated successfully"}

        raise NotImplementedError


@bp.route("/administration/change_discount", methods=["GET", "POST"])
def lehrkraft_change_discount():
    teacher_data = db.authenticate_teacher(request, session)
    vendor_id = request.args.get('shop')
    if request.method == "GET":
        discount = db.show_discount(vendor_id)[0]
        skonto_period = db.show_skonto_period(vendor_id)[0]
        return render_template("teacher/discount_change.html", discount=discount,skonto_period=skonto_period)
    elif request.method == "POST":
        discount = request.json.get("discount")
        skonto_period = request.json.get("skonto_period")
        result = db.change_discount(vendor_id, discount)
        reuslt1 = db.change_skonto_period(vendor_id, skonto_period)
        if result and reuslt1:
            flash("Discount changed successfully")
            return {"status": "success",
                    "message": "The vendor has been updated successfully"}
        else:
            flash("An error occurred while changing the discount")
            return {"status": "error",
                    "message": "The vendor has not been updated successfully"}
        raise NotImplementedError


@bp.route("/administration/delete", methods=["POST"])
def lehrkraft_delete():
    teacher_data = db.authenticate_teacher(request, session)
    if request.method == "POST":
        id_teacher = teacher_data["id"]
        result = db.delete_teacher(id_teacher)
        if result:
            flash("Account deleted successfully")
            return {"status": "success",
                    "message": "The Account has been updated successfully"}
        else:
            flash("An error occurred while deleting the account")
            return {"status": "error",
                    "message": "The Account has not been updated successfully"}



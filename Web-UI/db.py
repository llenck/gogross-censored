from time import strptime

import sqlalchemy as sql
import secrets, base64
from datetime import datetime, timedelta
import base64

from sqlalchemy import select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.ddl import CreateTable

from pw_hash import pw_hash
import PDFRechnunggen as pdf


@compiles(CreateTable, "sqlite")
def tables_are_strict(create_table, compiler, **kw):
    return compiler.visit_create_table(create_table, **kw).rstrip() + "STRICT"


# without these, sqlite fails to create strict tables
@compiles(sql.types.String, "sqlite")
def compile_str_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(sql.types.Boolean, "sqlite")
def compile_bool_sqlite(type_, compiler, **kw):
    return "INT"


@compiles(sql.types.DateTime, "sqlite")
def compile_datetime_sqlite(type_, compiler, **kw):
    return "TEXT"  # nicht optimal lol


@sql.event.listens_for(sql.Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


engine = sql.create_engine("sqlite+pysqlite:///persist/gogross-data.db", echo=True)
meta_obj = sql.MetaData()


# TODO im ganzen login & lookups & so sollten wir fehler zurückgeben, wenn das
# zugehörige planspiel nicht läuft

def gen_deeplink():
    return secrets.token_urlsafe(18)


game = sql.Table(
    "game",
    meta_obj,
    sql.Column("name", sql.String(24), primary_key=True),
    sql.Column("running", sql.Boolean),
)

# NOTE possible optimization: change the link format to id_key where
# id is an int representing a PK in this table, which has the full key as
# another column
teacher_deeplink = sql.Table(
    "teacher_deeplink",
    meta_obj,
    sql.Column("link", sql.String(24), primary_key=True),
    sql.Column("game", sql.ForeignKey("game.name", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
)

sus_deeplink = sql.Table(
    "sus_deeplink",
    meta_obj,
    sql.Column("link", sql.String(24), primary_key=True),
    sql.Column("game", sql.ForeignKey("game.name", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    sql.Column("country_code", sql.String(2), nullable=False),
)

pw_reset_token = sql.Table(
    "pw_reset_token",
    meta_obj,
    sql.Column("token_hash", sql.LargeBinary, primary_key=True),
    sql.Column("email", sql.String(64), nullable=False),
    sql.Column("expiry_date", sql.DateTime, nullable=False),
    sql.Column("vendor_id", sql.ForeignKey(
        "vendor.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=True),
)

# NOTE ab hier divergiere ich von den angegebenen produktdaten. Statt composite
# PKs benutze ich doch ids, da FKs auf tables mit composite PKs sehr painful
# sind.
vendor = sql.Table(
    "vendor",
    meta_obj,
    sql.Column("id", sql.Integer, primary_key=True),
    sql.Column("name", sql.String(24), nullable=False),
    sql.Column("game", sql.ForeignKey("game.name", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    sql.Column("country_code", sql.String(2), nullable=False),
    sql.Column("iban", sql.String(22), nullable=False),
    sql.Column("discount", sql.Integer, nullable=False),  # 1/1000ths
    sql.Column("skonto_period", sql.Integer, nullable=False),
    sql.Column("invoice_notes", sql.String(1024)),
    sql.Column("logo", sql.LargeBinary),

    sql.UniqueConstraint("game", "name"),
)

sus_acc = sql.Table(
    "sus_acc",
    meta_obj,
    sql.Column("id", sql.Integer, primary_key=True),
    sql.Column("vendor", sql.ForeignKey("vendor.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    sql.Column("email", sql.String(64), nullable=False),
    sql.Column("name", sql.String(64), nullable=False),
    sql.Column("pass_hash", sql.LargeBinary, nullable=False),

    sql.UniqueConstraint("vendor", "email"),
)

lehrkraft_acc = sql.Table(
    "lehrkraft_acc",
    meta_obj,
    sql.Column("id", sql.Integer, primary_key=True),
    sql.Column("game", sql.ForeignKey("game.name", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    sql.Column("email", sql.String(64), nullable=False, unique=True),
    sql.Column("country_code", sql.String(64), nullable=False),
    sql.Column("name", sql.String(64), nullable=False),
    sql.Column("pass_hash", sql.LargeBinary, nullable=False),
)

category = sql.Table(
    "category",
    meta_obj,
    sql.Column("id", sql.Integer, primary_key=True),
    sql.Column("vendor", sql.ForeignKey("vendor.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    sql.Column("name", sql.String(64), nullable=False),

    sql.UniqueConstraint("vendor", "name"),
)

item = sql.Table(
    "item",
    meta_obj,
    sql.Column("id", sql.Integer, primary_key=True),
    sql.Column("category", sql.ForeignKey("category.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    sql.Column("game", sql.ForeignKey("game.name", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    sql.Column("canon_id", sql.Integer, nullable=False),
    sql.Column("name", sql.String(64), nullable=False),
    sql.Column("manufacturer", sql.String(64), nullable=False),
    sql.Column("description", sql.String(64), nullable=False),
    sql.Column("price", sql.Integer, nullable=False),
    sql.Column("picture", sql.LargeBinary),

    sql.UniqueConstraint("game", "canon_id"),
)

invoice = sql.Table(
    "invoice",
    meta_obj,
    sql.Column("id", sql.Integer, primary_key=True),
    sql.Column("canon_id", sql.Integer, nullable=False),
    sql.Column("vendor", sql.ForeignKey("vendor.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    sql.Column("sus", sql.ForeignKey("sus_acc.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    sql.Column("date", sql.DateTime, nullable=False),
    # NOTE: das ist tendenziell nicht total normalisiert. total könnte
    # inconsistent mit den zugehörigen 'invoice_item's sein
    sql.Column("total", sql.Integer, nullable=False),
    sql.Column("total_discounted", sql.Integer, nullable=False),
    sql.Column("paid", sql.Boolean, nullable=False),
    # true -> belongs to a shopping cart, false -> an actual, finished invoice.
    # (das wort benutze ich auch nur weils cool klingt)
    # TODO shopping cart expiry, sonst ist das wort "ephemeral" ja sogar falsch lol
    sql.Column("ephemeral", sql.Boolean, nullable=False),

    sql.UniqueConstraint("vendor", "canon_id"),
)

invoice_item = sql.Table(
    "invoice_item",
    meta_obj,
    sql.Column("invoice", sql.ForeignKey("invoice.id", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True),
    sql.Column("canon_id", sql.Integer, primary_key=True),
    # TODO das ondelete=CASCADE ist problematisch. gehts besser?
    sql.Column("item", sql.ForeignKey("item.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    sql.Column("quantity", sql.Integer, nullable=False),
    sql.Column("price_per_unit", sql.Integer, nullable=False),
    sql.Column("total", sql.Integer, nullable=False),
)

invoice_pdf = sql.Table(
    "invoice_pdf",
    meta_obj,
    sql.Column("id", sql.Integer, primary_key=True),
    sql.Column("pdf", sql.LargeBinary, nullable=False),
)

# NOTE bei schema-changes müsste man so bisher manuell die DB droppen.
# das könnte man vllt mit irgendwelchen hashsachen automatisieren
meta_obj.create_all(engine)


def add_vendor(game, name, country_code, iban, discount, invoice_notes, logo, skonto_period):
    discount = int(discount)
    skonto_period = int(skonto_period)
    vals = {"game": game, "name": name, "country_code": country_code, "iban": iban, "discount": discount,
            "skonto_period": skonto_period,
            "invoice_notes": invoice_notes}
    if not logo is None:
        vals["logo"] = bytes(base64.b64decode(logo))
    ins_vendor_stmt = sql.insert(vendor).values(**vals)
    try:
        with engine.begin() as conn:
            conn.execute(ins_vendor_stmt)
        return True
    except sql.exc.IntegrityError as e:
        return False


def delete_teacher(id) -> bool:
    id = int(id)
    delete_stmt = lehrkraft_acc.delete().where(lehrkraft_acc.c.id == id)
    with engine.begin() as connection:
        return connection.execute(delete_stmt).rowcount > 0


def delete_vendor(vendor_id) -> bool:
    delete_stmt = vendor.delete().where(vendor.c.id == vendor_id)
    with engine.begin() as connection:
        return connection.execute(delete_stmt).rowcount > 0


def add_product(game, picture, product_name, category, canon_id, product_manufacturer, price, description):
    category = int(category)
    canon_id = int(canon_id)
    vals = {"game": game, "category": category, "canon_id": canon_id, "name": product_name,
            "manufacturer": product_manufacturer, "description": description, "price": price}
    if not picture is None:
        vals["picture"] = bytes(base64.b64decode(picture))
    ins_item_stmt = sql.insert(item).values(**vals)
    try:
        with engine.begin() as conn:
            conn.execute(ins_item_stmt)
        return True
    except sql.exc.IntegrityError as e:
        return False


def edit_product(item_id, picture, product_name, category, canon_id, product_manufacturer, price, description):
    category = int(category)
    canon_id = int(canon_id)
    vals = {"category": category, "canon_id": canon_id, "name": product_name,
            "manufacturer": product_manufacturer, "description": description, "price": price}
    if not picture is None:
        vals["picture"] = bytes(base64.b64decode(picture))
    update_stmt = item.update().where(item.c.id == item_id).values(**vals)
    with engine.begin() as conn:
        return conn.execute(update_stmt).rowcount > 0


def delete_product(canon_id, category) -> bool:
    category = int(category)
    delete_stmt = item.delete().where((item.c.canon_id == canon_id) & (item.c.category == category))
    with engine.begin() as connection:
        return connection.execute(delete_stmt).rowcount > 0


def lehrkraft_register(game, name, country_code, email, pw):
    country_exists = sql.select(sus_deeplink).where(
        (sus_deeplink.c.game == game)
        & (sus_deeplink.c.country_code == country_code))

    ins_lehrkraft_stmt = sql.insert(lehrkraft_acc).values(game=game, email=email,
                                                          country_code=country_code, name=name, pass_hash=pw_hash(pw))

    try:
        with engine.begin() as conn:
            if len(list(conn.execute(country_exists))) == 0:
                # no sus deeplink for this country exists (yet); create one
                ins_sus_dl = sql.insert(sus_deeplink).values(game=game,
                                                             country_code=country_code, link=gen_deeplink())
                conn.execute(ins_sus_dl)

            conn.execute(ins_lehrkraft_stmt)
        return True
    except sql.exc.IntegrityError as e:
        return False


def sus_register(vendor_id, name, email, pw):
    ins_stud_stmt = sus_acc.insert().values(vendor=vendor_id, name=name, email=email, pass_hash=pw_hash(pw))
    try:
        with engine.begin() as conn:
            conn.execute(ins_stud_stmt)
        return True
    except sql.exc.IntegrityError as e:
        return False


def change_pw(email, token, new_pw, vendor=None):
    """changes pw, expires the token of reset link in db

    :param email:
    :param token:
    :param new_pw:
    :param vendor: optional arg for sus case
    :return:
    """
    # update either lk or sus pw
    tbl = lehrkraft_acc if vendor is None else sus_acc
    update_pw = sql.update(tbl).where(
        tbl.c.email == email).values(
        pass_hash=pw_hash(new_pw)) if vendor is None else sql.update(tbl).where(
        tbl.c.email == email and tbl.c.vendor == vendor).values(
        pass_hash=pw_hash(new_pw))

    # set token to expired
    update_token = sql.update(pw_reset_token).where(
        pw_reset_token.c.token_hash == pw_hash(token)).values(
        expiry_date=datetime.now())

    with engine.begin() as conn:
        conn.execute(update_pw)
        conn.execute(update_token)


def get_sus_deeplink(game, country_code):
    stmt = sql.select(sus_deeplink).where(
        (sus_deeplink.c.game == game) & (sus_deeplink.c.country_code == country_code))
    with engine.begin() as connection:
        return connection.execute(stmt).mappings().one_or_none()


def show_vendors_of_country(land):  # gibt liste der vendor einer nation aus
    query = sql.select(*vendor.columns).where(vendor.c.country_code == land)
    with engine.begin() as connection:
        result_proxy = connection.execute(query)
    vendors = [dict(row._mapping) for row in result_proxy]
    return vendors


def show_vendors_of_country_and_game(land, game_name) -> list:
    query = sql.select(vendor.columns).where(
        vendor.c.country_code == land and vendor.c.game == game_name)
    with engine.begin() as connection:
        result_proxy = connection.execute(query)
    vendors = [dict(row._mapping) for row in result_proxy]
    return vendors


def get_categories(vendor_id):
    query = sql.select(category).where(
        category.c.vendor == vendor_id
    )
    with engine.begin() as connection:
        result = connection.execute(query)
    categories = [dict(row._mapping) for row in result]
    return categories


def get_item(item_id):
    query = sql.select(item).where(
        item.c.id == item_id
    )
    with engine.begin() as connection:
        result = connection.execute(query)
    items = [dict(row._mapping) for row in result]
    return items


def add_categories(vendor_id, cats):
    with engine.begin() as conn:
        for cat in cats:
            ins = sql.insert(category).values(vendor=vendor_id, name=cat)
            conn.execute(ins)


def del_categories(vendor_id, cats):
    with engine.begin() as conn:
        for cat in cats:
            ins = sql.delete(category).where(
                (category.c.vendor == vendor_id)
                & (category.c.name == cat))
            conn.execute(ins)


def get_vendor(vendor_id):
    stmt = sql.select(*vendor.columns).where(vendor.c.id == vendor_id)
    with engine.begin() as conn:
        return conn.execute(stmt).mappings().one()


def get_vendor_ids(shops) -> list:
    l = []
    for shop in shops:
        l.append(shop["id"])
    return l


def get_customer_count(vendor_id) -> int:
    stmt = sql.select(sus_acc).where(sus_acc.c.vendor == vendor_id)
    with engine.begin() as conn:
        return len(list(conn.execute(stmt)))


# besides item data, also return country & vendor id (the latter as id_1)
def get_item(item_id):
    stmt = sql.select(*item.columns, vendor.c.id, vendor.c.country_code) \
        .select_from(item) \
        .join(category) \
        .join(vendor) \
        .where(item.c.id == item_id)
    with engine.begin() as conn:
        return conn.execute(stmt).mappings().one()


def get_vendor_items(vendor_id):
    stmt = sql.select(*item.columns) \
        .select_from(item) \
        .join(category) \
        .where(category.c.vendor == vendor_id)
    with engine.begin() as conn:
        return conn.execute(stmt).mappings().all()


def get_pw_reset_token(email: str, vendor_id=None) -> str:
    """
    generates and stores pw_reset link with a certain timeout

    :param email: users email, assumed to be in db
    :param vendor_id: optional, required if resetting sus pw
    :return: pw reset token (the full link is generated in the handler)
    """
    TIMEOUT = 30  # in minutes
    token = gen_deeplink()
    ins_token_stmt = sql.insert(pw_reset_token).values(
        token_hash=pw_hash(token), email=email,
        expiry_date=datetime.now() + timedelta(minutes=TIMEOUT),
        vendor_id=None if vendor_id is None else vendor_id
    )
    with engine.begin() as conn:
        conn.execute(ins_token_stmt)

    return token


def get_tokens_row(token) -> list:
    stmt = sql.select(pw_reset_token).where(
        pw_reset_token.c.token_hash == pw_hash(token))
    with engine.begin() as conn:
        return list(conn.execute(stmt))


def get_tokens_email(token) -> str:
    rs = get_tokens_row(token)
    [(_, email, _, _)] = rs
    return email


def get_tokens_vendor_id(token) -> int:
    rs = get_tokens_row(token)
    [(_, _, _, vendor)] = rs
    return vendor


def change_iban(vendor_id, new_iban) -> bool:
    stmt = sql.update(vendor).where(vendor.c.id == vendor_id).values(iban=new_iban)
    with engine.begin() as conn:
        return conn.execute(stmt).rowcount > 0


def change_discount(vendor_id, new_discount) -> bool:
    new_discount = int(new_discount)
    stmt = sql.update(vendor).where(vendor.c.id == vendor_id).values(discount=new_discount)
    with engine.begin() as conn:
        return conn.execute(stmt).rowcount > 0


def change_skonto_period(vendor_id, new_skonto_period) -> bool:
    new_skonto_period = int(new_skonto_period)
    stmt = sql.update(vendor).where(vendor.c.id == vendor_id).values(skonto_period=new_skonto_period)
    with engine.begin() as conn:
        return conn.execute(stmt).rowcount > 0


def show_skonto_period(vendor_id):
    query = sql.select(vendor.c.skonto_period).where(vendor.c.id == vendor_id)
    with engine.begin() as connection:
        result = connection.execute(query)
    skonto_period = [dict(row._mapping) for row in result]
    return skonto_period


def show_discount(vendor_id):
    query = sql.select(vendor.c.discount).where(vendor.c.id == vendor_id)
    with engine.begin() as connection:
        result = connection.execute(query)
    discount = [dict(row._mapping) for row in result]
    return discount


def show_iban(vendor_id):
    query = sql.select(vendor.c.iban).where(vendor.c.id == vendor_id)
    with engine.begin() as connection:
        result = connection.execute(query)
    iban = [dict(row._mapping) for row in result]
    return iban


def get_invoices(sus):
    stmt = sql.select(*invoice.columns).where((invoice.c.sus == sus["id"]) & (invoice.c.ephemeral == False))
    with engine.begin() as conn:
        return conn.execute(stmt).mappings().all()


def get_sus_data(sus_id) -> list[(str, str)]:
    """
    :param sus_id:
    :return: list of tupel of name and email
    """
    stmt = sql.select(sus_acc.c.name, sus_acc.c.email).where(
        sus_acc.c.id == sus_id)
    with engine.begin() as conn:
        return list(conn.execute(stmt))


def cart_epheremal_or_new(sus, may_cart_id):
    with engine.begin() as conn:
        existing_cart_stmt = sql.select(invoice.c.ephemeral).where(invoice.c.id == may_cart_id)
        ex_cart = conn.execute(existing_cart_stmt).mappings().all()
        if len(ex_cart) == 1 and ex_cart[0]["ephemeral"]:
            return may_cart_id

        prior_max_stmt = sql.select(sql.func.max(invoice.c.canon_id)) \
            .where(invoice.c.vendor == sus["vendor"])

        prior_max = conn.execute(prior_max_stmt).fetchone()[0]
        if prior_max is None:
            prior_max = 0
        new_id = prior_max + 1

        new_invoice_stmt = sql.insert(invoice) \
            .values(canon_id=new_id, vendor=sus["vendor"], sus=sus["id"],
                    date=datetime.now(), total=0, total_discounted=0, paid=False,
                    ephemeral=True)
        return conn.execute(new_invoice_stmt).inserted_primary_key[0]


def get_cart(cart_id):
    with engine.begin() as conn:
        stmt = sql.select(item.c.id, item.c.manufacturer, item.c.name, item.c.canon_id,
                          item.c.description, invoice_item.c.total,
                          invoice_item.c.quantity, invoice_item.c.invoice,
                          invoice.c.ephemeral, invoice_item.c.canon_id, invoice_item.c.price_per_unit) \
            .select_from(invoice_item) \
            .join(item) \
            .join(invoice) \
            .where(invoice_item.c.invoice == cart_id)
        lines = conn.execute(stmt).mappings().all()

        if not all((l["ephemeral"] for l in lines)):
            raise ValueError("cart-id belongs to a non-ephemeral invoice")

        lines = [dict(row) for row in lines]
        for d in lines:
            d["item_id"] = d.pop("id")
            d["item_canon_id"] = d.pop("canon_id")
            d["canon_id"] = d.pop("canon_id_1")

        return lines


def checkout_cart(cart_id):
    # this also checks whether the cart is ephemeral
    cart = get_cart(cart_id)
    if len(cart) == 0:
        raise ValueError("Cart is empty")

    with engine.begin() as conn:
        vendor_discount_stmt = sql.select(vendor.c.discount, vendor.c.skonto_period) \
            .select_from(vendor) \
            .join(invoice) \
            .where(invoice.c.id == cart_id)
        vendor_data = conn.execute(vendor_discount_stmt).mappings().one()
        total = sum((it["total"] for it in cart))
        total_discounted = int(total * (1000 - vendor_data["discount"]) / 1000 + 0.5)

        bake_stmt = sql.update(invoice) \
            .where(invoice.c.id == cart_id) \
            .values(date=datetime.now(), total=total, total_discounted=total_discounted,
                    paid=False, ephemeral=False)
        conn.execute(bake_stmt)

        # now, also create/insert the pdf
        (inv_hdr, inv_lines) = get_invoice_info(cart_id)
        date_str = datetime.now().strftime("%d.%m.%Y")
        pdf_bytes = pdf.create_invoice(
            inv_hdr["iban"], inv_hdr["canon_id"], date_str, total,
            total_discounted, inv_hdr["name"], inv_hdr["invoice_notes"],
            inv_lines, vendor_data["skonto_period"], inv_hdr["logo"])
        ins_pdf_stmt = sql.insert(invoice_pdf).values(id=cart_id, pdf=pdf_bytes)
        return conn.execute(ins_pdf_stmt).inserted_primary_key[0]


def get_invoice_pdf(inv_id):
    with engine.begin() as conn:
        sel_stmt = sql.select(invoice_pdf).where(invoice_pdf.c.id == int(inv_id))
        return conn.execute(sel_stmt).mappings().one()["pdf"]


def add_to_cart(cart_id, item_id, item_cnt):
    with engine.begin() as conn:
        item = get_item(item_id)
        vendor_id = item["id_1"]

        max_line_no_stmt = sql.select(sql.func.max(invoice_item.c.canon_id)) \
            .select_from(invoice_item) \
            .join(invoice) \
            .where(invoice.c.vendor == vendor_id)

        prior_max = conn.execute(max_line_no_stmt).fetchone()[0]
        if prior_max is None:
            prior_max = 0
        new_id = prior_max + 1

        ins_line_stmt = sql.insert(invoice_item) \
            .values(invoice=cart_id, canon_id=new_id, item=item_id, quantity=item_cnt,
                    price_per_unit=item["price"], total=item["price"] * item_cnt)
        conn.execute(ins_line_stmt)

        # NOTE we update the values of the invoice containing the items at checkout.


def del_from_cart(cart_id, line_id):
    with engine.begin() as conn:
        del_stmt = sql.delete(invoice_item) \
            .where((invoice_item.c.invoice == cart_id)
                   & (invoice_item.c.canon_id == line_id))
        # NOTE we update the values of the invoice containing the items at checkout.
        return conn.execute(del_stmt).rowcount > 0


def get_invoice_info(inv_id):
    with engine.begin() as conn:
        stmt = sql.select(item.c.canon_id, item.c.name, invoice_item.c.quantity,
                          invoice_item.c.price_per_unit, invoice_item.c.total) \
            .select_from(invoice_item) \
            .join(item) \
            .where(invoice_item.c.invoice == inv_id)
        inv_lines = conn.execute(stmt).mappings().all()

        inv_header = sql.select(invoice.c.canon_id, invoice.c.date, invoice.c.total,
                                invoice.c.total_discounted, vendor.c.name, vendor.c.logo,
                                vendor.c.invoice_notes, vendor.c.iban) \
            .select_from(invoice) \
            .join(vendor) \
            .where(invoice.c.id == inv_id)
        inv = conn.execute(inv_header).mappings().one()

        return (inv, inv_lines)


def get_invoices_by_vendor(vendor_id) -> map:
    query = sql.select(invoice).where(invoice.c.vendor == vendor_id)
    with engine.begin() as connection:
        return map(dict, connection.execute(query).mappings().all())


def get_invoice_list_by_vendor(vendor_id) -> list[dict]:
    query = sql.select(invoice).where(invoice.c.vendor == vendor_id)
    with engine.begin() as connection:
        res = connection.execute(query)
    return [dict(row._mapping) for row in res]


def set_invoice_as_paid(inv_id, paid):
    update_paid = sql.update(invoice).where(invoice.c.id == inv_id).values(paid=paid)
    with engine.begin() as connection:
        connection.execute(update_paid)


def show_products(game, vendor_id):  # gibt items aus von spezifischen vendor
    # Erstellen Sie eine SQL-Abfrage, die die Tabellen `item`, `category` und `vendor` verbindet
    query = sql.select(*item.columns).where(
        (item.c.category == category.c.id) &
        (category.c.vendor == vendor.c.id) &
        (vendor.c.id == vendor_id) &
        (item.c.game == game)
    )
    with engine.begin() as connection:
        result = connection.execute(query)
    products = [dict(row._mapping) for row in result]
    return products


def get_games():
    stmt = select(*game.columns, teacher_deeplink.c.link).join(teacher_deeplink)
    with engine.begin() as conn:
        return list(conn.execute(stmt))


def create_game(name):
    deeplink = gen_deeplink()
    game_stmt = sql.insert(game).values(name=name, running=True)
    link_stmt = sql.insert(teacher_deeplink).values(game=name, link=deeplink)

    try:
        with engine.begin() as conn:
            conn.execute(game_stmt)
            conn.execute(link_stmt)
        return deeplink
    except sql.exc.IntegrityError as e:
        return None


# the "full" exports are, so far, not for consumption by import_game but for
# admin display purposes. The only missing information is:
# - shopping carts
def export_game(name, full=False):
    res = {}
    with engine.begin() as conn:
        def sel(stmt):
            return list(conn.execute(stmt))

        if sel(select(game.c.running) \
                       .where(game.c.name == name)) == []:
            raise ValueError("No such game!")

        if full:
            res["teacher_secret"] = sel(select(teacher_deeplink.c.link) \
                                        .where(teacher_deeplink.c.game == name))[0][0]

            res["teacher_accs"] = []
            teacher_accs = sel(select(lehrkraft_acc).where(lehrkraft_acc.c.game == name))
            for (_, _, t_email, t_cc, t_name, _) in teacher_accs:
                teacher_ob = {"mail": t_email, "country_code": t_cc, "name": t_name}
                res["teacher_accs"].append(teacher_ob)

            res["sus_secrets"] = []
            for (link, _, cc) in sel(select(sus_deeplink).where(sus_deeplink.c.game == name)):
                res["sus_secrets"].append({"secret": link, "country_code": cc})

        res["vendors"] = []

        # for every vendor...
        vendors = sel(select(vendor.c.id).where(vendor.c.game == name))
        for row in vendors:
            res["vendors"].append(export_vendor(row[0], full=full))

    return res


def import_game(name, data):
    with engine.begin() as conn:
        def ins(tbl, **kwarg):
            return conn.execute(sql
                                .insert(tbl)
                                .values(**kwarg)
                                .compile()) \
                .inserted_primary_key[0]

        ins(game, name=name, running=True)
        ins(teacher_deeplink, game=name, link=gen_deeplink())

        sus_dls_generated = set()

        for vendor_data in data["vendors"]:
            # possibly generate sus deeplink for country
            country = vendor_data["country_code"]
            if not country in sus_dls_generated:
                ins(sus_deeplink, game=name, country_code=country,
                    link=gen_deeplink())
                sus_dls_generated.add(country)

            # pop categories, convert logo to blob
            categories = vendor_data.pop("categories")
            if "logo" in vendor_data:
                vendor_data["logo"] = base64.b64decode(vendor_data["logo"])

            # insert all remaining fields
            vendor_id = ins(vendor, game=name, **vendor_data)

            for (cat_name, cat_items) in categories.items():
                cat_id = ins(category, vendor=vendor_id, name=cat_name)

                for it in cat_items:
                    it_props = {"category": cat_id, "game": name, "canon_id": it["id"],
                                "name": it["name"], "manufacturer": it["manufacturer"],
                                "description": it["description"], "price": it["price"]}
                    if "picture" in it:
                        it_props["picture"] = base64.b64decode(it["picture"])
                    ins(item, **it_props)


def import_vendor(vendor_data, game, country_code) -> str:
    with engine.begin() as conn:
        def ins(tbl, **kwarg):
            return conn.execute(sql
                                .insert(tbl)
                                .values(**kwarg)
                                .compile()) \
                .inserted_primary_key[0]

        # generate sus deeplink for country if needed
        sus_dl = get_sus_deeplink(game, vendor_data["country_code"])
        if sus_dl is None:
            ins(sus_deeplink, game=game, country_code=vendor_data["country_code"],
                link=gen_deeplink())

        # pop categories, convert logo to blob
        categories = vendor_data.pop("categories")
        if "logo" in vendor_data:
            vendor_data["logo"] = base64.b64decode(vendor_data["logo"])

        # set country to passed value instead of exported value
        vendor_data["country_code"] = country_code

        # insert all remaining fields
        vendor_id = ins(vendor, game=game, **vendor_data)

        for (cat_name, cat_items) in categories.items():
            cat_id = ins(category, vendor=vendor_id, name=cat_name)

            # TODO: design decision: if a product of a valid new vendor already exists the following
            # part throws and the user is warned, should this be circumvented or should the importer
            # know better?
            for it in cat_items:
                it_props = {"category": cat_id, "game": game, "canon_id": it["id"],
                            "name": it["name"], "manufacturer": it["manufacturer"],
                            "description": it["description"], "price": it["price"]}
                if "picture" in it:
                    it_props["picture"] = base64.b64decode(it["picture"])
                ins(item, **it_props)
        return vendor_data["name"]


def export_vendor(v_id, full=False) -> dict[list[dict]]:
    """
    :param v_id: vendor id
    :param full: extended export: for administration use only, not compatible with import vendor
    :return: dict with list of one vendor, compatible with export_game format
    """
    res = {}
    res["vendors"] = []
    with engine.begin() as conn:
        def sel(stmt):
            return list(conn.execute(stmt))

        [(vendor_id, name, _, country_code, iban, discount, skonto_period, invoice_notes, logo)] = \
            sel(select(*vendor.columns).where(vendor.c.id == v_id))
        vendor_data = {"name": name, "country_code": country_code, "iban": iban,
                       "discount": discount, "skonto_period": skonto_period,
                       "invoice_notes": invoice_notes, "categories": {}}
        if not logo is None:
            vendor_data["logo"] = str(base64.b64encode(logo), encoding="utf-8")

        if full:
            vendor_data["sus_accs"] = export_sus_accs(vendor_id)

        # for every category...
        categories = sel(select(*category.columns).where(category.c.vendor == vendor_id))
        for (cat_id, _, cat_name) in categories:
            items = sel(select(*item.columns).where(item.c.category == cat_id))

            cat_data = []

            # for every item in this category...
            for (_, _, _, it_id, name, manu, desc, price, pic) in items:
                it_data = {"id": it_id, "name": name, "manufacturer": manu,
                           "description": desc, "price": price}
                if not pic is None:
                    it_data["picture"] = str(base64.b64encode(pic), encoding="utf-8")
                cat_data.append(it_data)

            vendor_data["categories"][cat_name] = cat_data

        return vendor_data


def export_sus_accs(vendor_id) -> list[dict]:
    """
    :param vendor_id:
    :return: list of sus accs with nested data, that is associated to the particular sus acc,
    such as invoices and invoice items
    """
    l = []
    with engine.begin() as conn:
        def sel(stmt):
            return list(conn.execute(stmt))

        # sus_accs
        sus_accs = sel(select(*sus_acc.columns).where(sus_acc.c.vendor == vendor_id))
        for (sus_id, _, sus_mail, sus_name, _) in sus_accs:
            sus_obj = {"mail": sus_mail, "name": sus_name, "invoices": []}

            # sus_accs invoices
            invoices = sel(select(*invoice.columns) \
                           .where((invoice.c.sus == sus_id) & (invoice.c.ephemeral == False)))
            for (inv_id, inv_cid, _, _, date, total, total_dc, paid, _) in invoices:
                inv_ob = {"id": inv_cid, "date": date, "total": total,
                          "total_discounted": total_dc, "paid": paid, "items": []}

                # invoices items
                items = sel(select(*invoice_item.columns, item.c.canon_id) \
                            .select_from(invoice_item) \
                            .join(item) \
                            .where(invoice_item.c.invoice == inv_id))
                for (_, inv_it_cid, _, cnt, ppu, total, it_cid) in items:
                    inv_it_ob = {"id": inv_it_cid, "count": cnt,
                                 "price_per_unit": ppu, "total": total, "item_id": it_cid}

                    inv_ob["items"].append(inv_it_ob)
                sus_obj["invoices"].append(inv_ob)
            l.append(sus_obj)
    return l


def clear_game(name):
    # really inefficient, but generic & safe-ish implementation:
    # export the game, import it under a different name, delete the original,
    # rename the newly imported game to the original one.
    tmp_name = gen_deeplink()
    backup = export_game(name)
    import_game(tmp_name, backup)
    delete_game(name)
    with engine.begin() as conn:
        upd = sql.update(game).where(game.c.name == tmp_name).values(name=name)
        conn.execute(upd)


def delete_game(name):
    with engine.begin() as conn:
        game_deletion = sql.delete(game).where(game.c.name == name)
        conn.execute(game_deletion)


def set_game_state(name, running):
    stmt = sql.update(game).where(game.c.name == name).values(running=running)

    with engine.begin() as conn:
        conn.execute(stmt)


# gibt game-id zurück
def is_teacher_deeplink(req, dl) -> str:
    stmt = sql.select(teacher_deeplink).where(teacher_deeplink.c.link == dl)
    with engine.begin() as conn:
        rs = list(conn.execute(stmt))

    if len(rs) != 1:
        raise LehrkraftAuthException("Invalid Deeplink", req)

    [(_, game)] = rs
    return game


def is_change_pw_token(token) -> str or None:
    """

    :param token: token to be investigated
    :return: None if successful, else error str
    """
    rs = get_tokens_row(token)

    if len(rs) != 1:
        # 0 or in insanely rare cases more than one
        return "invalid token"
    else:
        [(_, _, expiry_date, _)] = rs
        # expired conditional
        return None if datetime.now() < expiry_date else "token expired"


# gibt game-id und country code zurück
def is_sus_deeplink(req, dl) -> (str, str):
    stmt = sql.select(sus_deeplink).where(sus_deeplink.c.link == dl)
    with engine.begin() as conn:
        rs = list(conn.execute(stmt))

    if len(rs) != 1:
        raise SusAuthException("Invalid Deeplink", req)

    [(_, game, cc)] = rs
    return (game, cc)


def is_mail(email: str, vendor_id=None) -> bool:
    """
    checks if email is lk or sus email, if only sus should be checked,
    a vendor_id must be specified, else the lk table will be searched only

    :param email:
    :param vendor_id: optional vendor name for sus mail checking
    :return:
    """
    print(email, vendor_id)
    query = sql.select(lehrkraft_acc).where((
            lehrkraft_acc.c.email == email)) if vendor_id is None else sql.select(
        sus_acc).where((sus_acc.c.email == email) & (sus_acc.c.vendor == vendor_id))

    with engine.begin() as connection:
        result = connection.execute(query).fetchone()

    return True if result is not None else False


def login_teacher(email, password, session):
    password_hash = pw_hash(password)
    query = select(lehrkraft_acc.c.pass_hash).where(
        (lehrkraft_acc.c.email == email) & (lehrkraft_acc.c.pass_hash == password_hash))
    with engine.begin() as connection:
        may_ph = connection.execute(query).mappings().one_or_none()
        if may_ph is None:
            return False
        else:
            session["teacher_email"] = email
            session["teacher_pass_hash"] = may_ph["pass_hash"]
            return True


def login_sus(email, password, vendor_id, session):
    stmt = select(sus_acc.c.pass_hash).where(
        (sus_acc.c.email == email)
        & (sus_acc.c.pass_hash == pw_hash(password))
        & (sus_acc.c.vendor == vendor_id))
    with engine.begin() as connection:
        may_ph = connection.execute(stmt).mappings().one_or_none()
        if may_ph is None:
            return False
        else:
            session["sus_email"] = email
            session["sus_shop"] = vendor_id
            session["sus_pass_hash"] = may_ph["pass_hash"]
            return True


class LehrkraftAuthException(Exception):
    def __init__(self, msg, req):
        super().__init__(msg)
        self.message = msg
        self.request = req


class SusAuthException(Exception):
    def __init__(self, msg, req, deeplink=None, shop=None):
        super().__init__(msg)
        self.message = msg
        self.request = req
        self.deeplink = deeplink
        self.shop = shop


# gibt alle daten über den lehrer zurück. benötigte attribute können als
# kwargs mitgegeben werden.
def authenticate_teacher(req, session, **required_attributes):
    if "teacher_email" not in session:
        raise LehrkraftAuthException("Not authenticated", req)

    stmt = sql.select(lehrkraft_acc).where(lehrkraft_acc.c.email == session["teacher_email"])
    with engine.begin() as conn:
        rs = list(conn.execute(stmt))

    if len(rs) != 1:
        raise LehrkraftAuthException("No such account", req)

    [(l_id, game, email, cc, name, ph)] = rs
    data = {"id": l_id, "game": game, "email": email, "country_code": cc,
            "name": name, "pw_hash": ph}

    if data["pw_hash"] != session.get("teacher_pass_hash"):
        raise LehrkraftAuthException("Password changed; you have been logged out.", req)

    for k, v in required_attributes.items():
        if not k in data.keys():
            raise ValueError("Programmierfehler!")

        if data[k] != v:
            raise LehrkraftAuthException("This account doesn't have access to this resource", req)

    return data


# Nutzerdaten drin sein, d.h. country, zugehöriger Großhändler
def authenticate_sus(req, session, **required_attributes) -> dict:
    path_elems = req.path.split("/")
    dl = path_elems[1] if len(path_elems) >= 2 else None

    if "sus_shop" not in session:
        raise SusAuthException("Not authenticated", req, deeplink=dl)
    shop = session["sus_shop"]
    if "sus_email" not in session:
        raise SusAuthException("Not authenticated", req, deeplink=dl, shop=shop)

    stmt = sql.select(sus_acc).where((sus_acc.c.email == session["sus_email"])
                                     & (sus_acc.c.vendor == session["sus_shop"]))
    with engine.begin() as conn:
        data = conn.execute(stmt).mappings().one_or_none()

    if data is None:
        raise SusAuthException("No such account", req, deeplink=dl, shop=shop)

    if data["pass_hash"] != session.get("sus_pass_hash"):
        raise SusAuthException("Password changed; you have been logged out.", req,
                               deeplink=dl, shop=shop)

    for k, v in required_attributes.items():
        if not k in data.keys():
            raise ValueError("Programmierfehler!")

        if data[k] != v:
            raise SusAuthException("This account doesn't have access to this resource", req, deeplink=dl, shop=shop)

    return data


def setup_test_data():
    meta_obj.drop_all(engine)
    meta_obj.create_all(engine)

    test_image = base64.b64decode(
        "UklGRjwAAABXRUJQVlA4TDAAAAAvF8AFADUoahvJ4Y9mIe5e7/fOTPDY938CnKfb0AEc9G6gB+iixVB/S/M0oP5CXwg=")

    with engine.begin() as conn:
        def ins(tbl, **kwarg):
            r = conn.execute(sql.insert(tbl).values(**kwarg))
            print(r.inserted_primary_key)
            return r.inserted_primary_key[0]

        game_id = ins(game, name="Test Game", running=True)

        teacher_dl = ins(teacher_deeplink, link="insecure-test-link", game=game_id)
        sus_dl = ins(sus_deeplink, link="insecure-test-link", game=game_id,
                     country_code="DE")
        sus_dl2 = ins(sus_deeplink, link="insecure-test-link2", game=game_id,
                      country_code="IE")

        vendor_id = ins(vendor, name="Test Vendor", game=game_id, country_code="DE",
                        iban="IE12BOFI12345678901234", discount=20, skonto_period=14,
                        invoice_notes="bitte schnell bezahlen und so", logo=test_image)

        vendor_id2 = ins(vendor, name="Test Vendor 2", game=game_id, country_code="DE",
                         iban="US12BOFI12345678901234", discount=15, skonto_period=14,
                         invoice_notes="please pay quickly and so")

        vendor_id3 = ins(vendor, name="Test Vendor 3", game=game_id, country_code="IE",
                         iban="US12BOFI12345678906666", discount=16, skonto_period=14,
                         invoice_notes="please pay quickly and so chap")

        sus_acc_id = ins(sus_acc, vendor=vendor_id, email="matheus@web.de",
                         name="Matheusius", pass_hash=pw_hash("testpw123"))

        # Hinzufügen eines weiteren sus_acc
        sus_acc_id2 = ins(sus_acc, vendor=vendor_id2, email="john@web.com",
                          name="John", pass_hash=pw_hash("testpw456"))

        sus_acc_id3 = ins(sus_acc, vendor=vendor_id3, email="john@web.com",
                          name="John", pass_hash=pw_hash("testpw456"))

        lehrkraft_acc_id = ins(lehrkraft_acc, game=game_id,
                               email="admin@blub.de", country_code="DE",
                               name="Hahah", pass_hash=pw_hash("testpw321"))

        # Hinzufügen Weiterer lehrkraft_acc
        lehrkraft_acc_id2 = ins(lehrkraft_acc, game=game_id,
                                email="teacher@blub.com", country_code="DE",
                                name="Teacher", pass_hash=pw_hash("testpw654"))

        lehrkraft_acc_id3 = ins(lehrkraft_acc, game=game_id,
                                email="thisisteacher@blub.de", country_code="IE",
                                name="Hahah", pass_hash=pw_hash("testpw"))

        category_id = ins(category, vendor=vendor_id, name="Drucker")

        # Hinzufügen einer weiteren Kategorie
        category_id2 = ins(category, vendor=vendor_id2, name="Scanner")

        item_id = ins(item, category=category_id, game=game_id, canon_id=123,
                      name="Caaaanon Blah", manufacturer="Canon",
                      description="Ein schlechter drucker", price=25000,
                      picture=test_image)

        # Hinzufügen eines weiteren Artikels
        item_id2 = ins(item, category=category_id2, game=game_id, canon_id=456,
                       name="Epson Scanner", manufacturer="Epson",
                       description="Ein guter Scanner", price=30000)

        inv_id = ins(invoice, canon_id=4321, vendor=vendor_id,
                     sus=sus_acc_id, date=datetime(1970, 1, 1, 0, 0),
                     total=50000, total_discounted=48000, paid=False, ephemeral=True)
        inv_it_id = ins(invoice_item, invoice=inv_id, canon_id=436218796,
                        item=item_id, quantity=2, price_per_unit=25000,
                        total=50000)

        inv_id2 = ins(invoice, canon_id=6543, vendor=vendor_id2,
                      sus=sus_acc_id2, date=datetime(2001, 9, 11, 9, 0),
                      total=60000, total_discounted=57000, paid=False, ephemeral=True)

        inv_it_id2 = ins(invoice_item, invoice=inv_id2, canon_id=654321879,
                         item=item_id2, quantity=1, price_per_unit=30000,
                         total=30000)

        inv_id3 = ins(invoice, canon_id=6543, vendor=vendor_id3,
                      sus=sus_acc_id3, date=datetime(2001, 9, 11, 9, 0),
                      total=60000, total_discounted=57000, paid=False, ephemeral=True)

        inv_it_id3 = ins(invoice_item, invoice=inv_id3, canon_id=235235235,
                         item=item_id2, quantity=6, price_per_unit=23,
                         total=27000)

    checkout_cart(inv_id)
    checkout_cart(inv_id2)
    checkout_cart(inv_id3)

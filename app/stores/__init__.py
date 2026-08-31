from flask import Blueprint

stores_bp = Blueprint('stores', __name__, url_prefix='/stores')

from app.stores import routes  # noqa: E402, F401

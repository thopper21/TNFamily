from flask import Blueprint

grocery_bp = Blueprint('grocery', __name__, url_prefix='/grocery')

from app.grocery import routes  # noqa: E402, F401

# app/home/routes.py
from flask import render_template
from flask_login import login_required, current_user
from app.home import home_bp


@home_bp.route('/')
@login_required
def index():
    return render_template('home/index.html', user=current_user)

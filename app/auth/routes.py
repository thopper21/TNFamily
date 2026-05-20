# app/auth/routes.py
from flask import redirect, url_for, render_template, current_app
from flask_login import login_user, logout_user
from sqlalchemy import select
from authlib.integrations.base_client.errors import OAuthError
from app.auth import auth_bp
from app.extensions import db, oauth
from app.models import User


@auth_bp.route('/login')
def login():
    return render_template('auth/login.html')


@auth_bp.route('/google')
def google():
    redirect_uri = url_for('auth.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/callback')
def callback():
    try:
        token = oauth.google.authorize_access_token()
    except OAuthError:
        return render_template('auth/denied.html', email='unknown'), 400
    user_info = token.get('userinfo')
    if not user_info:
        return render_template('auth/denied.html', email='unknown'), 403
    email = user_info['email']

    if email not in current_app.config.get('APPROVED_EMAILS', []):
        return render_template('auth/denied.html', email=email), 403

    user = db.session.scalar(select(User).where(User.google_id == user_info['sub']))
    if user is None:
        user = User(
            google_id=user_info['sub'],
            email=email,
            name=user_info['name'],
            profile_picture_url=user_info.get('picture'),
        )
        db.session.add(user)
    else:
        user.name = user_info['name']
        user.profile_picture_url = user_info.get('picture')

    db.session.commit()
    login_user(user)
    return redirect(url_for('home.index'))


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

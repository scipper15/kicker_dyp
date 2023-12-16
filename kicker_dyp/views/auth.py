from flask import (
    Blueprint, render_template, flash, redirect, url_for, request
)
from flask_login import login_user, logout_user, login_required
from kicker_dyp.forms import RegistrationForm, LoginForm
from kicker_dyp.models import User
from kicker_dyp import db
from kicker_dyp.database import get_settings

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        login_name = form.username.data
        password = form.password.data

        # Check if user already exists
        existing_user = User.query.filter_by(login_name=login_name).first()
        if login_name != 'info@mitkickzentrale.de':
            flash(
                'info@mitkickzentrale.de is the only user allowed and has already been registered.',
                'danger'
                )
        elif existing_user:
            flash('Login name is already taken. Please choose another.', 'danger')
        else:
            # Create a new user
            new_user = User(login_name=login_name,
                            password=User.hash_password(password))
            db.session.add(new_user)
            db.session.commit()
            flash(
                f'Registration successful! You can now log in as {login_name}.',
                'success'
                )
            return redirect(url_for('auth.login'))

    return render_template('auth_register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login_name = form.username.data
        password = form.password.data

        # Check if user already exists
        existing_user = User.query.filter(
            User.login_name == login_name).first()
        if not existing_user:
            flash('User name does not exist.', 'danger')
            redirect(url_for('auth.login'))
        # Check if password matches hash
        elif existing_user and not existing_user.check_password(password):
            flash(
                f'Wrong Password: {existing_user.password}, password: {password}.', 'danger'
            )
            redirect(url_for('auth.login'))
        # login user
        else:
            login_user(existing_user)
            next_page = request.args.get('next')
            # if settings table is empty ask to set settings
            if not get_settings():
                flash(
                    f'Welcome {login_name}. Please adjust settings.',
                    'success'
                    )
                return redirect(url_for('admin.settings'))
            else:
                flash(f'Welcome {login_name} to the admin panel.', 'success')
                return redirect(url_for('admin.upload'))

    return render_template('auth_login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout successful!', 'success')
    return redirect(url_for('home.index'))

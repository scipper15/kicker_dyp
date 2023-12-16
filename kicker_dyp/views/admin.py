from flask import (
    Blueprint, render_template, flash, redirect, request, url_for
)
from flask_login import login_required
from kicker_dyp.forms import UploadForm, SettingsForm, RevertForm
from kicker_dyp.extract_player_statistics import process_zip_file
from kicker_dyp.database import get_last_match_day, get_settings, revert_standings, save_settings, persist_data2db

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('admin_home.html')


@admin_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = UploadForm()

    if form.validate_on_submit():
        zip_file = form.zip_file.data

        try:
            dyp_results, dyp_date = process_zip_file(zip_file)
            match_days = get_last_match_day()
            if match_days == 0:
                match_days = 1
            else:
                match_days += 1
            persist_data2db(dyp_results, dyp_date, match_days)
            flash("Successfully processed the zip file.", 'success')
            return redirect(url_for('home.index', match_day=match_days))
        except Exception as e:
            flash(f"Error processing zip file: {e}", 'danger')

    return render_template('admin_upload.html', form=form)


@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = SettingsForm(request.form)
    if request.method == 'GET':
        settings = get_settings()
        if settings:
            form.dyp_year.data = settings.dyp_year
            form.dyp_season.data = settings.dyp_season
            form.dyp_start.data = settings.dyp_start
            form.dyp_end.data = settings.dyp_end

    if form.validate_on_submit():
        dyp_year = form.dyp_year.data
        dyp_season = form.dyp_season.data
        dyp_start = form.dyp_start.data
        dyp_end = form.dyp_end.data
        try:
            save_settings(dyp_year, dyp_season, dyp_start, dyp_end)
            flash("Successfully updated settings.", 'success')

            return render_template('admin_settings.html', form=form)
        except Exception as e:
            flash(f"Error saving settings: {e}", 'danger')

    return render_template('admin_settings.html', form=form, settings=settings)


@admin_bp.route('/revert', methods=['GET', 'POST'])
@login_required
def revert():
    form = RevertForm(request.form)
    match_days = get_last_match_day()
    if not match_days:
        match_days = 0
    form.match_day.choices = [day + 1 for day in range(match_days)]

    if form.validate_on_submit():
        match_days = form.match_day.data
        try:
            revert_standings(match_days)
            flash(
                f"Successfully reverted database to including match day {match_days}.", 'success')

            return redirect(url_for('admin.revert'))
        except Exception as e:
            flash(f"Error reverting: {e}", 'danger')

    return render_template('admin_revert.html', form=form)

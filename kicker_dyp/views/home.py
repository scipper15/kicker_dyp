from flask import Blueprint, render_template, flash
import roman
from kicker_dyp.database import read_standings, get_settings, get_last_updated, get_last_match_day, calc_jackpot, get_dyp_dates

home_bp = Blueprint('home', __name__)


@home_bp.route('/', defaults={'match_day': 0})
@home_bp.route('/<int:match_day>', methods=['GET'])
def index(match_day):
    if match_day == 0:
        match_days = get_last_match_day()
        if match_days:
            match_day = match_days
    standings, ranks_before = read_standings(match_day)
    settings = get_settings()
    if settings:
        dyp_year = settings.dyp_year
        dyp_season = roman.toRoman(settings.dyp_season)
        dyp_start = settings.dyp_start
        dyp_end = settings.dyp_end
        last_updated = get_last_updated()
        match_days = get_last_match_day()
        jackpot = calc_jackpot(match_day)
        dyp_dates = get_dyp_dates()
        return render_template('frontend_home.html',
                               standings=standings,
                               ranks_before=ranks_before,
                               dyp_year=dyp_year,
                               dyp_season=dyp_season,
                               dyp_start=dyp_start,
                               dyp_end=dyp_end,
                               last_updated=last_updated,
                               match_day=match_day,
                               match_days=match_days,
                               jackpot=jackpot,
                               dyp_dates=dyp_dates,
                               zip=zip,  # for for loops in template
                               )
    else:
        flash('Login and set meta in settings to make this work.')
        return render_template('frontend_home.html')

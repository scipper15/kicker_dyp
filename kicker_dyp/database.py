from sqlalchemy import distinct, select, func, case, literal_column
from kicker_dyp.models import Settings, Player, Score, players_scores
from kicker_dyp import db


def get_settings():
    settings = db.session.query(Settings).first()
    return settings


def save_settings(dyp_year, dyp_season, dyp_start, dyp_end):
    settings = Settings(
        dyp_year=dyp_year,
        dyp_season=dyp_season,
        dyp_start=dyp_start,
        dyp_end=dyp_end
    )
    settings_old = get_settings()
    if settings_old:
        settings_old.dyp_season = dyp_season
        settings_old.dyp_year = dyp_year
        settings_old.dyp_start = dyp_start
        settings_old.dyp_end = dyp_end
        db.session.add(settings_old)
    else:
        db.session.add(settings)
    db.session.commit()


def persist_data2db(dyp_results, dyp_date, match_day):
    for player in dyp_results:
        player_obj = db.session.query(Player).filter_by(
            full_name=player['name']).one_or_none()
        if not player_obj:
            player_obj = Player(
                full_name=player['name'],
                club=player['club'],
                registration_nr=player['registration_nr']
            )
        else:
            # always update those: they might change over time
            player_obj.club = player['club']
            player_obj.registration_nr = player['registration_nr']

        scores = Score(
            dyp_date=dyp_date,
            match_day=match_day,
            score_today=player['points'],
            place_today=player['rank']
        )
        player_obj.scores.append(scores)
        db.session.add(player_obj)
        db.session.add(scores)
        db.session.commit()


def read_standings(match_day):
    stmt = select(
        Player, Score,
        func.sum(Score.score_today).label('points_total'),
        func.count(Score.score_today).label('attendances'),
        func.count(case(
            (
                Score.place_today == 1,
                literal_column("'equals1'")
            )
        )).label('first_place'),
        func.count(case(
            (
                Score.place_today == 2,
                literal_column("'equals2'")
            )
        )).label('second_place'),
        func.count(case(
            (
                Score.place_today == 3,
                literal_column("'equals3'")
            )
        )).label('third_place'),
        func.count(case(
            (
                Score.place_today == 4,
                literal_column("'equals4'")
            )
        )).label('fourth_place'),
        case(
            (
                Score.match_day < match_day,
                literal_column("'already_played'")
            )
        ).label('already_played'),
        func.rank().over(
            order_by=func.sum(Score.score_today).desc()
        ).label('rank')
    ).join(
        Player.scores
    ).where(
        Score.match_day <= match_day
    ).group_by(
        Player.full_name
    ).order_by(
        func.sum(Score.score_today).desc()
    )
    results = db.session.execute(stmt).all()

    ranks_before = select(
        Player,
        func.rank().over(
            order_by=func.sum(Score.score_today).desc()
        ).label('rank_last_day')
    ).join(
        Player.scores
    ).where(
        Score.match_day < match_day
    ).group_by(
        Player.full_name
    ).order_by(
        func.sum(Score.score_today).desc()
    )
    ranks_before = db.session.execute(ranks_before).all()
    return results, ranks_before


def get_dyp_dates():
    dyp_dates = db.session.query(Score.dyp_date).distinct().all()
    return dyp_dates


def revert_standings(match_day):
    try:
        # Filter and delete entries from the Score table
        scores_to_delete = db.session.query(Score).filter(
            Score.match_day >= match_day).all()
        for score in scores_to_delete:
            db.session.delete(score)

        # Filter and delete entries from the players_scores association table
        players_to_delete = db.session.query(players_scores).join(
            Score).filter(Score.match_day >= match_day).all()
        for player in players_to_delete:
            db.session.execute(players_scores.delete().where(
                (players_scores.c.player_id == player.player_id) &
                (players_scores.c.score_id == player.score_id)
            ))

        # Commit the changes
        db.session.commit()

    except Exception as e:
        # Rollback in case of an error
        db.session.rollback()
        print(f"Error: {e}")

    finally:
        # Close the session
        db.session.close()


def get_last_updated():
    stmt = select(
        func.max(Score.created_date)
    )
    last_updated = db.session.execute(stmt).scalar()
    return last_updated


def calc_jackpot(match_day):
    jackpot = db.session.query(func.count(Score.id)).where(Score.match_day <= match_day).scalar()
    return jackpot


def get_last_match_day():
    match_day = db.session.query(func.count(
        distinct(Score.dyp_date))).scalar()
    return match_day

from flask import current_app as app
import werkzeug
from kicker_dyp.config import Config

import typing
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

if typing.TYPE_CHECKING:
    import werkzeug.datastructures.file_storage


def retrieve_xml_files_from_zip(
        zip_file_path: werkzeug.datastructures.file_storage.FileStorage
    ) -> list[zipfile.ZipExtFile]:
    with zipfile.ZipFile(zip_file_path) as z:
        return [z.open(filename) for filename in z.infolist() if not filename.is_dir()]


def extract_data_from_xml(xml_file):
    data = []
    tree = ET.parse(xml_file)
    root = tree.getroot()
    for meldung, spieler in zip(root.findall('.//meldung'), root.findall('.//spieler')):
        name = spieler.get('name')
        rank = int(meldung.get('platz'))
        club = spieler.get('verein')
        registration_nr = spieler.get('spielerpass')

        data.append({'name': name, 'rank': rank, 'club': club,
                    'registration_nr': registration_nr})
    return data


def calculate_points_per_step(players_total, total_ranks):
    points_per_step = round(players_total / (total_ranks - 1), 2)
    return points_per_step


def generate_ranking(qualifying, players_elemination_ko_tree_1, players_elemination_ko_tree_2, points_per_step, max_rank_1, total_ranks):
    ranking = []
    points = 10.0
    # 2 elemination trees means lower placement for players in 2nd elemination tree: means + max_rank_1
    if players_elemination_ko_tree_2:
        players_elemination_ko_tree_2 = [{
            'name': player['name'],
            'rank': player['rank'] + max_rank_1,
            'club': player['club'],
            'registration_nr': player['registration_nr']
        } for player in players_elemination_ko_tree_2]
    # reverse list as we're calculating points starting at worst player position
    ko_tree = list(reversed(players_elemination_ko_tree_1 +
                            players_elemination_ko_tree_2))
    for idx, player in enumerate(ko_tree):
        # same rank = equal points
        if idx > 0:
            if ko_tree[idx - 1]['rank'] != player['rank']:
                points += points_per_step
        elif idx == 0:
            pass
        else:
            points += points_per_step
        player['points'] = round(points, 2)
        ranking.append(player)

    # participation points if player didn't participate final round
    max_rank = max([player['rank'] for player in ranking])
    # add to ranking
    only_qualifying = [{
        'name': q['name'],
        'rank': max_rank + 1,
        'club': q['club'],
        'registration_nr': q['registration_nr'],
        'points': 10.0
    } for q in qualifying if q['name']
        not in [p['name'] for p in ranking]]
    # remove dummy players
    dummy_players = ['Bruce Lee', 'Chuck Norris']
    only_qualifying = [ranking.append(q) for q in only_qualifying if q['name']
                       not in dummy_players]
    return ranking


def extract_date_from_filename(filename):
    date_str = filename[5:13]
    date_format = '%y_%m_%d'
    date_obj = datetime.strptime(date_str, date_format)
    return date_obj


def assign_tree_names(xml_files: list[zipfile.ZipExtFile]):
    filename_dict = dict()
    for zip_ext_file in xml_files:
        filename: str = Path(zip_ext_file.name).name
        filename_dict[filename] = zip_ext_file
    return filename_dict


def process_zip_file(zip_file):
    xml_files = retrieve_xml_files_from_zip(zip_file)
    filename_dict = assign_tree_names(xml_files)

    qualifying = extract_data_from_xml(filename_dict[Config.QUALIFYING_FILENAME])
    players_elemination_ko_tree_1 = extract_data_from_xml(filename_dict[Config.TREE_1_FILENAME])
    # n.b.: in case the second elemination tree doesn't exist return an empty list
    players_elemination_ko_tree_2 = filename_dict.get(filename_dict[Config.TREE_2_FILENAME], [])

    players_total = len(players_elemination_ko_tree_1 +
                        players_elemination_ko_tree_2)
    max_rank_1 = max([player['rank']
                     for player in players_elemination_ko_tree_1])
    max_rank_2 = max([player['rank']
                     for player in players_elemination_ko_tree_2], default=0)  # 0 if only one elimination tree
    total_ranks = max_rank_1 + max_rank_2
    points_per_step = calculate_points_per_step(players_total, total_ranks)

    ranking = generate_ranking(
        qualifying, players_elemination_ko_tree_1, players_elemination_ko_tree_2,
        points_per_step, max_rank_1, total_ranks
    )
    dyp_date_obj = extract_date_from_filename(zip_file.filename)
    return ranking, dyp_date_obj

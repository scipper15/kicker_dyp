from __future__ import annotations
from datetime import datetime
from pathlib import Path
import typing
import zipfile

import werkzeug
import xml.etree.ElementTree as ET

from kicker_dyp.config import Config

if typing.TYPE_CHECKING:
    import werkzeug.datastructures.file_storage
    from typing import IO


class KickertoolPlayerInfo(typing.TypedDict):
    name: str
    rank: int
    club: str
    registration_nr: str


class RankingPlayerInfo(KickertoolPlayerInfo):
    points: float


def retrieve_xml_files_from_zip(
        zip_file_path: werkzeug.datastructures.file_storage.FileStorage,
    ) -> list[IO[bytes]]:
    """Opens zip file, returns filestream objects

    Args:
        zip_file_path: file object

    Returns:
        list[IO[bytes]]: filestreams of the files inside the zip file
    """

    with zipfile.ZipFile(zip_file_path) as z:
        return [z.open(filename) for filename in z.infolist() if not filename.is_dir()]


def extract_data_from_xml(xml_file: zipfile.ZipExtFile) -> list[KickertoolPlayerInfo]:
    """Extracts dyp results from xml

    Args:
        xml_file: zip file object

    Returns:
        'name', rank, 'club', 'registration_nr' from xml provided by Kickertool
    """

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


def calculate_points_per_step(players_total: int, total_ranks: int) -> float:
    """Calculates points given for each better rank

    Args:
        players_total (int): total number of participating players
        total_ranks (int): total number of ranks

    Returns:
        float: points given for each better rank
    """

    points_per_step = round(players_total / (total_ranks - 1), 2)
    return points_per_step


def generate_ranking(
        qualifying: list[KickertoolPlayerInfo],
        players_elemination_ko_tree_1: list[KickertoolPlayerInfo],
        players_elimination_ko_tree_2: list[KickertoolPlayerInfo],
        points_per_step: float,
        max_rank_1: int
    ) -> list[RankingPlayerInfo]:
    """Produces a ranking of all players who participated classification round only, amateur round or professional round

    Args:
        qualifying: 'name', 'rank', 'club', 'registration_nr' of players participating classification round
        players_elemination_ko_tree_1: 'name', 'rank', 'club', 'registration_nr' of players participating professional round
        players_elimination_ko_tree_2: 'name', 'rank', 'club', 'registration_nr' of players participating amateur round
        points_per_step: points per better rank
        max_rank_1: total number of ranks

    Returns:
        unsorted list of 'name', rank, 'club', 'registration_nr', 'points'
    """

    ranking = []
    points = 10.0
    # 2 elimination trees means lower placement for players in 2nd elemination tree: means + max_rank_1
    if players_elimination_ko_tree_2:
        players_elimination_ko_tree_2 = [{
            'name': player['name'],
            'rank': player['rank'] + max_rank_1,
            'club': player['club'],
            'registration_nr': player['registration_nr']
        } for player in players_elimination_ko_tree_2]
    # reverse list as we're calculating points starting at worst player position
    ko_tree = list(reversed(players_elemination_ko_tree_1 +
                            players_elimination_ko_tree_2))
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


def extract_date_from_filename(filename: str):
    """Transforms filename into a date
    
    Filename format should be "MDYP_{yy}_{mm}_{dd}_{match_day}_export.zip" to work.

    Args:
        filename: filename

    Returns:
        date object extracted from filename
    """

    date_str = filename[5:13]
    date_format = '%y_%m_%d'
    date_obj = datetime.strptime(date_str, date_format)
    return date_obj


def assign_tree_names(xml_files: list[zipfile.ZipExtFile]) -> dict[str, zipfile.ZipExtFile]:
    """Generates a dictionary of filenames from the list of zip filestream objects

    Args:
        xml_files: list of zip filestream objects

    Returns:
        dictionary of {filename identifier: filestream object}
    """

    filename_dict = dict()
    for zip_ext_file in xml_files:
        filename: str = Path(zip_ext_file.name).name
        filename_dict[filename] = zip_ext_file
    return filename_dict


def process_zip_file(zip_file):
    """Generates a ranking of all participating players

    1. Gets list of filestreams from zip archive
    2. Assigns an identifier for each filestream object
    3. Extracts all xml trees: 1 qualifying and 2 elimination trees
    4. n.b.: In some cases there is only 1 elimination tree
    5. Counts total players, max_ranks, points_per_step
    6. Extracts the date from the filename
    7. Generates the ranking and returns it together with the date

    Args:
        zip_file (_type_): _description_

    Returns:
        _type_: _description_
    """
    xml_files = retrieve_xml_files_from_zip(zip_file)
    filestream_dict = assign_tree_names(xml_files)

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import typing
import zipfile
import xml.etree.ElementTree as ET

import werkzeug


if typing.TYPE_CHECKING:
    from werkzeug.datastructures.file_storage import FileStorage


class KickertoolPlayerInfo(typing.TypedDict):
    name: str
    rank: int
    club: str
    registration_nr: str


class RankingPlayerInfo(KickertoolPlayerInfo):
    points: float


def read_zip_members(
    zip_file: FileStorage,
) -> dict[str, bytes]:
    """
    Liest alle Dateien aus dem ZIP und liefert ein Dict:
    {basename -> file_bytes}
    """
    zip_file.stream.seek(0)

    with zipfile.ZipFile(zip_file.stream) as archive:
        files: dict[str, bytes] = {}

        for info in archive.infolist():
            if info.is_dir():
                continue

            basename = Path(info.filename).name
            files[basename] = archive.read(info.filename)

    return files


def get_xml_files(
    files: dict[str, bytes],
) -> dict[str, bytes]:
    """Filtert XML-Dateien aus einem Dateidict."""
    return {
        filename: content
        for filename, content in files.items()
        if filename.lower().endswith(".xml")
    }


def detect_xml_role(
    filename: str,
    xml_content: bytes,
) -> str | None:
    """
    Erkennt die Rolle einer XML-Datei.

    Rückgabe:
        - 'qualifying'
        - 'pro'
        - 'amateur'
        - None
    """
    filename_lower = filename.lower()

    filename_aliases = {
        "qualifying-group-1.xml": "qualifying",
        "vorrunde.xml": "qualifying",
        "elimination-ko-baum 1.xml": "pro",
        "ko_runde_profi.xml": "pro",
        "elimination-ko-baum 2.xml": "amateur",
        "ko_runde_amateur.xml": "amateur",
    }

    if filename_lower in filename_aliases:
        return filename_aliases[filename_lower]

    root = ET.fromstring(xml_content)

    disziplin = root.find(".//disziplin")
    if disziplin is None:
        return None

    disziplin_name = (disziplin.get("name") or "").strip().lower()

    if "vorrunde" in disziplin_name or "qualifying" in disziplin_name:
        return "qualifying"

    if "profi" in disziplin_name or "pro" in disziplin_name:
        return "pro"

    if "amateur" in disziplin_name:
        return "amateur"

    return None


def assign_xml_files(
    xml_files: dict[str, bytes],
) -> dict[str, bytes]:
    """
    Ordnet XML-Dateien ihren Rollen zu.
    qualifying und pro sind Pflicht, amateur ist optional.
    """
    assigned: dict[str, bytes] = {}

    for filename, xml_content in xml_files.items():
        role = detect_xml_role(filename, xml_content)
        if role is None:
            continue
        assigned[role] = xml_content

    missing = {"qualifying", "pro"} - set(assigned.keys())
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(
            f"ZIP konnte nicht verarbeitet werden. Fehlende XML-Rolle(n): {missing_str}"
        )

    return assigned


def parse_players_from_xml(
    xml_content: bytes,
) -> list[KickertoolPlayerInfo]:
    """
    Extrahiert Spieler aus einer XML-Datei.

    Wichtig:
    - In der Vorrunde enthält eine <meldung> typischerweise genau 1 <spieler>.
    - In KO-Runden enthält eine <meldung> typischerweise 2 <spieler>.

    Deshalb wird pro Meldung über alle enthaltenen Spieler iteriert.
    """
    root = ET.fromstring(xml_content)
    data: list[KickertoolPlayerInfo] = []

    for meldung in root.findall(".//meldung"):
        rank_raw = meldung.get("platz")
        if rank_raw is None:
            continue

        try:
            rank = int(rank_raw)
        except ValueError:
            continue

        for spieler in meldung.findall("./spieler"):
            name = (spieler.get("name") or "").strip()
            if not name:
                continue

            club = (spieler.get("verein") or "").strip()
            registration_nr = (spieler.get("spielerpass") or "").strip()

            data.append(
                {
                    "name": name,
                    "rank": rank,
                    "club": club,
                    "registration_nr": registration_nr,
                }
            )

    return data


def calculate_points_per_step(
    players_total: int,
    total_ranks: int,
) -> float:
    """
    Berechnet die Punktedifferenz pro besserem Rang.
    """
    if total_ranks <= 1:
        return 0.0

    return round(players_total / (total_ranks - 1), 2)


def shift_ranks(
    players: list[KickertoolPlayerInfo],
    rank_offset: int,
) -> list[KickertoolPlayerInfo]:
    """Verschiebt Ränge um einen Offset."""
    return [
        {
            "name": player["name"],
            "rank": player["rank"] + rank_offset,
            "club": player["club"],
            "registration_nr": player["registration_nr"],
        }
        for player in players
    ]


def generate_ranking(
    qualifying: list[KickertoolPlayerInfo],
    pro_players: list[KickertoolPlayerInfo],
    amateur_players: list[KickertoolPlayerInfo],
    points_per_step: float,
    max_rank_pro: int,
) -> list[RankingPlayerInfo]:
    """
    Erzeugt das Endranking.

    Annahme wie im bisherigen Code:
    - Profi-Baum vor Amateur-Baum
    - Spieler, die nur in der Vorrunde waren, erhalten Teilnahmepunkte
    """
    ranking: list[RankingPlayerInfo] = []
    points = 10.0

    adjusted_amateur_players = (
        shift_ranks(amateur_players, max_rank_pro)
        if amateur_players
        else []
    )

    ko_players = list(reversed(pro_players + adjusted_amateur_players))

    for index, player in enumerate(ko_players):
        if index > 0 and ko_players[index - 1]["rank"] != player["rank"]:
            points += points_per_step

        ranking.append(
            {
                "name": player["name"],
                "rank": player["rank"],
                "club": player["club"],
                "registration_nr": player["registration_nr"],
                "points": round(points, 2),
            }
        )

    max_rank = max((player["rank"] for player in ranking), default=0)
    ranking_names = {player["name"] for player in ranking}
    dummy_players = {"Bruce Lee", "Chuck Norris"}

    for player in qualifying:
        if player["name"] in ranking_names:
            continue

        if player["name"] in dummy_players:
            continue

        ranking.append(
            {
                "name": player["name"],
                "rank": max_rank + 1,
                "club": player["club"],
                "registration_nr": player["registration_nr"],
                "points": 10.0,
            }
        )

    return ranking


def extract_date_from_filename(
    filename: str,
) -> datetime:
    """
    Unterstützt altes und neues Dateinamensschema.

    Alt:
        MDYP_26_03_26_12_export.zip

    Neu:
        2026-3-26 MDYP_12_export.zip
    """
    basename = Path(filename).name

    old_match = re.search(r"MDYP_(\d{2}_\d{2}_\d{2})_", basename)
    if old_match:
        return datetime.strptime(old_match.group(1), "%y_%m_%d")

    new_match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", basename)
    if new_match:
        year, month, day = map(int, new_match.groups())
        return datetime(year=year, month=month, day=day)

    raise ValueError(f"Unbekanntes ZIP-Dateinamenformat: {basename}")


def process_zip_file(
    zip_file: FileStorage,
) -> tuple[list[RankingPlayerInfo], datetime]:
    """
    Verarbeitet das hochgeladene ZIP und erzeugt:
        (ranking, dyp_date)
    """
    files = read_zip_members(zip_file)
    xml_files = get_xml_files(files)

    if not xml_files:
        raise ValueError("ZIP enthält keine XML-Dateien.")

    assigned = assign_xml_files(xml_files)

    qualifying = parse_players_from_xml(assigned["qualifying"])
    pro_players = parse_players_from_xml(assigned["pro"])
    amateur_players = (
        parse_players_from_xml(assigned["amateur"])
        if "amateur" in assigned
        else []
    )

    players_total = len(pro_players) + len(amateur_players)

    max_rank_pro = max((player["rank"] for player in pro_players), default=0)
    max_rank_amateur = max((player["rank"] for player in amateur_players), default=0)

    total_ranks = max_rank_pro + max_rank_amateur
    points_per_step = calculate_points_per_step(players_total, total_ranks)

    ranking = generate_ranking(
        qualifying=qualifying,
        pro_players=pro_players,
        amateur_players=amateur_players,
        points_per_step=points_per_step,
        max_rank_pro=max_rank_pro,
    )

    dyp_date = extract_date_from_filename(zip_file.filename or "")

    return ranking, dyp_date

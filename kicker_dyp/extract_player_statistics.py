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

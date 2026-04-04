from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import typing
import zipfile
import xml.etree.ElementTree as ET

from werkzeug.datastructures import FileStorage


class KickertoolPlayerInfo(typing.TypedDict):
    name: str
    rank: int
    club: str
    registration_nr: str


class RankingPlayerInfo(KickertoolPlayerInfo):
    points: float


XML_ROLE_QUALIFYING = "qualifying"
XML_ROLE_PRO = "pro"
XML_ROLE_AMATEUR = "amateur"

DUMMY_PLAYERS = {"Bruce Lee", "Chuck Norris"}

FILENAME_ROLE_MAP: dict[str, str] = {
    # Altes Format
    "qualifying-group-1.xml": XML_ROLE_QUALIFYING,
    "elimination-ko-baum 1.xml": XML_ROLE_PRO,
    "elimination-ko-baum 2.xml": XML_ROLE_AMATEUR,
    # Neues Format
    "vorrunde.xml": XML_ROLE_QUALIFYING,
    "ko_runde_profi.xml": XML_ROLE_PRO,
    "ko_runde_amateur.xml": XML_ROLE_AMATEUR,
}


def read_zip_members(zip_file: FileStorage) -> dict[str, bytes]:
    """
    Read all files from the uploaded ZIP archive.

    Returns:
        Mapping of basename -> file content as bytes.
    """
    zip_file.stream.seek(0)

    with zipfile.ZipFile(zip_file.stream) as archive:
        result: dict[str, bytes] = {}

        for info in archive.infolist():
            if info.is_dir():
                continue

            basename = Path(info.filename).name
            result[basename] = archive.read(info.filename)

    return result


def get_xml_files(files: dict[str, bytes]) -> dict[str, bytes]:
    """
    Filter XML files from a file mapping.
    """
    return {
        filename: content
        for filename, content in files.items()
        if filename.lower().endswith(".xml")
    }


def detect_xml_role(filename: str, xml_content: bytes) -> str | None:
    """
    Detect the semantic role of an XML file.

    Supported roles:
        - qualifying
        - pro
        - amateur

    Detection strategy:
        1. Known filename aliases for old/new export formats
        2. Fallback: inspect XML metadata
    """
    normalized_name = filename.strip().lower()

    if normalized_name in FILENAME_ROLE_MAP:
        return FILENAME_ROLE_MAP[normalized_name]

    root = ET.fromstring(xml_content)

    disziplin = root.find(".//disziplin")
    if disziplin is None:
        return None

    disziplin_name = (disziplin.get("name") or "").strip().lower()

    if "vorrunde" in disziplin_name or "qualifying" in disziplin_name:
        return XML_ROLE_QUALIFYING

    if "profi" in disziplin_name:
        return XML_ROLE_PRO

    if "amateur" in disziplin_name:
        return XML_ROLE_AMATEUR

    return None


def assign_xml_files(xml_files: dict[str, bytes]) -> dict[str, bytes]:
    """
    Assign XML files to their logical roles.

    Required:
        - qualifying
        - pro

    Optional:
        - amateur
    """
    assigned: dict[str, bytes] = {}

    for filename, xml_content in xml_files.items():
        role = detect_xml_role(filename, xml_content)
        if role is None:
            continue

        assigned[role] = xml_content

    missing_roles = {XML_ROLE_QUALIFYING, XML_ROLE_PRO} - set(assigned.keys())
    if missing_roles:
        missing = ", ".join(sorted(missing_roles))
        raise ValueError(
            f"ZIP konnte nicht verarbeitet werden. Fehlende XML-Rolle(n): {missing}"
        )

    return assigned


def parse_players_from_xml(xml_content: bytes) -> list[KickertoolPlayerInfo]:
    """
    Parse all players from a ranking XML.

    Important:
        A <meldung> may contain multiple <spieler> elements.
        This is required for current KO exports and still works for the old format.
    """
    root = ET.fromstring(xml_content)
    players: list[KickertoolPlayerInfo] = []

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

            players.append(
                {
                    "name": name,
                    "rank": rank,
                    "club": club,
                    "registration_nr": registration_nr,
                }
            )

    return players


def shift_ranks(
    players: list[KickertoolPlayerInfo],
    offset: int,
) -> list[KickertoolPlayerInfo]:
    """
    Shift all player ranks by a fixed offset.
    """
    return [
        {
            "name": player["name"],
            "rank": player["rank"] + offset,
            "club": player["club"],
            "registration_nr": player["registration_nr"],
        }
        for player in players
    ]


def calculate_points_per_step(players_total: int, total_ranks: int) -> float:
    """
    Calculate the ranking point increment between rank groups.
    """
    if total_ranks <= 1:
        return 0.0

    return round(players_total / (total_ranks - 1), 2)


def generate_ranking(
    qualifying_players: list[KickertoolPlayerInfo],
    pro_players: list[KickertoolPlayerInfo],
    amateur_players: list[KickertoolPlayerInfo],
    points_per_step: float,
    max_rank_pro: int,
) -> list[RankingPlayerInfo]:
    """
    Generate the final ranking.

    Behaviour is intentionally aligned with the existing application logic:
        - pro tree ranks before amateur tree ranks
        - players only present in qualifying get participation points
    """
    ranking: list[RankingPlayerInfo] = []

    adjusted_amateur_players = (
        shift_ranks(amateur_players, max_rank_pro)
        if amateur_players
        else []
    )

    ko_players = list(reversed(pro_players + adjusted_amateur_players))

    points = 10.0
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

    ranking_names = {player["name"] for player in ranking}
    max_rank = max((player["rank"] for player in ranking), default=0)

    for player in qualifying_players:
        if player["name"] in ranking_names:
            continue

        if player["name"] in DUMMY_PLAYERS:
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


def extract_date_from_filename(filename: str) -> datetime:
    """
    Extract tournament date from the ZIP filename.

    Supported old format:
        MDYP_26_03_26_12_export.zip

    Supported new format:
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
    Process an uploaded ZIP file and return:
        (ranking, tournament_date)
    """
    files = read_zip_members(zip_file)
    xml_files = get_xml_files(files)

    if not xml_files:
        raise ValueError("ZIP enthält keine XML-Dateien.")

    assigned_xml_files = assign_xml_files(xml_files)

    qualifying_players = parse_players_from_xml(
        assigned_xml_files[XML_ROLE_QUALIFYING]
    )
    pro_players = parse_players_from_xml(assigned_xml_files[XML_ROLE_PRO])

    amateur_players: list[KickertoolPlayerInfo] = []
    if XML_ROLE_AMATEUR in assigned_xml_files:
        amateur_players = parse_players_from_xml(
            assigned_xml_files[XML_ROLE_AMATEUR]
        )

    players_total = len(pro_players) + len(amateur_players)
    max_rank_pro = max((player["rank"] for player in pro_players), default=0)
    max_rank_amateur = max(
        (player["rank"] for player in amateur_players),
        default=0,
    )

    total_ranks = max_rank_pro + max_rank_amateur
    points_per_step = calculate_points_per_step(players_total, total_ranks)

    ranking = generate_ranking(
        qualifying_players=qualifying_players,
        pro_players=pro_players,
        amateur_players=amateur_players,
        points_per_step=points_per_step,
        max_rank_pro=max_rank_pro,
    )

    tournament_date = extract_date_from_filename(zip_file.filename or "")

    return ranking, tournament_date

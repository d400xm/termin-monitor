#!/usr/bin/env python3
"""Monitor najblizszego wolnego terminu na ZnanyLekarz + powiadomienia ntfy.sh.

Uruchamiany cyklicznie (GitHub Actions co 5 minut). Stan trzyma w state.json
obok skryptu. Wymagana zmienna srodowiskowa: NTFY_TOPIC (nazwa tematu ntfy).
Opcjonalne: DOCTOR_URL (inny lekarz), NTFY_SERVER (wlasny serwer ntfy).
"""
import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DOCTOR_URL = os.environ.get(
    "DOCTOR_URL",
    "https://www.znanylekarz.pl/martyna-sacharewicz/fizjoterapeuta/bialystok",
)
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
STATE_FILE = Path(__file__).parent / "state.json"
# po ilu kolejnych nieudanych pobraniach wyslac ostrzezenie (12 x 5 min = ~1 h)
FAIL_ALERT_AFTER = 12

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}


def warsaw_tz():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Europe/Warsaw")
    except Exception:
        # brak bazy stref czasowych (np. goly Python na Windows) - przyblizenie
        return timezone(timedelta(hours=2))


def fetch_page():
    req = urllib.request.Request(DOCTOR_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_earliest(page):
    """Najwczesniejszy termin jako datetime w strefie PL albo None (brak terminow).

    Strona osadza w HTML JSON z polem earliestBookableDate (czas w UTC)
    osobno dla kazdej uslugi - bierzemy najwczesniejszy ze wszystkich.
    """
    text = html.unescape(page)
    dates = re.findall(r'"earliestBookableDate":\{"date":"([0-9 :.\-]+)"', text)
    if not dates:
        return None
    raw = min(dates).split(".")[0]
    dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.astimezone(warsaw_tz())


def notify(title, message, priority="default", tags=""):
    if not NTFY_TOPIC:
        print(f"[brak NTFY_TOPIC - powiadomienie tylko w logu] {title}: {message}")
        return
    req = urllib.request.Request(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            # naglowki HTTP nie znosza polskich znakow, dlatego tytul bez ogonkow
            "Title": title,
            "Priority": priority,
            "Tags": tags,
            "Click": DOCTOR_URL,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"ntfy: HTTP {resp.status}")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return None


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def fmt(iso):
    if not iso:
        return "brak wolnych terminow"
    return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M")


def main():
    state = load_state()
    first_run = state is None
    state = state or {"earliest": None, "failures": 0}

    try:
        current_dt = parse_earliest(fetch_page())
    except Exception as exc:
        failures = state.get("failures", 0) + 1
        print(f"Blad pobierania (proba {failures}): {exc}", file=sys.stderr)
        if failures == FAIL_ALERT_AFTER:
            notify(
                "Monitoring terminow: problem",
                f"Od ~godziny nie udaje sie pobrac strony ZnanyLekarz "
                f"(ostatni blad: {exc}). Sprawdz zakladke Actions na GitHubie.",
                priority="high",
                tags="warning",
            )
        # ograniczamy licznik, zeby plik stanu przestal sie zmieniac
        state["failures"] = min(failures, FAIL_ALERT_AFTER + 1)
        save_state(state)
        return

    previous = state.get("earliest")
    previous_dt = datetime.fromisoformat(previous) if previous else None
    current = current_dt.isoformat() if current_dt else None
    state["earliest"] = current
    state["failures"] = 0

    print(f"Najblizszy termin: {fmt(current)} (poprzednio: {fmt(previous)})")

    if first_run:
        notify(
            "Monitoring terminow uruchomiony",
            f"Pilnuje terminow: Martyna Sacharewicz (fizjoterapeuta, Bialystok).\n"
            f"Aktualnie najblizszy termin: {fmt(current)}.\n"
            f"Dostaniesz powiadomienie, gdy pojawi sie wczesniejszy.",
            tags="white_check_mark",
        )
    elif current_dt and (previous_dt is None or current_dt < previous_dt):
        notify(
            "Wczesniejszy termin wizyty!",
            f"Pojawil sie wczesniejszy termin: {fmt(current)}\n"
            f"(poprzednio najblizszy: {fmt(previous)}).\n"
            f"Kliknij powiadomienie, zeby otworzyc strone rezerwacji.",
            priority="urgent",
            tags="rotating_light,calendar",
        )

    save_state(state)


if __name__ == "__main__":
    main()

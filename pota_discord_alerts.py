import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests

POTA_SPOTS_URL = "https://api.pota.app/spot/activator"
STATE_FILE = Path("seen_spots.json")
CONFIG_FILE = Path("config.json")
LATEST_SPOT_FILE = Path("latest_pota_spot.txt")


def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError("Missing config.json")
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_seen() -> Set[str]:
    if not STATE_FILE.exists():
        return set()
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen: Set[str]) -> None:
    trimmed = list(seen)[-1000:]
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(trimmed, f, indent=2)


def normalize_list(values: List[str]) -> Set[str]:
    return {str(v).strip().upper() for v in values if str(v).strip()}


def parse_spot_time(spot: Dict[str, Any]) -> Optional[datetime]:
    for key in ("spotTime", "time", "date", "created", "createdAt"):
        value = spot.get(key)
        if not value:
            continue
        try:
            text = str(value).replace("Z", "+00:00")
            return datetime.fromisoformat(text).astimezone(timezone.utc)
        except Exception:
            continue
    return None


def spot_matches(spot: Dict[str, Any], config: Dict[str, Any]) -> bool:
    watch_callsigns = normalize_list(config.get("watch_callsigns", []))
    watch_parks = normalize_list(config.get("watch_parks", []))
    watch_modes = normalize_list(config.get("watch_modes", []))
    watch_bands = normalize_list(config.get("watch_bands", []))

    activator = str(spot.get("activator", "")).upper()
    park = str(spot.get("reference", "")).upper()
    mode = str(spot.get("mode", "")).upper()
    band = str(spot.get("band", "")).upper()

    mode_ok = not watch_modes or mode in watch_modes
    band_ok = not watch_bands or band in watch_bands

    target_ok = (
        (watch_callsigns and activator in watch_callsigns)
        or (watch_parks and park in watch_parks)
    )

    if not watch_callsigns and not watch_parks:
        target_ok = True

    return target_ok and mode_ok and band_ok


def make_unique_id(spot: Dict[str, Any]) -> str:
    pieces = [
        spot.get("activator", ""),
        spot.get("reference", ""),
        spot.get("frequency", ""),
        spot.get("mode", ""),
        spot.get("spotter", ""),
        spot.get("spotTime", spot.get("time", "")),
    ]
    return "|".join(str(p) for p in pieces)


def format_frequency(freq: str) -> str:
    try:
        value = float(freq)
        if value > 1000:
            return f"{value / 1000:.3f} MHz"
        return f"{value:.3f} MHz"
    except Exception:
        return str(freq)


def write_latest_spot_file(spot: Dict[str, Any]) -> None:
    activator = str(spot.get("activator", "Unknown")).upper()
    park = str(spot.get("reference", "Unknown"))
    freq = format_frequency(str(spot.get("frequency", "Unknown")))
    mode = str(spot.get("mode", "Unknown"))
    band = str(spot.get("band", ""))
    spotter = str(spot.get("spotter", "Unknown"))
    qrz_url = f"https://www.qrz.com/db/{activator}"
    pota_url = f"https://pota.app/#/activator/{activator}"

    text = f"🚨 POTA: {activator} spotted at {park} on {freq} {mode}"

    if band:
        text += f" ({band})"

    text += f" | Spotted by {spotter} | QRZ: {qrz_url} | POTA: {pota_url}"

    with LATEST_SPOT_FILE.open("w", encoding="utf-8") as f:
        f.write(text[:450])


def push_latest_spot_to_github() -> None:
    subprocess.run(["git", "add", "latest_pota_spot.txt"], check=False)
    subprocess.run(["git", "commit", "-m", "Update latest POTA spot"], check=False)
    subprocess.run(["git", "push"], check=False)


def build_embed_payload(spot: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    activator = str(spot.get("activator", "Unknown")).upper()
    park = str(spot.get("reference", "Unknown"))
    freq = str(spot.get("frequency", "Unknown"))
    mode = str(spot.get("mode", "Unknown"))
    band = str(spot.get("band", ""))
    spotter = str(spot.get("spotter", "Unknown"))
    comments = str(spot.get("comments", "") or "No comments")[:900]

    pota_url = f"https://pota.app/#/activator/{activator}"
    qrz_url = f"https://www.qrz.com/db/{activator}"

    fields = [
        {"name": "Park", "value": park, "inline": True},
        {"name": "Frequency", "value": format_frequency(freq), "inline": True},
        {"name": "Mode", "value": mode or "Unknown", "inline": True},
        {"name": "Band", "value": band or "Unknown", "inline": True},
        {"name": "Spotted By", "value": spotter, "inline": True},
        {"name": "QRZ Lookup", "value": f"[Open QRZ for {activator}]({qrz_url})", "inline": True},
        {"name": "Comments", "value": comments, "inline": False},
    ]

    content = ""
    allowed_mentions: Dict[str, Any] = {"parse": []}
    role_id = str(config.get("role_id", "")).strip()

    if config.get("ping_here", False):
        content = "@here"
        allowed_mentions = {"parse": ["everyone"]}

    if config.get("ping_role", False) and role_id:
        content = f"<@&{role_id}>"
        allowed_mentions = {"roles": [role_id], "parse": []}

    return {
        "username": "POTA Spot Alerts",
        "content": content,
        "embeds": [
            {
                "title": f"🚨 POTA Spot: {activator}",
                "url": pota_url,
                "description": f"**{activator}** was just spotted for **{park}**.",
                "color": 3066993,
                "fields": fields,
                "footer": {"text": "Parks on the Air Spot Alert"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "allowed_mentions": allowed_mentions,
    }


def send_to_discord(webhook_url: str, payload: Dict[str, Any]) -> None:
    response = requests.post(webhook_url, json=payload, timeout=20)
    if response.status_code >= 300:
        raise RuntimeError(f"Discord webhook failed: {response.status_code} {response.text}")


def main() -> int:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print("Missing DISCORD_WEBHOOK_URL secret/environment variable.")
        return 1

    config = load_config()
    seen = load_seen()

    response = requests.get(POTA_SPOTS_URL, timeout=20)
    response.raise_for_status()
    spots = response.json()

    cutoff_minutes = int(config.get("only_newer_than_minutes", 20))
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=cutoff_minutes)

    sent_count = 0

    for spot in spots:
        if not isinstance(spot, dict):
            continue

        spot_time = parse_spot_time(spot)
        if spot_time and spot_time < cutoff:
            continue

        if not spot_matches(spot, config):
            continue

        unique_id = make_unique_id(spot)
        if unique_id in seen:
            continue

        payload = build_embed_payload(spot, config)
        send_to_discord(webhook_url, payload)
        write_latest_spot_file(spot)
        push_latest_spot_to_github()

        seen.add(unique_id)
        sent_count += 1

    save_seen(seen)
    print(f"Sent {sent_count} Discord alert(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
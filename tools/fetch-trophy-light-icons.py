#!/usr/bin/env python3
"""Fetch missing Trophy* + light-source icons → 64×64 transparent PNG + icon-map."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
STORE_JS = ROOT / "js" / "commands-data.js"
ICON_DIR = ROOT / "assets" / "icons"
ICON_MAP = ROOT / "assets" / "icon-map.json"
WIKI = "https://valheim.weirdgloop.org"
UA = {"User-Agent": "HeimHeimTrophyIcons/1.0"}

LIGHT_OVERRIDES = {
    "Lantern": "Dvergr_Lantern.png",
    "Lantern_hooded": "Hooded_Lantern.png",
    "Lantern_DN": "Snow_Lantern.png",
    "Torch": "Torch.png",
    "TorchMist": "Mist_torch.png",
    "CandleWick": "Candle_Wick.png",
}


def words(prefab: str) -> list[str]:
    s = prefab.replace("_", " ")
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return [w for w in s.split() if w]


def trophy_candidates(prefab: str) -> list[str]:
    """Wiki uses Creature_Trophy.png (e.g. Boar_Trophy.png)."""
    rest = prefab[6:] if prefab.startswith("Trophy") else prefab
    parts = words(rest) if rest else words(prefab)
    human = "_".join(p.capitalize() if not p.isupper() else p for p in parts)
    # Keep underscore variants (Blob_Lava → Blob_Lava_Trophy)
    raw = rest
    out = [
        f"{raw}_Trophy.png",
        f"{human}_Trophy.png",
        f"{raw.replace('_', '')}_Trophy.png",
        f"Trophy_{raw}.png",
        f"{prefab}.png",
    ]
    # Common renames
    aliases = {
        "ForestTroll": "Troll",
        "FrostTroll": "Troll",
        "GreydwarfBrute": "Greydwarf_Brute",
        "GreydwarfShaman": "Greydwarf_Shaman",
        "SGolem": "Stone_Golem",
        "DragonQueen": "Moder",
        "TheElder": "The_Elder",
        "GoblinKing": "Yagluth",
        "GoblinBrute": "Fuling_Berserker",
        "GoblinShaman": "Fuling_Shaman",
        "Goblin": "Fuling",
        "Hatchling": "Drake",
        "SeekerQueen": "The_Queen",
        "SeekerBrute": "Seeker_Soldier",
        "BonemawSerpent": "Bonemaw",
        "Blob_Lava": "Lava_Blob",
        "Blob_Frost": "Frost_Blob",
        "Blob_Morkhalla": "Morkhalla_Blob",
        "BjornUndead": "Undead_Bjorn",
        "FallenValkyrie": "Fallen_Valkyrie",
        "CharredArcher": "Charred_Archer",
        "CharredMage": "Charred_Warlock",
        "CharredMelee": "Charred_Warrior",
        "Cultist_Hildir": "Cultist",
        "GoblinBruteBrosBrute": "Fuling_Berserker",
        "GoblinBruteBrosShaman": "Fuling_Shaman",
        "DeerWhite": "Deer",
        "JotunWarrior": "Dvergr",
        "Elaking": "Elk",
    }
    if raw in aliases:
        out.insert(0, f"{aliases[raw]}_Trophy.png")
    # Dedup
    seen, ordered = set(), []
    for g in out:
        if g and g not in seen:
            seen.add(g)
            ordered.append(g)
    return ordered


def candidates(prefab: str) -> list[str]:
    if prefab in LIGHT_OVERRIDES:
        return [LIGHT_OVERRIDES[prefab]]
    if prefab.startswith("Trophy"):
        return trophy_candidates(prefab)
    w = words(prefab)
    human = "_".join(x.capitalize() for x in w)
    return [f"{prefab}.png", f"{human}.png", LIGHT_OVERRIDES.get(prefab, "")]


def http_png(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
        return data if data[:8] == b"\x89PNG\r\n\x1a\n" else None
    except Exception:
        return None


def to_64_transparent(data: bytes) -> bytes:
    im = Image.open(BytesIO(data)).convert("RGBA")
    # Drop near-black / near-white letterbox if present (wiki icons usually clean)
    im = im.resize((64, 64), Image.Resampling.LANCZOS)
    buf = BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def fetch_one(prefab: str) -> tuple[str, bool]:
    dest = ICON_DIR / f"{prefab}.png"
    if dest.exists() and dest.stat().st_size > 80:
        return prefab, True
    for name in candidates(prefab):
        if not name:
            continue
        data = http_png(f"{WIKI}/images/{urllib.parse.quote(name)}")
        if not data:
            continue
        try:
            dest.write_bytes(to_64_transparent(data))
            return prefab, True
        except Exception:
            continue
    # opensearch fallback
    try:
        q = " ".join(words(prefab))
        if prefab.startswith("Trophy"):
            q = " ".join(words(prefab[6:])) + " trophy"
        api = (
            WIKI
            + "/api.php?"
            + urllib.parse.urlencode(
                {"action": "opensearch", "search": q, "limit": 3, "format": "json"}
            )
        )
        req = urllib.request.Request(api, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            titles = json.loads(r.read().decode())[1]
        for title in titles or []:
            guess = title.replace(" ", "_") + ".png"
            data = http_png(f"{WIKI}/images/{urllib.parse.quote(guess)}")
            if data:
                dest.write_bytes(to_64_transparent(data))
                return prefab, True
    except Exception:
        pass
    return prefab, False


def store_prefabs() -> list[str]:
    text = STORE_JS.read_text(encoding="utf-8")
    m = re.search(r"= (\{.*\});\s*$", text, re.S)
    if not m:
        return []
    store = json.loads(m.group(1))
    out, seen = [], set()
    for tab in store.values():
        if not isinstance(tab, list):
            continue
        for e in tab:
            p = e.get("prefab")
            if p and p not in seen:
                seen.add(p)
                out.append(p)
    return out


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    prefabs = store_prefabs()
    targets = [
        p
        for p in prefabs
        if p.startswith("Trophy")
        or any(x in p.lower() for x in ("lantern", "torch", "candle", "sconce", "firepit"))
        or p in LIGHT_OVERRIDES
    ]
    missing = [
        p
        for p in targets
        if not ((ICON_DIR / f"{p}.png").exists() and (ICON_DIR / f"{p}.png").stat().st_size > 80)
    ]
    print(f"targets={len(targets)} missing={len(missing)}", flush=True)
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = [pool.submit(fetch_one, p) for p in missing]
        for i, fut in enumerate(as_completed(futs), 1):
            _, success = fut.result()
            ok += int(success)
            fail += int(not success)
            if i % 20 == 0 or i == len(missing):
                print(f"  {i}/{len(missing)} ok={ok} fail={fail}", flush=True)

    mapping = {}
    if ICON_MAP.exists():
        try:
            mapping = json.loads(ICON_MAP.read_text())
        except Exception:
            mapping = {}
    for p in prefabs:
        if (ICON_DIR / f"{p}.png").exists():
            mapping[p] = f"assets/icons/{p}.png"
    ICON_MAP.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    still_t = [
        p
        for p in targets
        if p.startswith("Trophy") and p not in mapping
    ]
    still_l = [
        p
        for p in targets
        if not p.startswith("Trophy") and p not in mapping
    ]
    print(
        f"done map={len(mapping)} trophy_missing={len(still_t)} light_missing={len(still_l)}",
        flush=True,
    )
    if still_t:
        print("still trophies:", ", ".join(still_t[:30]), flush=True)
    if still_l:
        print("still lights:", ", ".join(still_l), flush=True)


if __name__ == "__main__":
    main()

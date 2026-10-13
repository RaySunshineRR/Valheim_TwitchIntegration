#!/usr/bin/env python3
"""Fetch missing Valheim wiki icons (weirdgloop) for every store prefab."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE_JS = ROOT / "js" / "commands-data.js"
ICON_DIR = ROOT / "assets" / "icons"
ICON_MAP = ROOT / "assets" / "icon-map.json"
WIKI = "https://valheim.weirdgloop.org"
API = f"{WIKI}/api.php"
UA = {
    "User-Agent": "ValheimTwitchStore/0.7 (+https://github.com/RaySunshineRR/Valheim_TwitchIntegration)"
}

# Prefab → known wiki file (when heuristics fail)
OVERRIDES = {
    "FineWood": "Finewood.png",
    "CoreWood": "Corewood.png",
    "RoundLog": "Corewood.png",
    "ElderBark": "Ancient_bark.png",
    "ArmorRagsChest": "Rag_Tunic.png",
    "ArmorRagsLegs": "Rag_Pants.png",
    "ArmorLeatherChest": "Leather_Tunic.png",
    "ArmorLeatherLegs": "Leather_Pants.png",
    "ArmorTrollLeatherChest": "Troll_Leather_Tunic.png",
    "ArmorTrollLeatherLegs": "Troll_Leather_Pants.png",
    "HelmetLeather": "Leather_Helmet.png",
    "HelmetTrollLeather": "Troll_Leather_Helmet.png",
    "HelmetBronze": "Bronze_Helmet.png",
    "HelmetIron": "Iron_Helmet.png",
    "HelmetPadded": "Padded_Helmet.png",
    "HelmetCarapace": "Carapace_Helmet.png",
    "HelmetRoot": "Root_Mask.png",
    "HelmetRootCrown": "Root_Mask.png",
    "ArmorRootChest": "Root_Harnesk.png",
    "ArmorRootLegs": "Root_Leggings.png",
    "ArmorWolfChest": "Wolf_Armor_Chest.png",
    "ArmorWolfLegs": "Wolf_Armor_Legs.png",
    "CapeWolf": "Wolf_Fur_Cape.png",
    "ArmorCarapaceChest": "Carapace_Breastplate.png",
    "ArmorCarapaceLegs": "Carapace_Greaves.png",
    "ArmorBronzeChest": "Bronze_Plate_Tunic.png",
    "ArmorBronzeLegs": "Bronze_Plate_Leggings.png",
    "ArmorIronChest": "Iron_Scale_Mail.png",
    "ArmorIronLegs": "Iron_Greaves.png",
    "Greydwarf_Shaman": "Greydwarf_Shaman.png",
    "Greydwarf_Elite": "Greydwarf_Brute.png",
    "BlobElite": "Oozer.png",
    "Hatchling": "Drake.png",
    "Draugr_Elite": "Draugr_Elite.png",
    "Draugr_Ranged": "Draugr.png",
    "Fenring_Cultist": "Cultist.png",
    "TrollFrost": "Troll.png",
    "CookedMeat": "Cooked_Boar_Meat.png",
    "QueensJam": "Queen's_Jam.png",
    "MeadHealthMinor": "Minor_Healing_Mead.png",
    "MeadStaminaMinor": "Minor_Stamina_Mead.png",
    "MeadTasty": "Tasty_Mead.png",
    "MeadPoisonResist": "Poison_Resistance_Mead.png",
    "MeadFrostResist": "Frost_Resistance_Mead.png",
    "SwordIron": "Iron_Sword.png",
    "SwordBronze": "Bronze_Sword.png",
    "SwordSilver": "Silver_Sword.png",
    "SwordBlackmetal": "Black_Metal_Sword.png",
    "ShieldWood": "Wood_Shield.png",
    "ShieldBanded": "Banded_Shield.png",
}


def split_words(prefab: str) -> list[str]:
    s = prefab.replace("_", " ")
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return [w for w in s.split() if w]


def human_name(prefab: str) -> str:
    words = split_words(prefab)
    if words and words[0] in {
        "Sword",
        "Axe",
        "Mace",
        "Spear",
        "Knife",
        "Bow",
        "Arrow",
        "Shield",
        "Pickaxe",
        "Sledge",
        "Atgeir",
        "Battleaxe",
        "Crossbow",
        "Staff",
        "Bolt",
        "THSword",
    }:
        return " ".join(words[1:] + words[:1])
    if words and words[0] == "Armor" and len(words) >= 2:
        return " ".join(words[1:])
    return " ".join(words)


def http_get(url: str, timeout: float = 15) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def api(params: dict) -> dict | None:
    url = API + "?" + urllib.parse.urlencode(params)
    data = http_get(url)
    if not data:
        return None
    try:
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None


def is_png(data: bytes | None) -> bool:
    return bool(data and data[:8] == b"\x89PNG\r\n\x1a\n")


def fetch_png_url(url: str) -> bytes | None:
    # strip cache buster ?xxxx
    url = url.split("?")[0]
    data = http_get(url)
    return data if is_png(data) else None


def candidate_filenames(prefab: str) -> list[str]:
    names: list[str] = []
    if prefab in OVERRIDES:
        names.append(OVERRIDES[prefab])
    words = split_words(prefab)
    human = human_name(prefab)
    variants = [
        prefab + ".png",
        human.replace(" ", "_") + ".png",
        "_".join(w.capitalize() for w in words) + ".png",
        "".join(w.capitalize() for w in words) + ".png",
        # FineWood → Finewood.png (wiki style)
        (words[0].capitalize() + "".join(w.lower() for w in words[1:]) + ".png")
        if words
        else "",
        # Fine_Wood / finewood
        "_".join(words) + ".png",
        "".join(words).lower() + ".png",
        "".join(w.capitalize() for w in words).replace("Wood", "wood") + ".png"
        if any(w == "Wood" for w in words)
        else "",
    ]
    # Strip variant suffixes for fallbacks
    base = re.sub(
        r"(_(?:piggy|White|Frozen|Summoned|noarcher|NoArcher|cave|Elite|Ranged|Cultist|Hildir|Swamps|Meadows|Mountains|Void|hatchling))?$",
        "",
        prefab,
        flags=re.I,
    )
    if base != prefab:
        variants.extend(candidate_filenames(base)[:6])
    # Uncooked / New suffixes
    bare = re.sub(r"(Uncooked|New|Blood|Lightning|Nature|FrostFire|BloodLightning)$", "", prefab)
    if bare and bare != prefab:
        variants.append(bare + ".png")
        variants.extend(candidate_filenames(bare)[:4])

    if words and words[0] == "Armor":
        rest = words[1:]
        variants.append("_".join(w.capitalize() for w in rest) + ".png")
        if rest and rest[-1] in {"Chest", "Body"}:
            mat = rest[:-1]
            for tail in (
                ["Plate", "Tunic"],
                ["Tunic"],
                ["Cuirass"],
                ["Scale", "Mail"],
                ["Breastplate"],
                ["Harnesk"],
                ["Armor", "Chest"],
            ):
                variants.append("_".join(w.capitalize() for w in mat + tail) + ".png")
        if rest and rest[-1] in {"Legs", "legs", "Leggings"}:
            mat = [w for w in rest[:-1]]
            for tail in (
                ["Greaves"],
                ["Pants"],
                ["Trousers"],
                ["Leggings"],
                ["Plate", "Leggings"],
                ["Armor", "Legs"],
            ):
                variants.append("_".join(w.capitalize() for w in mat + tail) + ".png")
    if words and words[0] == "Helmet":
        mat = words[1:]
        variants.append("_".join(w.capitalize() for w in mat + ["Helmet"]) + ".png")
        variants.append("_".join(w.capitalize() for w in mat + ["Mask"]) + ".png")

    out, seen = [], set()
    for n in names + variants:
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def opensearch(query: str, limit: int = 3) -> list[str]:
    data = api(
        {"action": "opensearch", "search": query, "limit": limit, "format": "json"}
    )
    if not data or not isinstance(data, list) or len(data) < 2:
        return []
    return list(data[1] or [])


def images_on_page(title: str) -> list[str]:
    data = api({"action": "parse", "page": title, "prop": "images", "format": "json"})
    if not data or "parse" not in data:
        return []
    return [i for i in (data["parse"].get("images") or []) if i.lower().endswith(".png")]


def allimages_prefix(prefix: str, limit: int = 10) -> list[str]:
    data = api(
        {
            "action": "query",
            "list": "allimages",
            "aiprefix": prefix,
            "ailimit": limit,
            "format": "json",
        }
    )
    if not data:
        return []
    return [i["name"] for i in data.get("query", {}).get("allimages", [])]


def file_url(filename: str) -> str | None:
    data = api(
        {
            "action": "query",
            "titles": f"File:{filename}",
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
        }
    )
    if not data:
        return None
    pages = data.get("query", {}).get("pages", {})
    for p in pages.values():
        if p.get("missing") is not None:
            return None
        info = (p.get("imageinfo") or [{}])[0]
        return info.get("url")
    return None


def resolve_icon(prefab: str) -> bytes | None:
    # 1) Direct candidate URLs
    for name in candidate_filenames(prefab):
        data = fetch_png_url(f"{WIKI}/images/{urllib.parse.quote(name)}")
        if data:
            return data
        # via imageinfo (handles weird names)
        url = file_url(name)
        if url:
            data = fetch_png_url(url)
            if data:
                return data

    # 2) Opensearch → page images / Title.png
    queries = [human_name(prefab), prefab.replace("_", " "), " ".join(split_words(prefab))]
    seen_q = set()
    for q in queries:
        if not q or q in seen_q:
            continue
        seen_q.add(q)
        for title in opensearch(q):
            # try Title.png
            guess = title.replace(" ", "_") + ".png"
            data = fetch_png_url(f"{WIKI}/images/{urllib.parse.quote(guess)}")
            if data:
                return data
            # parse page images — prefer ones matching tokens
            tokens = {w.lower() for w in split_words(prefab)}
            imgs = images_on_page(title)
            ranked = sorted(
                imgs,
                key=lambda n: (
                    0
                    if any(t in n.lower().replace("_", "") for t in tokens)
                    else 1,
                    len(n),
                ),
            )
            for img in ranked[:6]:
                if any(
                    skip in img.lower()
                    for skip in ("trophy", "stack", "appearance", "logo", "banner")
                ):
                    continue
                url = file_url(img) or f"{WIKI}/images/{urllib.parse.quote(img)}"
                data = fetch_png_url(url)
                if data:
                    return data

    # 3) allimages prefix from first word(s)
    words = split_words(prefab)
    prefixes = []
    if words:
        prefixes.append(words[0])
        if len(words) >= 2:
            prefixes.append(words[0] + words[1].lower())  # Finewood
            prefixes.append(words[0] + "_" + words[1])
    for prefix in prefixes:
        for name in allimages_prefix(prefix, 12):
            if name.lower().endswith(".png") and "stack" not in name.lower():
                url = file_url(name) or f"{WIKI}/images/{urllib.parse.quote(name)}"
                data = fetch_png_url(url)
                if data:
                    return data

    return None


def load_store_prefabs() -> list[str]:
    text = STORE_JS.read_text()
    m = re.search(r"window\.VALHEIM_TWITCH_STORE = (\{.*\});\s*$", text, re.S)
    if not m:
        raise SystemExit("commands-data.js missing store")
    store = json.loads(m.group(1))
    ordered, seen = [], set()
    # Priority tabs first
    for tab in ("quick", "mobs", "weapons", "armor", "food", "materials", "misc"):
        for e in store.get(tab) or []:
            p = e.get("prefab")
            if p and p not in seen:
                seen.add(p)
                ordered.append(p)
    return ordered


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    if ICON_MAP.exists():
        try:
            mapping = json.loads(ICON_MAP.read_text())
        except Exception:
            mapping = {}

    prefabs = load_store_prefabs()
    missing = [
        p
        for p in prefabs
        if not ((ICON_DIR / f"{p}.png").exists() and (ICON_DIR / f"{p}.png").stat().st_size > 100)
    ]
    print(f"Store prefabs: {len(prefabs)}  missing files: {len(missing)}  cached map: {len(mapping)}")

    fetched = 0
    failed: list[str] = []
    for i, prefab in enumerate(missing, 1):
        data = resolve_icon(prefab)
        if data:
            dest = ICON_DIR / f"{prefab}.png"
            dest.write_bytes(data)
            mapping[prefab] = f"assets/icons/{prefab}.png"
            fetched += 1
            if fetched % 20 == 0:
                print(f"  fetched {fetched}/{i} tried…")
                ICON_MAP.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
        else:
            failed.append(prefab)
            mapping.pop(prefab, None)
        time.sleep(0.03)

    # Refresh map for everything that exists on disk
    for p in prefabs:
        dest = ICON_DIR / f"{p}.png"
        if dest.exists() and dest.stat().st_size > 100:
            mapping[p] = f"assets/icons/{p}.png"

    ICON_MAP.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    print(f"Done. New this run: {fetched}. Map size: {len(mapping)}. Still missing: {len(failed)}")
    if failed:
        print("Still missing sample:", failed[:40])
        (ROOT / "assets" / "icons-missing.txt").write_text("\n".join(failed) + "\n")


if __name__ == "__main__":
    main()

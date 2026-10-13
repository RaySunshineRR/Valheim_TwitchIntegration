#!/usr/bin/env python3
"""Fast parallel icon fetch for remaining missing store prefabs."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE_JS = ROOT / "js" / "commands-data.js"
ICON_DIR = ROOT / "assets" / "icons"
ICON_MAP = ROOT / "assets" / "icon-map.json"
WIKI = "https://valheim.weirdgloop.org"
UA = {"User-Agent": "ValheimTwitchStore/0.7-fast"}

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
    "ArmorRootChest": "Root_Harnesk.png",
    "ArmorRootLegs": "Root_Leggings.png",
    "ArmorWolfChest": "Wolf_Armor_Chest.png",
    "ArmorWolfLegs": "Wolf_Armor_Legs.png",
    "CapeWolf": "Wolf_Fur_Cape.png",
    "ArmorCarapaceChest": "Carapace_Breastplate.png",
    "ArmorCarapaceLegs": "Carapace_Greaves.png",
    "Greydwarf_Elite": "Greydwarf_Brute.png",
    "Greydwarf_Shaman": "Greydwarf_Shaman.png",
    "BlobElite": "Oozer.png",
    "Hatchling": "Drake.png",
    "Fenring_Cultist": "Cultist.png",
    "CookedMeat": "Cooked_Boar_Meat.png",
    "QueensJam": "Queen's_Jam.png",
}


def words(prefab: str) -> list[str]:
    s = prefab.replace("_", " ")
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return [w for w in s.split() if w]


def candidates(prefab: str) -> list[str]:
    out = []
    if prefab in OVERRIDES:
        out.append(OVERRIDES[prefab])
    w = words(prefab)
    human = " ".join(w)
    guesses = [
        prefab + ".png",
        human.replace(" ", "_") + ".png",
        "_".join(x.capitalize() for x in w) + ".png",
        (w[0].capitalize() + "".join(x.lower() for x in w[1:]) + ".png") if w else "",
        "".join(w) + ".png",
        "".join(w).capitalize() + ".png" if w else "",
    ]
    # base without biome/variant suffix
    base = re.sub(
        r"_(?:piggy|White|Frozen|Summoned|noarcher|NoArcher|cave|Elite|Ranged|Cultist|Hildir|Swamps|Meadows|Mountains|Void|hatchling|DN)$",
        "",
        prefab,
        flags=re.I,
    )
    if base != prefab:
        guesses += [
            base + ".png",
            "_".join(x.capitalize() for x in words(base)) + ".png",
        ]
    bare = re.sub(r"(Uncooked|New|Blood|Lightning|Nature|FrostFire|BloodLightning)$", "", prefab)
    if bare != prefab:
        guesses.append(bare + ".png")
        guesses.append("_".join(x.capitalize() for x in words(bare)) + ".png")
    if w and w[0] == "Armor" and len(w) >= 2:
        rest = w[1:]
        if rest[-1].lower() in {"chest", "body", "legs", "leggings"}:
            mat = rest[:-1]
            if rest[-1].lower() in {"chest", "body"}:
                for tail in (["Tunic"], ["Plate", "Tunic"], ["Cuirass"], ["Breastplate"], ["Harnesk"]):
                    guesses.append("_".join(x.capitalize() for x in mat + tail) + ".png")
            else:
                for tail in (["Pants"], ["Greaves"], ["Leggings"], ["Trousers"]):
                    guesses.append("_".join(x.capitalize() for x in mat + tail) + ".png")
    if w and w[0] == "Helmet":
        guesses.append("_".join(x.capitalize() for x in w[1:] + ["Helmet"]) + ".png")
        guesses.append("_".join(x.capitalize() for x in w[1:] + ["Mask"]) + ".png")
    # weapon reorder
    if w and w[0] in {"Sword", "Axe", "Bow", "Shield", "Spear", "Knife", "Mace", "Arrow", "Atgeir", "Staff", "Crossbow", "Bolt", "THSword"}:
        guesses.append("_".join(x.capitalize() for x in (w[1:] + w[:1])) + ".png")

    seen, ordered = set(), []
    for g in out + guesses:
        if g and g not in seen:
            seen.add(g)
            ordered.append(g)
    return ordered[:12]  # hard cap — keep it fast


def get_png(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = r.read()
        return data if data[:8] == b"\x89PNG\r\n\x1a\n" else None
    except Exception:
        return None


def fetch_one(prefab: str) -> tuple[str, bool]:
    dest = ICON_DIR / f"{prefab}.png"
    if dest.exists() and dest.stat().st_size > 100:
        return prefab, True
    for name in candidates(prefab):
        data = get_png(f"{WIKI}/images/{urllib.parse.quote(name)}")
        if data:
            dest.write_bytes(data)
            return prefab, True
    # one opensearch fallback
    try:
        q = " ".join(words(prefab))
        api = (
            WIKI
            + "/api.php?"
            + urllib.parse.urlencode(
                {"action": "opensearch", "search": q, "limit": 1, "format": "json"}
            )
        )
        req = urllib.request.Request(api, headers=UA)
        with urllib.request.urlopen(req, timeout=8) as r:
            arr = json.loads(r.read().decode())
        titles = arr[1] if isinstance(arr, list) and len(arr) > 1 else []
        if titles:
            guess = titles[0].replace(" ", "_") + ".png"
            data = get_png(f"{WIKI}/images/{urllib.parse.quote(guess)}")
            if data:
                dest.write_bytes(data)
                return prefab, True
    except Exception:
        pass
    return prefab, False


def main() -> None:
    text = STORE_JS.read_text()
    store = json.loads(re.search(r"= (\{.*\});\s*$", text, re.S).group(1))
    prefabs, seen = [], set()
    for tab in ("quick", "mobs", "weapons", "armor", "food", "materials", "misc"):
        for e in store.get(tab) or []:
            p = e.get("prefab")
            if p and p not in seen:
                seen.add(p)
                prefabs.append(p)

    missing = [
        p
        for p in prefabs
        if not ((ICON_DIR / f"{p}.png").exists() and (ICON_DIR / f"{p}.png").stat().st_size > 100)
    ]
    print(f"missing={len(missing)} total={len(prefabs)}", flush=True)

    ok = fail = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = [pool.submit(fetch_one, p) for p in missing]
        for i, fut in enumerate(as_completed(futs), 1):
            _, success = fut.result()
            if success:
                ok += 1
            else:
                fail += 1
            if i % 40 == 0:
                print(f"  progress {i}/{len(missing)} ok={ok} fail={fail}", flush=True)

    mapping = {}
    for p in prefabs:
        if (ICON_DIR / f"{p}.png").exists():
            mapping[p] = f"assets/icons/{p}.png"
    ICON_MAP.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    still = [p for p in prefabs if p not in mapping]
    (ROOT / "assets" / "icons-missing.txt").write_text("\n".join(still) + "\n")
    print(f"done ok={ok} fail={fail} map={len(mapping)} still_missing={len(still)}", flush=True)


if __name__ == "__main__":
    main()

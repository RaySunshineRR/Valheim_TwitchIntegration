#!/usr/bin/env python3
"""Build Valheim Twitch command store from Heim-Heim prefab-catalog.json."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Path(
    "/media/rayray/BigChungus/000_AI_WORKSPACE/ZZ_Heim-Heim/docs/prefab-catalog.json"
)
OUT_JS = ROOT / "js" / "commands-data.js"
ICON_DIR = ROOT / "assets" / "icons"
ICON_MAP = ROOT / "assets" / "icon-map.json"
WIKI_IMG = "https://valheim.weirdgloop.org/images/"
WIKI_API = "https://valheim.weirdgloop.org/api.php"
UA = {"User-Agent": "ValheimTwitchStore/0.6 (+https://github.com/raysunshinerr/Valheim_TwitchIntegration)"}

BIOME_ORDER = [
    "Meadows",
    "Black Forest",
    "Swamp",
    "Mountain",
    "Plains",
    "Mistlands",
    "Ashlands",
    "Ocean",
    "Deep North",
    "Bosses",
]

# Prefab → wiki image overrides (when heuristics miss)
ICON_OVERRIDES = {
    "ArmorBronzeChest": "Bronze_Plate_Tunic.png",
    "ArmorBronzeLegs": "Bronze_Plate_Leggings.png",
    "ArmorBronzeHelmet": "Bronze_Helmet.png",
    "ArmorIronChest": "Iron_Scale_Mail.png",
    "ArmorIronLegs": "Iron_Greaves.png",
    "ArmorIronHelmet": "Iron_Helmet.png",
    "ArmorPaddedCuirass": "Padded_Cuirass.png",
    "ArmorPaddedGreaves": "Padded_Greaves.png",
    "ArmorPaddedHelmet": "Padded_Helmet.png",
    "CookedMeat": "Cooked_Boar_Meat.png",
    "CookedBoarMeat": "Cooked_Boar_Meat.png",
    "CookedDeerMeat": "Cooked_Deer_Meat.png",
    "CookedLoxMeat": "Cooked_Lox_Meat.png",
    "QueensJam": "Queen's_Jam.png",
    "SwordIron": "Iron_Sword.png",
    "SwordBronze": "Bronze_Sword.png",
    "SwordSilver": "Silver_Sword.png",
    "SwordBlackmetal": "Black_Metal_Sword.png",
    "ShieldWood": "Wood_Shield.png",
    "ShieldBanded": "Banded_Shield.png",
    "ArrowFire": "Fire_Arrow.png",
    "ArrowFrost": "Frost_Arrow.png",
    "ArrowPoison": "Poison_Arrow.png",
    "MeadHealthMinor": "Minor_Healing_Mead.png",
    "MeadStaminaMinor": "Minor_Stamina_Mead.png",
    "MeadTasty": "Tasty_Mead.png",
    "MeadPoisonResist": "Poison_Resistance_Mead.png",
    "MeadFrostResist": "Frost_Resistance_Mead.png",
}


def split_words(prefab: str) -> list[str]:
    s = prefab.replace("_", " ")
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return [w for w in s.split() if w]


def title_case(words: list[str]) -> str:
    return " ".join(w[:1].upper() + w[1:] for w in words)


def human_name(prefab: str) -> str:
    words = split_words(prefab)
    # Reorder common prefixes
    if len(words) >= 2 and words[0] in {
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
    }:
        return title_case(words[1:] + words[:1])
    if words and words[0] == "Armor" and len(words) >= 3:
        # ArmorBronzeChest → Bronze Chest
        return title_case(words[1:])
    return title_case(words)


def pretty_cmd_name(prefab: str, alias: str | None) -> str:
    return human_name(prefab)


def entry(prefab: str, alias: str | None, command: str | None = None, desc: str | None = None):
    e = {
        "name": pretty_cmd_name(prefab, alias),
        "cmd": command or f"#{(alias or prefab).lower()}",
        "prefab": prefab,
    }
    if desc:
        e["desc"] = desc
    return e


# ---- Item classification ----

WEAPON_PREFIX = {
    "Sword": "Swords",
    "THSword": "Swords",
    "Dyrnwyn": "Swords",
    "Axe": "Axes",
    "Battleaxe": "Axes",
    "Mace": "Maces & clubs",
    "Sledge": "Maces & clubs",
    "Club": "Maces & clubs",
    "Spear": "Spears",
    "Atgeir": "Spears",
    "Knife": "Knives",
    "Bow": "Bows",
    "Crossbow": "Bows",
    "Arrow": "Arrows & bolts",
    "Bolt": "Arrows & bolts",
    "Shield": "Shields",
    "Staff": "Magic",
    "Tankard": "Utility weapons",
    "Torch": "Utility weapons",
}

ARMOR_TIER_HINTS = [
    ("Rags", "T0 · Rags"),
    ("Leather", "T1 · Leather"),
    ("Troll", "T1 · Troll"),
    ("Bronze", "T2 · Bronze"),
    ("Root", "T2 · Root"),
    ("Iron", "T3 · Iron"),
    ("Fenris", "T3 · Fenris"),
    ("Wolf", "T4 · Wolf"),
    ("Padded", "T4 · Padded"),
    ("Carapace", "T5 · Carapace"),
    ("Eitr", "T5 · Eitr-weave"),
    ("Mage", "T5 · Mage"),
    ("Asksvin", "T6 · Asksvin"),
    ("Flametal", "T6 · Flametal"),
    ("Ashlands", "T6 · Ashlands"),
    ("Berserker", "Special · Berserker"),
    ("Emblem", "Special · Capes & misc"),
    ("Cape", "Special · Capes & misc"),
    ("Circlet", "Special · Capes & misc"),
]

FOOD_COOKED = re.compile(r"^(Cooked|Grilled|Smoke|SerpentMeatCooked|FishCooked)", re.I)
FOOD_MEAD = re.compile(r"(Mead|BarleyWine|Flask|Potion)", re.I)
FOOD_RAW = re.compile(r"(Meat|Egg|Fish|Tail|Blubber)$", re.I)
FOOD_CROP = {
    "Carrot",
    "Turnip",
    "Onion",
    "Barley",
    "Flax",
    "Mushroom",
    "Raspberry",
    "Blueberries",
    "Cloudberry",
    "Honey",
    "Dandelion",
    "Thistle",
    "QueensJam",
    "JotunPuffs",
    "Magecap",
    "Fiddleheadfern",
    "OnionSoup",
    "CarrotSoup",
    "DeerStew",
    "Sausages",
    "BloodPudding",
    "Bread",
    "LoxPie",
    "FishWraps",
    "Eyescream",
    "Salad",
    "MeatPlatter",
    "MisthareSupreme",
    "HoneyGlazedChicken",
    "MushroomOmelette",
    "PiquantPie",
    "RoastedCrustPie",
    "SpicyMarmalade",
    "CookedEgg",
    "BoarJerky",
    "WolfJerky",
    "BlackSoup",
    "SerpentStew",
}


def weapon_section(prefab: str) -> str:
    for prefix, section in WEAPON_PREFIX.items():
        if prefab.startswith(prefix):
            return section
    if "Bomb" in prefab or "Grenade" in prefab:
        return "Throwables"
    return "Other weapons"


def armor_section(prefab: str) -> str:
    for key, section in ARMOR_TIER_HINTS:
        if key.lower() in prefab.lower():
            return section
    return "Other armor"


def food_section(prefab: str) -> str:
    if FOOD_MEAD.search(prefab) or "Mead" in prefab:
        return "Meads & flasks"
    if FOOD_COOKED.search(prefab) or prefab.startswith("Cooked"):
        return "Cooked meals"
    if prefab in FOOD_CROP or any(
        prefab.startswith(x)
        for x in ("Mushroom", "Berry", "Honey", "Onion", "Carrot", "Turnip", "Barley")
    ):
        return "Crops & forage"
    if FOOD_RAW.search(prefab) or "Meat" in prefab:
        return "Raw ingredients"
    return "Prepared dishes"


def material_section(prefab: str) -> str:
    p = prefab.lower()
    if any(x in p for x in ("wood", "roundlog", "finewood", "corewood", "ygg")):
        return "Wood & plant"
    if any(x in p for x in ("stone", "flint", "obsidian", "crystal", "grausten", "blackmarble")):
        return "Stone & crystal"
    if any(
        x in p
        for x in (
            "bronze",
            "copper",
            "tin",
            "iron",
            "silver",
            "blackmetal",
            "flametal",
            "scrap",
            "ore",
            "bar",
        )
    ):
        return "Metals"
    if any(x in p for x in ("hide", "leather", "pelt", "wool", "hair", "scale", "chitin", "carapace")):
        return "Hides & scales"
    if any(x in p for x in ("trophy", "boss", "egg", "queen", "eitr")):
        return "Boss & rare drops"
    if any(x in p for x in ("coin", "amber", "ruby", "pearl", "gem", "silvernecklace")):
        return "Valuables"
    return "Crafting parts"


def should_skip_item(prefab: str) -> bool:
    """Drop cosmetics, world pickables, projectiles — not useful Twitch targets."""
    if prefab.startswith(("Beard", "Hair", "Player", "Pickable")):
        return True
    if "projectile" in prefab.lower():
        return True
    if "ragdoll" in prefab.lower() or prefab.endswith("Corpse"):
        return True
    if prefab.startswith("MoldArmor") or prefab.startswith("MoldHelmet"):
        return True
    return False


def misc_section(prefab: str) -> str:
    p = prefab.lower()
    if prefab.startswith("Mold") or "mold" in p:
        return "Crafting molds"
    if "treasure" in p or "chest" in p or "coffer" in p:
        return "Chests & treasure"
    if "firework" in p or "bell" in p:
        return "Fun & fireworks"
    if "trinket" in p or "wishbone" in p or "barber" in p:
        return "Accessories"
    if "saddle" in p or ("asksvin" in p and "egg" in p) or prefab.endswith("Egg"):
        return "Mounts & eggs"
    if any(x in p for x in ("torch", "lantern", "candle", "firepit", "campfire")):
        return "Light sources"
    if any(x in p for x in ("hammer", "hoe", "cultivator", "pickaxe", "fishing", "harpoon")):
        return "Tools"
    if "trophy" in p:
        return "Trophies"
    return "Utility & oddities"


def classify_item(it: dict) -> tuple[str, str]:
    """Return (tab, section)."""
    prefab = it["prefab"]
    cat = it.get("category") or "Misc"
    if cat == "Weapons":
        return "weapons", weapon_section(prefab)
    if cat == "Armor":
        return "armor", armor_section(prefab)
    if cat == "Food":
        return "food", food_section(prefab)
    if cat == "Materials":
        return "materials", material_section(prefab)
    if cat == "Valuables":
        return "materials", "Valuables"
    # Misc — rescue into better tabs
    if prefab.startswith(("THSword", "Dyrnwyn")):
        return "weapons", "Swords"
    if prefab.startswith(
        (
            "Sword",
            "Axe",
            "Bow",
            "Arrow",
            "Shield",
            "Spear",
            "Knife",
            "Mace",
            "Atgeir",
            "Staff",
            "Crossbow",
            "Bolt",
            "Battleaxe",
            "Sledge",
        )
    ):
        return "weapons", weapon_section(prefab)
    if prefab.startswith("SP_Armor") or prefab.startswith("Armor") or "Cape" in prefab:
        return "armor", armor_section(prefab)
    if (
        "Mead" in prefab
        or prefab in FOOD_CROP
        or prefab.startswith("Cooked")
        or prefab.startswith("Feast")
        or prefab.startswith("Spice")
        or prefab.startswith("Baked")
        or any(prefab.startswith(x) for x in ("Kale", "Oat", "Piquant", "Misthare"))
    ):
        if prefab.startswith("Feast") or prefab.startswith("Spice"):
            return "food", "Prepared dishes"
        return "food", food_section(prefab)
    if prefab.startswith("Trinket"):
        return "armor", "Special · Capes & misc"
    return "misc", misc_section(prefab)


# Prioritized "Quick" picks for streamers
QUICK_PREFABS = [
    ("Greyling", "Starter mob — soft chaos"),
    ("Boar", "Meadows pest"),
    ("Troll", "Big smash"),
    ("Skeleton", "Raid filler"),
    ("Neck", "Shore pest"),
    ("Wood", "Building basics"),
    ("Stone", "Building basics"),
    ("FineWood", "Quality builds"),
    ("Iron", "Mid-game metal"),
    ("Bronze", "Early metal"),
    ("Coal", "Smelting fuel"),
    ("CookedMeat", "Quick food"),
    ("Honey", "Mead base"),
    ("MeadHealthMinor", "Heal up"),
    ("MeadStaminaMinor", "Stamina up"),
    ("ArrowFire", "Ranged spice"),
    ("SwordIron", "Solid blade"),
    ("ShieldWood", "Starter block"),
    ("ArmorBronzeChest", "Early plate"),
    ("Torch", "Light"),
]


def build_store(data: dict) -> dict:
    creatures = data.get("creatures") or []
    items = [
        i
        for i in (data.get("items") or [])
        if i.get("bareCommand") and not should_skip_item(i["prefab"])
    ]

    store: dict = {
        "meta": {
            "title": "Valheim Twitch Command Store",
            "subtitle": "Copy a #command · paste in Twitch chat · Heim-Heim",
            "prefix": "#",
            "theme": "blue",
        },
        "quick": [
            {
                "type": "help",
                "text": "Streamer favourites first. Full lists live in the other tabs. #visit also works in chat.",
            },
            {"type": "section", "title": "Chat basics"},
            {"name": "Visit", "cmd": "#visit", "desc": "Spawn your named Greyling"},
            {"name": "Spawn (legacy)", "cmd": "#spawn Greyling", "desc": "Explicit spawn form"},
            {"name": "Item (legacy)", "cmd": "#item Wood", "desc": "Explicit item form"},
        ],
        "mobs": [],
        "weapons": [],
        "armor": [],
        "food": [],
        "materials": [],
        "misc": [],
    }

    # Quick entries
    by_prefab_c = {c["prefab"]: c for c in creatures}
    by_prefab_i = {i["prefab"]: i for i in items}
    store["quick"].append({"type": "section", "title": "Handy mobs"})
    for prefab, desc in QUICK_PREFABS:
        if prefab in by_prefab_c:
            c = by_prefab_c[prefab]
            store["quick"].append(
                entry(prefab, c.get("alias"), c.get("command"), desc)
            )
    store["quick"].append({"type": "section", "title": "Handy items"})
    for prefab, desc in QUICK_PREFABS:
        if prefab in by_prefab_i:
            i = by_prefab_i[prefab]
            store["quick"].append(
                entry(prefab, i.get("alias"), i.get("command"), desc)
            )

    # Mobs by biome (subtabs driven by section titles matching BIOME_ORDER)
    store["mobs"].append(
        {
            "type": "help",
            "text": "Pick a biome sub-tab. Bosses are separate. Commands are bare #aliases (no args).",
        }
    )
    by_biome: dict[str, list] = defaultdict(list)
    for c in creatures:
        by_biome[c.get("category") or "Other"].append(c)
    for biome in BIOME_ORDER:
        if biome not in by_biome:
            continue
        store["mobs"].append({"type": "section", "title": biome})
        for c in sorted(by_biome[biome], key=lambda x: x["prefab"].lower()):
            store["mobs"].append(entry(c["prefab"], c.get("alias"), c.get("command")))
    for biome, lst in sorted(by_biome.items()):
        if biome in BIOME_ORDER:
            continue
        store["mobs"].append({"type": "section", "title": biome})
        for c in sorted(lst, key=lambda x: x["prefab"].lower()):
            store["mobs"].append(entry(c["prefab"], c.get("alias"), c.get("command")))

    # Items into tabs/sections
    buckets: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for it in items:
        tab, section = classify_item(it)
        buckets[tab][section].append(it)

    section_order = {
        "weapons": [
            "Swords",
            "Axes",
            "Maces & clubs",
            "Spears",
            "Knives",
            "Bows",
            "Arrows & bolts",
            "Shields",
            "Magic",
            "Throwables",
            "Utility weapons",
            "Other weapons",
        ],
        "armor": list(dict.fromkeys([s for _, s in ARMOR_TIER_HINTS] + ["Other armor"])),
        "food": [
            "Cooked meals",
            "Prepared dishes",
            "Meads & flasks",
            "Crops & forage",
            "Raw ingredients",
        ],
        "materials": [
            "Wood & plant",
            "Stone & crystal",
            "Metals",
            "Hides & scales",
            "Boss & rare drops",
            "Valuables",
            "Crafting parts",
        ],
        "misc": [
            "Tools",
            "Light sources",
            "Mounts & eggs",
            "Accessories",
            "Fun & fireworks",
            "Chests & treasure",
            "Crafting molds",
            "Trophies",
            "Utility & oddities",
        ],
    }

    for tab, order in section_order.items():
        help_text = {
            "weapons": "Ordered by weapon family — swords before arrows. Prefer mid-tier for fun without ending the run.",
            "armor": "Tiered by progression (T0 rags → T6 Ashlands). Capes & odd pieces at the end.",
            "food": "Cooked & prepared first (actual usefulness), then meads, crops, raw.",
            "materials": "Building & crafting staples up top; boss drops and valuables lower.",
            "misc": "Tools, lights, mounts, fireworks, chests — streamer-useful leftovers.",
        }[tab]
        store[tab].append({"type": "help", "text": help_text})
        seen = set()
        for section in order:
            lst = buckets[tab].get(section) or []
            if not lst:
                continue
            seen.add(section)
            store[tab].append({"type": "section", "title": section})
            for it in sorted(lst, key=lambda x: x["prefab"].lower()):
                store[tab].append(entry(it["prefab"], it.get("alias"), it.get("command")))
        for section, lst in sorted(buckets[tab].items()):
            if section in seen or not lst:
                continue
            store[tab].append({"type": "section", "title": section})
            for it in sorted(lst, key=lambda x: x["prefab"].lower()):
                store[tab].append(entry(it["prefab"], it.get("alias"), it.get("command")))

    return store


def candidate_icon_names(prefab: str) -> list[str]:
    if prefab in ICON_OVERRIDES:
        return [ICON_OVERRIDES[prefab]]
    words = split_words(prefab)
    human = human_name(prefab)
    names = []
    # Direct
    names.append(prefab + ".png")
    names.append(human.replace(" ", "_") + ".png")
    names.append("_".join(w.capitalize() for w in words) + ".png")
    # Reordered weapon style already in human
    if words and words[0] in WEAPON_PREFIX:
        names.append("_".join(w.capitalize() for w in (words[1:] + words[:1])) + ".png")
    # ArmorBronzeChest → Bronze_Plate_Tunic style guesses
    if words and words[0] == "Armor":
        rest = words[1:]
        names.append("_".join(w.capitalize() for w in rest) + ".png")
        if rest and rest[-1] in {"Chest", "Body"}:
            names.append("_".join(w.capitalize() for w in rest[:-1] + ["Plate", "Tunic"]) + ".png")
            names.append("_".join(w.capitalize() for w in rest[:-1] + ["Cuirass"]) + ".png")
            names.append("_".join(w.capitalize() for w in rest[:-1] + ["Scale", "Mail"]) + ".png")
        if rest and rest[-1] in {"Legs", "Leggings"}:
            names.append("_".join(w.capitalize() for w in rest[:-1] + ["Greaves"]) + ".png")
            names.append("_".join(w.capitalize() for w in rest[:-1] + ["Plate", "Leggings"]) + ".png")
    # Dedupe preserve order
    out, seen = [], set()
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def http_get(url: str, timeout: float = 12) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            return data
    except Exception:
        return None


def opensearch_title(query: str) -> str | None:
    url = (
        WIKI_API
        + "?"
        + urllib.parse.urlencode(
            {"action": "opensearch", "search": query, "limit": 1, "format": "json"}
        )
    )
    data = http_get(url)
    if not data:
        return None
    try:
        arr = json.loads(data.decode("utf-8"))
        titles = arr[1] if isinstance(arr, list) and len(arr) > 1 else []
        return titles[0] if titles else None
    except Exception:
        return None


def fetch_icons(prefabs: list[str], limit: int = 400) -> dict[str, str]:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    if ICON_MAP.exists():
        try:
            mapping = json.loads(ICON_MAP.read_text())
        except Exception:
            mapping = {}

    fetched = 0
    for prefab in prefabs:
        if fetched >= limit:
            break
        dest = ICON_DIR / f"{prefab}.png"
        if dest.exists() and dest.stat().st_size > 100:
            mapping[prefab] = f"assets/icons/{prefab}.png"
            continue

        data = None
        # 1) candidates
        for name in candidate_icon_names(prefab):
            data = http_get(WIKI_IMG + urllib.parse.quote(name))
            if data and data[:8] == b"\x89PNG\r\n\x1a\n":
                break
            data = None
        # 2) opensearch → Title.png
        if data is None:
            title = opensearch_title(human_name(prefab))
            if title:
                guess = title.replace(" ", "_") + ".png"
                data = http_get(WIKI_IMG + urllib.parse.quote(guess))
                if data and data[:8] != b"\x89PNG\r\n\x1a\n":
                    data = None

        if data and data[:8] == b"\x89PNG\r\n\x1a\n":
            dest.write_bytes(data)
            mapping[prefab] = f"assets/icons/{prefab}.png"
            fetched += 1
            if fetched % 25 == 0:
                print(f"  icons fetched {fetched}…")
            time.sleep(0.05)
        else:
            mapping.pop(prefab, None)

    ICON_MAP.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    print(f"Icon map: {len(mapping)} / tried up to {limit} new this run (+cached)")
    return mapping


def write_js(store: dict) -> None:
    OUT_JS.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(store, indent=2, ensure_ascii=False)
    OUT_JS.write_text(
        "/** Valheim Heim-Heim #command store — generated by tools/build-store.py */\n"
        f"window.VALHEIM_TWITCH_STORE = {payload};\n"
    )
    # counts
    for k, v in store.items():
        if k == "meta":
            continue
        n = sum(1 for e in v if e.get("cmd"))
        print(f"  {k}: {n} commands")


def main() -> None:
    data = json.loads(CATALOG.read_text())
    print("Building store from", CATALOG)
    store = build_store(data)
    write_js(store)

    # Icons: all creatures + prioritized items + first N of each tab
    prefabs: list[str] = []
    for c in data.get("creatures") or []:
        prefabs.append(c["prefab"])
    for prefab, _ in QUICK_PREFABS:
        prefabs.append(prefab)
    for it in data.get("items") or []:
        if it.get("bareCommand"):
            prefabs.append(it["prefab"])
    # unique preserve order
    seen = set()
    ordered = []
    for p in prefabs:
        if p not in seen:
            seen.add(p)
            ordered.append(p)

    print("Fetching wiki icons (weirdgloop 64×64)…")
    # Prefer fetching icons for entries that actually appear in the store
    store_prefabs = []
    for key, rows in store.items():
        if key == "meta":
            continue
        for e in rows:
            if e.get("prefab"):
                store_prefabs.append(e["prefab"])
    seen2, prioritized = set(), []
    for p in store_prefabs + ordered:
        if p not in seen2:
            seen2.add(p)
            prioritized.append(p)
    fetch_icons(prioritized, limit=600)


if __name__ == "__main__":
    main()

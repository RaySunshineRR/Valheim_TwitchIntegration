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
ECONOMY_CATALOG = Path(
    "/media/rayray/BigChungus/000_AI_WORKSPACE/ZZ_Heim-Heim/docs/heimheim-catalog.json"
)
OUT_JS = ROOT / "js" / "commands-data.js"
ICON_DIR = ROOT / "assets" / "icons"
ICON_MAP = ROOT / "assets" / "icon-map.json"
# prefab → coinCost from heimheim-catalog.json (filled in main)
COIN_COSTS: dict[str, int] = {}
# prefab → defaultAmount (materials → 10); stack display cost = coinCost × amount
DEFAULT_AMOUNTS: dict[str, int] = {}
# prefab → tier int from economy catalog (mead biome overrides)
ECONOMY_TIERS: dict[str, int] = {}
TIER_LABEL = {
    0: "T0 · Meadows",
    1: "T1 · Black Forest",
    2: "T2 · Swamp",
    3: "T3 · Mountain",
    4: "T4 · Plains",
    5: "T5 · Mistlands",
    6: "T6 · Ashlands",
}
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
    "MeadHealthMedium": "Medium_Healing_Mead.png",
    "MeadHealthMajor": "Major_Healing_Mead.png",
    "MeadHealthLingering": "Lingering_Healing_Mead.png",
    "MeadStaminaMinor": "Minor_Stamina_Mead.png",
    "MeadStaminaMedium": "Medium_Stamina_Mead.png",
    "MeadStaminaLingering": "Lingering_Stamina_Mead.png",
    "MeadTasty": "Tasty_Mead.png",
    "MeadPoisonResist": "Poison_Resistance_Mead.png",
    "MeadFrostResist": "Frost_Resistance_Mead.png",
    "MeadLightfoot": "Lightfoot_Mead.png",
    "MeadBzerker": "Berserkir_Mead.png",
    "MeadEitrMinor": "Minor_Eitr_Mead.png",
    "MeadEitrLingering": "Lingering_Eitr_Mead.png",
    "MeadBugRepellent": "Anti-Sting_Concoction.png",
    "MeadHasty": "Tonic_of_Ratatosk.png",
    "MeadStrength": "Mead_of_Troll_Endurance.png",
    "MeadSwimmer": "Draught_of_Vananidir.png",
    "MeadTamer": "Brew_of_Animal_Whispers.png",
    "MeadTrollPheromones": "Love_Potion.png",
    "BarleyWine": "Fire_Resistance_Barley_Wine.png",
    "BarleyWineBase": "Barley_Wine_Base_-_Fire_Resistance.png",
    "MeadBaseHealthMinor": "Mead_Base_-_Minor_Healing.png",
    "MeadBaseHealthMedium": "Mead_Base_-_Medium_Healing.png",
    "MeadBaseHealthMajor": "Mead_Base_-_Major_Healing.png",
    "MeadBaseHealthLingering": "Mead_Base_-_Lingering_Health.png",
    "MeadBaseStaminaMinor": "Mead_Base_-_Minor_Stamina.png",
    "MeadBaseStaminaMedium": "Mead_Base_-_Medium_Stamina.png",
    "MeadBaseStaminaLingering": "Mead_Base_-_Lingering_Stamina.png",
    "MeadBaseTasty": "Mead_Base_-_Tasty.png",
    "MeadBasePoisonResist": "Mead_Base_-_Poison_Resistance.png",
    "MeadBaseFrostResist": "Mead_Base_-_Frost_Resistance.png",
    "MeadBaseLightFoot": "Mead_Base_-_Lightfoot.png",
    "MeadBaseBzerker": "Mead_Base_-_Berserkir.png",
    "MeadBaseEitrMinor": "Mead_Base_-_Minor_Eitr.png",
    "MeadBaseEitrLingering": "Mead_Base_-_Lingering_Eitr.png",
    "MeadBaseBugRepellent": "Mead_Base_-_Anti-Sting.png",
    "MeadBaseHasty": "Mead_Base_-_Ratatosk.png",
    "MeadBaseStrength": "Mead_Base_-_Troll_Endurance.png",
    "MeadBaseSwimmer": "Mead_Base_-_Vananidir.png",
    "MeadBaseTamer": "Mead_Base_-_Animal_Whispers.png",
    # Biome feasts (wiki dining names — Material prefabs)
    "FeastMeadows_Material": "Whole_Roasted_Meadow_Boar.png",
    "FeastBlackforest_Material": "Black_Forest_Buffet_Platter.png",
    "FeastSwamps_Material": "Swamp_Dweller's_Delight.png",
    "FeastOceans_Material": "Sailor's_Bounty.png",
    "FeastMountains_Material": "Hearty_Mountain_Logger's_Stew.png",
    "FeastPlains_Material": "Plains_Pie_Picnic.png",
    "FeastMistlands_Material": "Mushrooms_Galore_á_la_Mistlands.png",
    "FeastAshlands_Material": "Ashlands_Gourmet_Bowl.png",
    "FeastDeepNorth_Material": "Northern_Morning_Fare.png",
}


def split_words(prefab: str) -> list[str]:
    s = prefab.replace("_", " ")
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return [w for w in s.split() if w]


def title_case(words: list[str]) -> str:
    return " ".join(w[:1].upper() + w[1:] for w in words)


# SoftRef ids → streamer-friendly labels (wiki names)
DISPLAY_NAME = {
    "RawMeat": "Boar Meat",
    "CookedMeat": "Cooked Boar Meat",
    "NeckTail": "Neck Tail",
    "NeckTailGrilled": "Grilled Neck Tail",
    "gd_king": "The Elder",
    "GoblinKing": "Yagluth",
    "Dragon": "Moder",
    "SeekerQueen": "The Queen",
    "FeastMeadows_Material": "Whole Roasted Meadow Boar",
    "FeastBlackforest_Material": "Black Forest Buffet Platter",
    "FeastSwamps_Material": "Swamp Dweller's Delight",
    "FeastOceans_Material": "Sailor's Bounty",
    "FeastMountains_Material": "Hearty Mountain Logger's Stew",
    "FeastPlains_Material": "Plains Pie Picnic",
    "FeastMistlands_Material": "Mushrooms Galore á la Mistlands",
    "FeastAshlands_Material": "Ashlands Gourmet Bowl",
    "FeastDeepNorth_Material": "Northern Morning Fare",
}


def human_name(prefab: str) -> str:
    if prefab in DISPLAY_NAME:
        return DISPLAY_NAME[prefab]
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
    amt = max(1, int(DEFAULT_AMOUNTS.get(prefab, 1)))
    name = pretty_cmd_name(prefab, alias)
    if amt > 1:
        name = f"{name} x{amt}"
    e = {
        "name": name,
        "cmd": command or f"#{(alias or prefab).lower()}",
        "prefab": prefab,
    }
    cost = COIN_COSTS.get(prefab)
    if cost is not None:
        # Stack-aware: charge unit × defaultAmount (matches bridge costFor)
        e["cost"] = int(cost) * amt
    if amt > 1:
        e["amount"] = amt
    if desc:
        e["desc"] = desc
    return e


def load_economy_meta(path: Path = ECONOMY_CATALOG) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Map prefab → coinCost, defaultAmount, tier from Heim-Heim economy catalog."""
    if not path.is_file():
        print(f"WARNING: economy catalog missing at {path} — cards will omit 🪙")
        return {}, {}, {}
    raw = json.loads(path.read_text())
    costs: dict[str, int] = {}
    amounts: dict[str, int] = {}
    tiers: dict[str, int] = {}
    rows = raw.get("entries") or list((raw.get("byId") or {}).values())
    for row in rows:
        pid = row.get("id") or row.get("prefab")
        if not pid:
            continue
        pid = str(pid)
        try:
            costs[pid] = max(1, int(round(float(row.get("coinCost") or 1))))
        except (TypeError, ValueError):
            pass
        try:
            amt = int(row.get("defaultAmount") or 1)
            if amt > 1:
                amounts[pid] = amt
        except (TypeError, ValueError):
            pass
        try:
            if row.get("tier") is not None:
                tiers[pid] = max(0, min(6, int(row["tier"])))
        except (TypeError, ValueError):
            pass
    return costs, amounts, tiers


def load_coin_costs(path: Path = ECONOMY_CATALOG) -> dict[str, int]:
    """Map prefab id → coinCost from Heim-Heim economy catalog."""
    costs, _, _ = load_economy_meta(path)
    return costs


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

# Unified progression tiers (sets share one bucket per biome step)
TIER_ORDER = [
    "T0 · Meadows",
    "T1 · Black Forest",
    "T2 · Swamp",
    "T3 · Mountain",
    "T4 · Plains",
    "T5 · Mistlands",
    "T6 · Ashlands",
    "Special",
    "Other",
]

# Armor → unified tier (first substring match wins; Troll before Leather)
ARMOR_TIER_HINTS = [
    ("Berserker", "T6 · Ashlands"),
    ("Rags", "T0 · Meadows"),
    ("Troll", "T1 · Black Forest"),
    ("Leather", "T0 · Meadows"),
    ("Bronze", "T1 · Black Forest"),
    ("Root", "T2 · Swamp"),
    ("Iron", "T2 · Swamp"),
    ("Fenring", "T3 · Mountain"),
    ("DeepNorth", "T3 · Mountain"),
    ("Wolf", "T3 · Mountain"),
    # Full Lox set (chest/legs/helmet/cape) stays with Padded on Plains
    ("Lox", "T4 · Plains"),
    ("Padded", "T4 · Plains"),
    ("Carapace", "T5 · Mistlands"),
    ("Eitr", "T5 · Mistlands"),
    ("Mage", "T5 · Mistlands"),
    ("Asksvin", "T6 · Ashlands"),
    ("Flametal", "T6 · Ashlands"),
    ("Ashlands", "T6 · Ashlands"),
]

# Capes / hoods that must land in a biome tier (not a separate Special bucket)
CAPE_TIER = {
    "CapeDeerHide": "T0 · Meadows",
    "CapeTrollHide": "T1 · Black Forest",
    "CapeWolf": "T3 · Mountain",
    "CapeLox": "T4 · Plains",
    "CapeLinen": "T4 · Plains",
    "CapeFeather": "T5 · Mistlands",
    "CapeAsh": "T6 · Ashlands",
    "CapeDeepNorth": "T3 · Mountain",
    "CapeOdin": "T0 · Meadows",
}

# Core building / crafting mats often mis-tagged Misc or Food in the prefab catalog
CORE_MATERIAL_PREFABS = {
    "Wood",
    "FineWood",
    "RoundLog",  # Core wood
    "ElderBark",  # Ancient bark
    "Blackwood",
    "Frostwood",
    "YggdrasilWood",
    "BarkaBranch",
    "Chain",
    "WitheredBone",
    "AncientSeed",
    "Thunderstone",
    "BlackCore",
    "Softtissue",
    "MechanicalSpring",
    "Bloodbag",
    "Root",
    "SerpentScale",
    "Guck",
    "Ooze",
    "OozeMork",
    "Resin",
    "Coal",
    "Stone",
    "Flint",
    "Obsidian",
    "Crystal",
    "BlackMarble",
    "Grausten",
    "Chitin",
    "Feathers",
    "LeatherScraps",
    "DeerHide",
    "TrollHide",
    "WolfPelt",
    "LoxPelt",
    "SurtlingCore",
    "MoltenCore",
    "FrostCore",
    "CharredBone",
    "BonemawSerpentScale",
    "BonemawSerpentTooth",
    "GiantBloodSack",
    "WrithanRoots",
    "Needle",
    "FreezeGland",
    "GreydwarfEye",
    "JuteBlue",
    "JuteRed",
    "LinenThread",
    "QueenBee",
    "ProustitePowder",
    "WolfClaw",
    "WolfFang",
    "WolfHairBundle",
    "Ice",
    "SulfurStone",
}

# Keyword → tier for weapons / food / potions / materials (checked T6→T0)
TIER_KEYWORDS = [
    (
        "T6 · Ashlands",
        (
            "flametal",
            "asksvin",
            "ashlands",
            "grausten",
            "charred",
            "morgen",
            "slayer",
            "berserkir",
            "staffredtroll",
            "flametalore",
            "sulfur",
            "proustite",
            "flametalweapon",
            "volture",
        ),
    ),
    (
        "T5 · Mistlands",
        (
            "carapace",
            "eitr",
            "mage",
            "jotun",
            "mistlands",
            "blackcore",
            "softtissue",
            "refinedeitr",
            "seeker",
            "scalehide",
            "bukeperries",
            "misthare",
            "magecap",
            "royaljelly",
            "dverger",
            "gjall",
            "tick",
            "yggdrasil",
            "wispthroat",
            "sap",
            "haremeat",
            "bugmeat",
            "cookedchicken",
            "honeyglazedchicken",
            "cookedegg",
            "mushroomomelette",
            "powdereddragonegg",
        ),
    ),
    (
        "T4 · Plains",
        (
            "blackmetal",
            "padded",
            "lox",
            "barley",
            "flax",
            "cloudberry",
            "tar",
            "deathsquito",
            "goblin",
            "fuling",
            "needle",
            "bread",
            "bloodpudding",
            "fishwraps",
            "eyescream",
            "spice",
            "salad",
            "meatplatter",
            "loxmeat",
            "chickenmeat",
            "chickenegg",
        ),
    ),
    (
        "T3 · Mountain",
        (
            "silver",
            "wolf",
            "fenring",
            "obsidian",
            "freeze",
            "frost",
            "drake",
            "onion",
            "crystal",
            "cultist",
            "ulv",
            "hatchling",
            "wolfjerky",
            "wolfmeat",
            "bjornmeat",
            "moosemeat",
            "dragonegg",
        ),
    ),
    (
        "T2 · Swamp",
        (
            "iron",
            "root",
            "ancientbark",
            "corewood",
            "turnip",
            "guck",
            "chain",
            "wither",
            "entrails",
            "bloodbag",
            "ooze",
            "surtling",
            "leech",
            "draugr",
            "serpent",
            "poison",
            "abomination",
            "serpentmeat",
            "sausages",
            "sausage",
        ),
    ),
    (
        "T1 · Black Forest",
        (
            "bronze",
            "copper",
            "tin",
            "troll",
            "finewood",
            "carrot",
            "deer",
            "greydwarf",
            "skeleton",
            "thistle",
            "blueberr",
            "yellowmushroom",
            "mushroomsyellow",
            "queensjam",
            "boarjerky",
            "deerstew",
            "deermeat",
            "mincemeat",
            "mashedmeat",
            "macebronze",
            "atgierbronze",
            "spearbronze",
            "swordbronze",
            "axebronze",
            "pickaxebronze",
            "shieldbronze",
            "bowfinewood",
        ),
    ),
    (
        "T0 · Meadows",
        (
            "roundlog",
            "wood",
            "stone",
            "flint",
            "leather",
            "rag",
            "resin",
            "feather",
            "honey",
            "dandelion",
            "raspberr",  # Meadows berry
            "cookedmeat",
            "cookedboarmeat",
            "grilledneck",
            "grilled",
            "necktail",
            "rawmeat",
            "boarmeat",
            "rottenmeat",
            "torch",
            "shieldwood",
            "arrowwood",
            "arrowflint",
            "knifeflint",
            "spearflint",
            "axestone",
            "pickaxeantler",
            "pickaxestone",
            "club",
            "tankard",
            "meadhealthminor",
            "meadstaminaminor",
            "meadtastyminor",
            "meadbasehealthminor",
            "meadbasestaminaminor",
            "meadbasetasty",
        ),
    ),
]

FOOD_COOKED = re.compile(r"^(Cooked|Grilled|Smoke|SerpentMeatCooked|FishCooked)", re.I)
# Word-boundary style: avoid matching "Mead" inside "Meadows"
POTION_ITEM = re.compile(
    r"(?:^|_)(?:Mead|MeadBase|BarleyWine|BarleyWineBase|Flask|Potion)",
    re.I,
)
POTION_NAME = re.compile(r"^(Mead|MeadBase|BarleyWine|BarleyWineBase|Flask|Potion)", re.I)
FOOD_RAW = re.compile(r"(Meat|Egg|Fish|Tail|Blubber)$", re.I)
# Moder nest egg looks like *Egg but is a Mountain summon material
NOT_FOOD_ITEMS = {"DragonEgg"}
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
    "Entrails",  # sausage craft ingredient (food mat, not misc)
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
    if prefab.startswith("TurretBolt") or prefab.startswith("Turret"):
        return "Arrows & bolts"
    if "Bomb" in prefab or "Grenade" in prefab:
        return "Throwables"
    return "Other weapons"


def armor_section(prefab: str) -> str:
    if prefab in CAPE_TIER:
        return CAPE_TIER[prefab]
    if prefab.startswith("Cape"):
        # Unknown cape — try material keywords, else progression_tier
        return progression_tier(prefab)
    if prefab.startswith("Trinket"):
        return progression_tier(prefab)
    if "DNHeavy" in prefab or "DNMedium" in prefab:
        return "T3 · Mountain"
    for key, section in ARMOR_TIER_HINTS:
        if key.lower() in prefab.lower():
            return section
    return progression_tier(prefab)


def progression_tier(prefab: str) -> str:
    """Biome-step tier for full sets (weapons / food / potions / materials)."""
    if prefab in ECONOMY_TIERS:
        return TIER_LABEL.get(ECONOMY_TIERS[prefab], "Other")
    p = prefab.lower()
    # Capes / odd armor-adjacent pieces already handled for armor tab
    for tier, keys in TIER_KEYWORDS:
        for key in keys:
            if key in p:
                return tier
    if prefab.startswith(("Mead", "MeadBase", "BarleyWine", "BarleyWineBase")):
        # Mead tiers by suffix when keywords miss
        if any(x in p for x in ("lingering", "major", "frostresist", "poisonresist", "barley")):
            if "barley" in p:
                return "T4 · Plains"
            if "frost" in p:
                return "T3 · Mountain"
            if "poison" in p:
                return "T2 · Swamp"
            return "T2 · Swamp"
        return "T0 · Meadows"
    return "Other"


def is_potion_item(prefab: str) -> bool:
    return bool(POTION_NAME.match(prefab) or POTION_ITEM.search(prefab))


def potion_section(prefab: str) -> str:
    if prefab.startswith("MeadBase") or prefab.startswith("BarleyWineBase"):
        return "Bases"
    if prefab.startswith("BarleyWine"):
        return "Wines"
    if prefab.startswith("Mead"):
        return "Meads"
    if "Flask" in prefab or "Potion" in prefab:
        return "Flasks & potions"
    return "Other potions"


def is_feast_item(prefab: str) -> bool:
    """Biome feast platters (not the unrelated Feaster prefab)."""
    return prefab.startswith("Feast") and prefab != "Feaster"


def food_section(prefab: str) -> str:
    if is_feast_item(prefab):
        return "Feasts"
    if FOOD_COOKED.search(prefab) or prefab.startswith(("Cooked", "Smoked", "Grilled")):
        return "Cooked meals"
    if prefab.endswith("Uncooked") or prefab.startswith(
        ("Spice", "Baked", "Oven", "Mashed", "Mince", "Marinated", "Seeker", "Shocklate", "Sizzling", "Sparkling", "Scorching", "Fiery", "Pulled", "Magically", "GreydwarfSurprise", "Viking", "SealSoup", "Pancakes", "Lingondricka")
    ):
        return "Prepared dishes"
    if any(
        x in prefab
        for x in (
            "Pie",
            "Soup",
            "Stew",
            "Sauce",
            "Skewer",
            "Pancake",
            "Broth",
            "Aspic",
            "Medley",
            "Smoothie",
            "Shake",
            "Cupcake",
            "Ham",
            "Jerky",
            "Salad",
            "Platter",
            "Omelette",
            "Marmalade",
            "Wraps",
            "Pudding",
            "Bread",
            "Sausages",
        )
    ):
        return "Prepared dishes"
    # Crafting guts / thistle sit with raw cook ingredients, not crop bushes
    if prefab in {"Entrails", "Thistle"}:
        return "Raw ingredients"
    if prefab in FOOD_CROP or any(
        prefab.startswith(x)
        for x in (
            "Mushroom",
            "Berry",
            "Honey",
            "Onion",
            "Carrot",
            "Turnip",
            "Barley",
            "Lingon",
            "Vineberry",
            "Pukeberr",
            "FreshSeaweed",
            "Poteitr",
        )
    ):
        return "Crops & forage"
    if (
        FOOD_RAW.search(prefab)
        or prefab.endswith("Meat")
        or "Meat" in prefab
        or prefab
        in {
            "WolfMeat",
            "DeerMeat",
            "BjornMeat",
            "BugMeat",
            "MooseMeat",
            "RottenMeat",
            "BoneMawSerpentMeat",
            "SealBlubber",
            "Larva",
            "NeckTail",
            "Entrails",
        }
    ):
        return "Raw ingredients"
    return "Prepared dishes"


def is_food_item(prefab: str) -> bool:
    """Meats / meals / forage that the catalog often tags as Misc."""
    if prefab in NOT_FOOD_ITEMS:
        return False
    if is_potion_item(prefab):
        return False
    if prefab.startswith(("Staff", "Armor", "Helmet", "Cape", "Trophy", "Pickable")):
        return False
    p = prefab.lower()
    if prefab in FOOD_CROP:
        return True
    if FOOD_COOKED.search(prefab) or (FOOD_RAW.search(prefab) and prefab not in NOT_FOOD_ITEMS):
        return True
    if prefab.endswith(("Meat", "Uncooked", "Skewer", "Jerky", "Blubber")):
        return True
    if "meat" in p and not prefab.startswith("Trophy"):
        return True
    if any(
        x in p
        for x in (
            "pie",
            "soup",
            "stew",
            "sauce",
            "pancake",
            "broth",
            "aspic",
            "medley",
            "smoothie",
            "shake",
            "cupcake",
            "sausage",
            "pudding",
            "omelette",
            "marmalade",
            "wraps",
            "salad",
            "platter",
            "porridge",
            "dricka",
            "kebab",
            "ham",
            "berry",
            "seaweed",
            "lingon",
            "vineberry",
            "pukeberr",
            "feast",
            "spice",
        )
    ):
        return True
    if prefab.startswith(("Cooked", "Smoked", "Grilled", "Feast", "Spice", "Baked", "Oven")):
        return True
    return False


def is_accessory_item(prefab: str) -> bool:
    """Keys, belts, wishbone, demister, etc."""
    if prefab.startswith("Mold"):
        return False
    if prefab in {
        "Wishbone",
        "BarberKit",
        "BeltStrength",
        "Demister",
        "IceSkates",
        "CryptKey",
        "DvergrKey",
        "DvergrKeyFragment",
        "BloodGoldKey",
        "KeysGoldUncooked",
        "GoblinTotem",
        "CrownJewel",
        "Wisp",
        "DragonTear",
        "HardAntler",
    }:
        return True
    if prefab.startswith("HildirKey"):
        return True
    if prefab.endswith("Key") or "Key_" in prefab:
        return True
    if prefab.startswith("Trinket"):
        return True
    return False


def is_weapon_like(prefab: str) -> bool:
    return prefab.startswith(
        (
            "Sword",
            "THSword",
            "Dyrnwyn",
            "Axe",
            "Battleaxe",
            "Mace",
            "Sledge",
            "Club",
            "Spear",
            "Atgeir",
            "Knife",
            "Bow",
            "Crossbow",
            "Arrow",
            "Bolt",
            "TurretBolt",
            "Shield",
            "Staff",
        )
    )


def is_tool_item(prefab: str) -> bool:
    p = prefab.lower()
    if prefab.startswith(("Hammer", "Hoe", "Cultivator", "Pickaxe", "FishingRod")):
        return True
    if "harpoon" in p:
        return True
    return False


def looks_like_material(prefab: str) -> bool:
    """Rescue core mats mis-tagged as Misc/Food so RoundLog / ElderBark / etc. are never missed."""
    if prefab in CORE_MATERIAL_PREFABS:
        return True
    if prefab.startswith(
        (
            "Pickable",
            "TreasureChest",
            "loot_chest",
            "LootSpawner",
            "Vegvisir",
            "HealthUpgrade",
            "HildirKey",
            "Trinket",
            "Armor",
            "Helmet",
            "Cape",
            "Feast",
            "Spice",
            "Mold",
            "THSword",
            "Orb",
        )
    ):
        return False
    p = prefab.lower()
    if "projectile" in p or "ragdoll" in p:
        return False
    if prefab.endswith(("Ore", "Scrap", "Hide", "Pelt", "Core")):
        return True
    if any(
        x in p
        for x in (
            "roundlog",
            "elderbark",
            "blackwood",
            "frostwood",
            "yggdrasilwood",
            "finewood",
        )
    ):
        return True
    # Heuristic: material_section recognized a real family (not the catch-all)
    if material_section(prefab) != "Crafting parts" and not is_weapon_like(prefab):
        # Avoid pulling random Misc junk that substring-matches "iron" etc. via section only
        if any(
            x in p
            for x in (
                "wood",
                "bark",
                "ore",
                "scrap",
                "hide",
                "pelt",
                "resin",
                "coal",
                "flint",
                "obsidian",
                "crystal",
                "chitin",
                "scale",
                "wool",
                "entrails",
                "guck",
                "bone",
                "feather",
                "bloodbag",
                "chain",
                "core",
            )
        ):
            return True
    return False


def material_section(prefab: str) -> str:
    if prefab == "DragonEgg":
        return "Boss & rare drops"
    p = prefab.lower()
    # Trophies first — never let metal substrings steal them
    if prefab.startswith("Trophy") or "trophy" in p:
        return "Boss & rare drops"
    if any(
        x in p
        for x in (
            "wood",
            "roundlog",
            "finewood",
            "corewood",
            "yggdrasilwood",
            "elderbark",
            "blackwood",
            "frostwood",
            "barkabranch",
        )
    ):
        return "Wood & plant"
    if prefab in {"Root", "WrithanRoots"} or p.endswith("roots"):
        return "Wood & plant"
    if prefab in {"BlackMarble", "Grausten", "Ice", "SulfurStone"} or any(
        x in p for x in ("stone", "flint", "obsidian", "crystal", "thunderstone", "grausten")
    ):
        return "Stone & crystal"
    # Hides / fiber before metals (LeatherScraps ends with scrap)
    if any(
        x in p
        for x in (
            "hide",
            "leather",
            "pelt",
            "wool",
            "hair",
            "scale",
            "chitin",
            "carapace",
            "jute",
            "linen",
            "feather",
        )
    ):
        return "Hides & scales"
    if prefab.endswith("Core") or any(
        x in p for x in ("surtlingcore", "blackcore", "frostcore", "moltencore")
    ):
        return "Boss & rare drops"
    if any(
        x in p
        for x in (
            "bloodbag",
            "ooze",
            "guck",
            "entrails",
            "freezegland",
            "greydwarfeye",
            "needle",
            "wolfclaw",
            "wolffang",
            "chain",
            "proustite",
            "queenbee",
            "ectoplasm",
            "mandible",
            "sinew",
            "bladder",
            "carrion",
            "resin",
            "coal",
            "withbone",
            "withere",
            "charredbone",
            "bonefragments",
        )
    ) or prefab in {"WitheredBone", "CharredBone", "Chain", "Ooze", "Bloodbag", "Needle"}:
        return "Crafting parts"
    metal_prefabs = {
        "Copper",
        "Tin",
        "Iron",
        "Silver",
        "Bronze",
        "BlackMetal",
        "Flametal",
        "FlametalNew",
        "TinOre",
        "CopperOre",
        "SilverOre",
        "FlametalOre",
        "FlametalOreNew",
        "GoldOre",
        "IronOre",
        "IronScrap",
        "CopperScrap",
        "BronzeScrap",
        "BlackMetalScrap",
        "BronzeNails",
    }
    if prefab in metal_prefabs or (
        not prefab.startswith("Trinket")
        and (
            any(x in p for x in ("bronze", "copper", "blackmetal", "flametal", "ironscrap"))
            or p.endswith("ore")
            or (p.endswith("scrap") and "leather" not in p)
            or prefab in {"Silver", "Iron", "Tin", "Copper", "Bronze"}
        )
    ):
        return "Metals"
    if any(x in p for x in ("boss", "egg", "queen", "eitr", "dragontear", "yagluth", "fader", "ymir")):
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
    if "treasure" in p or "chest" in p or "coffer" in p or prefab.startswith("loot_"):
        return "Chests & treasure"
    if "firework" in p or "bell" in p or "sparkler" in p:
        return "Fun & fireworks"
    if is_accessory_item(prefab):
        return "Accessories"
    if "saddle" in p or ("asksvin" in p and "egg" in p) or prefab.endswith("Egg"):
        return "Mounts & eggs"
    if any(x in p for x in ("torch", "lantern", "candle", "firepit", "campfire")):
        return "Light sources"
    if any(
        x in p for x in ("hammer", "hoe", "cultivator", "pickaxe", "fishing", "harpoon", "shovel")
    ) or prefab in {"Shovel", "GrapplingHook", "Hook"}:
        return "Tools"
    if "trophy" in p:
        return "Trophies"
    if any(x in p for x in ("seed", "cone", "acorn")) or prefab.endswith("Seeds"):
        return "Utility & oddities"
    return "Utility & oddities"


def classify_item(it: dict) -> tuple[str, str]:
    """Return (tab, section)."""
    prefab = it["prefab"]
    cat = it.get("category") or "Misc"

    if is_potion_item(prefab):
        return "potions", potion_section(prefab)
    if is_tool_item(prefab):
        return "misc", "Tools"
    if is_weapon_like(prefab) or prefab.startswith(("Tankard", "Torch")):
        if prefab.startswith("Torch") or prefab.startswith("Tankard"):
            return "weapons", "Utility weapons"
        return "weapons", weapon_section(prefab)

    # Trinkets / armor wearables before material keyword rescue (TrinketBronze ≠ metal bar)
    if (
        prefab.startswith("Trinket")
        or prefab.startswith("SP_Armor")
        or prefab.startswith("Armor")
        or prefab.startswith("Helmet")
        or prefab.startswith("Cape")
    ):
        return "armor", armor_section(prefab)

    # Accessories (CryptKey / skeleton-dungeon keys, wishbone, megingjord…)
    if is_accessory_item(prefab):
        return "misc", "Accessories"

    # Moder nest egg — Mountain rare summon mat (never Food / Misc junk)
    if prefab == "DragonEgg":
        return "materials", "Boss & rare drops"

    # Food before material rescue — WolfMeat / meals must not sit in Utility
    if cat == "Food" or is_food_item(prefab):
        return "food", food_section(prefab)

    # Core mats (RoundLog, ElderBark, Bloodbag, BlackMarble…)
    if looks_like_material(prefab) or cat == "Materials":
        if is_weapon_like(prefab):
            return "weapons", weapon_section(prefab)
        return "materials", material_section(prefab)

    if cat == "Weapons":
        return "weapons", weapon_section(prefab)
    if cat == "Armor":
        return "armor", armor_section(prefab)
    if cat == "Valuables":
        return "materials", "Valuables"
    if prefab.startswith(("THSword", "Dyrnwyn")):
        return "weapons", "Swords"
    if prefab.startswith("Trophy"):
        return "materials", "Boss & rare drops"
    return "misc", misc_section(prefab)


# Prioritized "Quick" picks for streamers
QUICK_PREFABS = [
    ("Greyling", "Starter mob — soft chaos"),
    ("Boar", "Meadows pest"),
    ("Skeleton", "Raid filler"),
    ("Neck", "Shore pest"),
    ("Wood", "Building basics"),
    ("Stone", "Building basics"),
    ("FineWood", "Quality builds"),
    ("RoundLog", "Core wood"),
    ("ElderBark", "Ancient bark"),
    ("Iron", "Mid-game metal"),
    ("Bronze", "Early metal"),
    ("Coal", "Smelting fuel"),
    ("Resin", "Torch fuel"),
    ("CookedMeat", "Quick food"),
    ("Honey", "Mead base"),
    ("MeadHealthMinor", "Heal up"),
    ("MeadStaminaMinor", "Stamina up"),
    ("ArrowFire", "Ranged spice"),
    ("MaceBronze", "Early smash"),
    ("MaceWood", "Starter club"),
    ("ShieldWood", "Starter block"),
    ("ShieldBronzeBuckler", "Bronze block"),
    ("Torch", "Light"),
]


def inject_food_aliases(items: list[dict]) -> list[dict]:
    """Ensure #boarmeat / #cookedboarmeat appear even if SoftRef id is RawMeat."""
    by = {i["prefab"]: i for i in items}
    extras = [
        ("RawMeat", "boarmeat", "#boarmeat", "Boar drop (RawMeat)"),
        ("CookedMeat", "cookedboarmeat", "#cookedboarmeat", "Cooked boar meat"),
    ]
    out = list(items)
    seen_alias = {str(i.get("alias") or "").lower() for i in items}
    for prefab, alias, cmd, _desc in extras:
        if prefab not in by or alias in seen_alias:
            continue
        donor = by[prefab]
        out.append(
            {
                **donor,
                "alias": alias,
                "command": cmd,
                "bareCommand": True,
                "category": "Food",
                "_displayPrefab": prefab,
            }
        )
        seen_alias.add(alias)
    return out


def build_store(data: dict) -> dict:
    creatures = data.get("creatures") or []
    items = [
        i
        for i in (data.get("items") or [])
        if i.get("bareCommand") and not should_skip_item(i["prefab"])
    ]
    items = inject_food_aliases(items)

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
                "text": "Streamer favourites first. Full lists live in the other tabs. Materials default ×10 (e.g. #silver → 10, cost ×10) · override with #silver 50 · arrows default to 10 · stack-capped.",
            },
            {"type": "section", "title": "Chat basics"},
            {"name": "Visit", "cmd": "#visit", "desc": "Spawn your named Greyling"},
            {"name": "Follower ally", "cmd": "#f", "desc": "#f / #follower [creature] [stars] — ally (default Greyling)"},
            {"name": "Yeet", "cmd": "#yeet", "desc": "Launch the streamer (optional N/S/E/W)", "cost": 10, "prefab": "Yeet"},
            {"name": "Spawn (legacy)", "cmd": "#spawn Greyling", "desc": "Explicit spawn form"},
            {"name": "Give / item", "cmd": "#give Wood 50", "desc": "#give or #item · materials default ×10 · amount override OK · capped to stack"},
        ],
        "mobs": [],
        "weapons": [],
        "armor": [],
        "food": [],
        "potions": [],
        "curses": [
            {
                "type": "help",
                "text": "Bad = mischief · Good = buffs. Costs shown on each card. Streamer can disable any curse in Heim-Heim >CURSES< (icon toggle) — no coins spent. #yeet accepts N/S/E/W. #feast = HP+stam burst (not Food Prep).",
            },
            {"type": "section", "title": "Bad"},
            {"name": "Yeet", "cmd": "#yeet", "prefab": "Yeet", "desc": "Launch player (optional N/S/E/W)", "cost": 10},
            {"name": "Mini", "cmd": "#mini", "prefab": "Mini", "desc": "Shrink the player for a while", "cost": 10},
            {"name": "Ragdoll", "cmd": "#ragdoll", "prefab": "Ragdoll", "desc": "Hard stagger + short push", "cost": 10},
            {"name": "Drunk", "cmd": "#drunk", "prefab": "Drunk", "desc": "Woozy turn/move for ~20s", "cost": 10},
            {"name": "Cold", "cmd": "#cold", "prefab": "Cold", "desc": "Cold + Freezing pressure", "cost": 10},
            {"name": "Wet", "cmd": "#wet", "prefab": "Wet", "desc": "Instant soak (Wet)", "cost": 10},
            {"name": "Smoked", "cmd": "#smoked", "prefab": "Smoked", "desc": "Mild poison smoke tick", "cost": 10},
            {"name": "Hungry", "cmd": "#hungry", "prefab": "Hungry", "desc": "Clear food timers", "cost": 10},
            {"name": "Tired", "cmd": "#tired", "prefab": "Tired", "desc": "Stamina crash + drain", "cost": 10},
            {"name": "Encumber", "cmd": "#encumber", "prefab": "Encumber", "desc": "Temporary −100 carry weight (~67s)", "cost": 10},
            {"name": "Butterfingers", "cmd": "#butterfingers", "prefab": "Butterfingers", "desc": "Fumble / unequip hands", "cost": 10},
            {"name": "Spin", "cmd": "#spin", "prefab": "Spin", "desc": "Wild yaw spin", "cost": 10},
            {"name": "Dark", "cmd": "#dark", "prefab": "Dark", "desc": "Forced dark environment", "cost": 10},
            {"name": "Bee", "cmd": "#bee", "prefab": "Bee", "desc": "Spawn a Deathsquito nearby", "cost": COIN_COSTS.get("Deathsquito", 17)},
            {"name": "Greyling gang", "cmd": "#greylinggang", "prefab": "GreylingGang", "desc": "Three Greylings on you", "cost": COIN_COSTS.get("Greyling", 5) * 3},
            {"name": "Troll toe", "cmd": "#trolltoe", "prefab": "TrollToe", "desc": "Knockback + oof", "cost": 10},
            {"name": "Silence", "cmd": "#silence", "prefab": "Silence", "desc": "Hands empty / panic", "cost": 10},
            {"name": "Magnet", "cmd": "#magnet", "prefab": "Magnet", "desc": "Yank hostiles toward player", "cost": 10},
            {"type": "section", "title": "Good"},
            {"name": "Health", "cmd": "#health", "prefab": "Health", "desc": "Health regen buff", "cost": 10},
            {"name": "Stamina", "cmd": "#stamina", "prefab": "Stamina", "desc": "Stamina regen buff", "cost": 10},
            {"name": "Sonic", "cmd": "#sonic", "prefab": "Sonic", "desc": "Speed buff (longer)", "cost": 10},
            {"name": "Mule", "cmd": "#mule", "prefab": "Mule", "desc": "Temporary +100 carry weight (~67s)", "cost": 10},
            {"name": "Shield", "cmd": "#shield", "prefab": "Shield", "desc": "Timed resist / absorb", "cost": 10},
            {"name": "Warm", "cmd": "#warm", "prefab": "Warm", "desc": "Frost/cold resist", "cost": 10},
            {"name": "Dry", "cmd": "#dry", "prefab": "Dry", "desc": "Clear Wet + stay dry", "cost": 10},
            {"name": "Feast", "cmd": "#feast", "prefab": "Feast", "desc": "Small HP + stamina burst (not Food Prep)", "cost": 10},
            {"name": "Iron skin", "cmd": "#ironskin", "prefab": "IronSkin", "desc": "High resist window", "cost": 10},
            {"name": "Eagle", "cmd": "#eagle", "prefab": "Eagle", "desc": "Jumpier for a minute", "cost": 10},
            {"name": "Night vision", "cmd": "#nightvision", "prefab": "NightVision", "desc": "Personal light", "cost": 10},
            {"name": "Rested", "cmd": "#rested", "prefab": "Rested", "desc": "Apply/extend Rested", "cost": 10},
            {"name": "XP", "cmd": "#xp", "prefab": "Xp", "desc": "Tiny random skill XP", "cost": 10},
            {"name": "Repair", "cmd": "#repair", "prefab": "Repair", "desc": "Nudge equipped durability", "cost": 10},
            {"name": "Cleanse", "cmd": "#cleanse", "prefab": "Cleanse", "desc": "Strip bad curse effects", "cost": 10},
            {"name": "Breeze", "cmd": "#breeze", "prefab": "Breeze", "desc": "Light speed + stam regen", "cost": 10},
            {"name": "Anchor", "cmd": "#anchor", "prefab": "Anchor", "desc": "Anti-stagger window", "cost": 10},
            {"name": "Honey", "cmd": "#honey", "prefab": "HoneyBuff", "desc": "Poison resist + gentle regen", "cost": 10},
            {"name": "Guardian", "cmd": "#guardian", "prefab": "Guardian", "desc": "2★ random skeleton ally", "cost": int(round(COIN_COSTS.get("Skeleton", 9) * 2.5))},
            {"type": "section", "title": "Followers"},
            {
                "name": "Follower",
                "cmd": "#f",
                "prefab": "Greyling",
                "desc": "#f / #follower [creature] [0|1|2] — ally at creature cost (default Greyling)",
                "cost": COIN_COSTS.get("Greyling", 5),
            },
        ],
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
            "text": "Pick a biome sub-tab. Bosses are separate. Bare #alias · optional ★ level (#boar 2). ★ costs: ★1 = base 🪙 · ★2 = ×1.75 · ★3 = ×2.5. Count is always 1 for now.",
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

    weapon_families = [
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
    ]
    section_order = {
        "weapons": weapon_families,
        "armor": list(TIER_ORDER),
        "food": [
            "Feasts",
            "Raw ingredients",
            "Cooked meals",
            "Prepared dishes",
            "Crops & forage",
        ],
        "potions": [
            "Meads",
            "Bases",
            "Wines",
            "Flasks & potions",
            "Other potions",
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

    # Tabs with progression tiers listed first, then by type/family
    tier_first_tabs = ("weapons", "food", "potions", "materials")

    for tab, order in section_order.items():
        help_text = {
            "weapons": "Gold row = tiers (T0–T6). Second row = weapon family. Catalog starts with tier sets.",
            "armor": "Unified tiers — each T# holds the full armor sets for that step.",
            "food": "Gold row = tiers. Second row = feasts / raw / cooked / prepared / crops. Feasts are type-only (not under tiers).",
            "potions": "Gold row = tiers. Second row = meads / bases / wines. Catalog starts with tiers.",
            "materials": "Gold row = tiers. Second row = wood / metals / etc. Catalog starts with tiers.",
            "misc": "Tools, lights, mounts, fireworks, chests — streamer-useful leftovers.",
        }[tab]
        store[tab].append({"type": "help", "text": help_text})

        if tab in tier_first_tabs:
            tab_items: dict[str, dict] = {}
            for section, lst in buckets[tab].items():
                for it in lst:
                    tab_items[it["prefab"]] = it
            by_tier: dict[str, list] = defaultdict(list)
            for it in tab_items.values():
                # Feasts live only under the Feasts type section (not duplicated in tiers).
                if tab == "food" and is_feast_item(it["prefab"]):
                    continue
                by_tier[progression_tier(it["prefab"])].append(it)

            store[tab].append(
                {
                    "type": "help",
                    "text": "By tier — full sets for that progression step.",
                }
            )
            for tier in TIER_ORDER:
                lst = by_tier.get(tier) or []
                if not lst:
                    continue
                store[tab].append({"type": "section", "title": tier})
                for it in sorted(lst, key=lambda x: x["prefab"].lower()):
                    store[tab].append(
                        entry(it["prefab"], it.get("alias"), it.get("command"))
                    )

            store[tab].append(
                {
                    "type": "help",
                    "text": "By type — same items grouped by family / category.",
                }
            )

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
            # Skip bare tier titles already emitted above for tier_first tabs
            if tab in tier_first_tabs and section in TIER_ORDER:
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
    import argparse

    ap = argparse.ArgumentParser(description="Build Valheim Twitch command store")
    ap.add_argument(
        "--no-icons",
        action="store_true",
        help="Skip wiki icon fetch (regenerate JS catalog only)",
    )
    args = ap.parse_args()

    global COIN_COSTS, DEFAULT_AMOUNTS, ECONOMY_TIERS
    COIN_COSTS, DEFAULT_AMOUNTS, ECONOMY_TIERS = load_economy_meta()
    print(
        f"Loaded {len(COIN_COSTS)} coin costs, {len(DEFAULT_AMOUNTS)} defaultAmounts, "
        f"{len(ECONOMY_TIERS)} tiers from {ECONOMY_CATALOG}"
    )

    data = json.loads(CATALOG.read_text())
    print("Building store from", CATALOG)
    store = build_store(data)
    store.setdefault("meta", {})["currency"] = "🪙"
    store["meta"]["economySource"] = str(ECONOMY_CATALOG)
    write_js(store)

    if args.no_icons:
        print("Skipping icon fetch (--no-icons)")
        return

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

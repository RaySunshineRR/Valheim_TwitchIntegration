#!/usr/bin/env python3
"""Force-overwrite icon PNGs from ICON_OVERRIDES (wiki weirdgloop → 64×64).

Use when cached icons are wrong duplicates/placeholders. Does not mass-touch
icons that are not listed in FORCE_PREFABS / ICON_OVERRIDES keys passed in.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "assets" / "icons"
ICON_MAP = ROOT / "assets" / "icon-map.json"
WIKI_IMG = "https://valheim.weirdgloop.org/images/"
UA = {"User-Agent": "ValheimTwitchStore/0.8-force-icons"}

# Import overrides by parsing build-store (avoid import side effects)
src = (ROOT / "tools" / "build-store.py").read_text()
m = re.search(r"^ICON_OVERRIDES = \{.*?^\}", src, re.S | re.M)
ns: dict = {}
exec(m.group(0), ns)  # noqa: S102
OVERRIDES: dict[str, str] = ns["ICON_OVERRIDES"]

FORCE = [
    # T5–T7 armor + DN
    "ArmorDeepNorthHeavyChest",
    "ArmorDeepNorthHeavylegs",
    "ArmorDeepNorthMediumChest",
    "ArmorDeepNorthMediumlegs",
    "ArmorDeepNorthMageChest",
    "ArmorDeepNorthMagelegs",
    "HelmetDNHeavy",
    "HelmetDNMediumHood",
    "HelmetDNMage",
    "CapeDeepNorth",
    "CapeDeepNorthMage",
    "ArmorWolfChest",
    "ArmorWolfLegs",
    "HelmetDrake",
    "CapeWolf",
    "HelmetMage",
    "ArmorMageChest",
    "ArmorMageLegs",
    "HelmetMage_Ashlands",
    "ArmorMageChest_Ashlands",
    "ArmorMageLegs_Ashlands",
    "HelmetAshlandsMediumHood",
    "ArmorAshlandsMediumChest",
    "ArmorAshlandsMediumlegs",
    "HelmetCarapace",
    "ArmorCarapaceChest",
    "ArmorCarapaceLegs",
    "HelmetFlametal",
    "ArmorFlametalChest",
    "ArmorFlametalLegs",
    "CapeAsh",
    "CapeAsksvin",
    "CapeFeather",
    "FistBjornClaw",
    "FistBjornUndeadClaw",
    # Molds / cast
    "MoldArmorGoldHelmet",
    "MoldArmorGoldChest",
    "MoldArmorGoldLegs",
    "MoldArmorMediumHelmet",
    "MoldArmormediumChest",
    "MoldArmorMediumLegs",
    "MoldArmorMageHelmet",
    "MoldArmorMageChest",
    "MoldArmorMageLegs",
    "ArmorGoldHeavyHelmetUncooked",
    "ArmorGoldHeavyChestUncooked",
    "ArmorGoldHeavyLegsUncooked",
    "ArmorGoldMediumHelmetUncooked",
    "ArmorGoldMediumChestUncooked",
    "ArmorGoldMediumLegsUncooked",
    "ArmorGoldMageHelmetUncooked",
    "ArmorGoldMageChestUncooked",
    "ArmorGoldMageLegsUncooked",
    # Baits + cooked meat
    "FishingBait",
    "FishingBaitForest",
    "FishingBaitSwamp",
    "FishingBaitPlains",
    "FishingBaitOcean",
    "FishingBaitMistlands",
    "FishingBaitAshlands",
    "FishingBaitDeepNorth",
    "FishingBaitCave",
    "CookedMeat",
    "CookedBoarMeat",
    "RawMeat",
    # Trinkets
    "TrinketBronzeHealth",
    "TrinketBronzeStamina",
    "TrinketIronHealth",
    "TrinketIronStamina",
    "TrinketChitinSwim",
    "TrinketSilverDamage",
    "TrinketSilverResist",
    "TrinketBlackDamageHealth",
    "TrinketBlackStamina",
    "TrinketCarapaceEitr",
    "TrinketScaleStaminaDamage",
    "TrinketFlametalEitr",
    "TrinketFlametalStaminaHealth",
    "TrinketBloodGoldHealth",
    "TrinketBloodGoldStamina",
    # DN mobs
    "DvergerDeepNorth",
    "Skeleton_DeepNorth",
    "GoblinDeepNorth",
    "Greydwarf_Frozen",
    # Nord / Deep North weapons
    "AtgeirGold",
    "AtgeirGold_BloodLightning",
    "AtgeirGold_FrostFire",
    "AxeGold",
    "AxeGold_BloodLightning",
    "AxeGold_FrostFire",
    "BattleaxeGold",
    "BattleaxeGold_BloodLightning",
    "BattleaxeGold_FrostFire",
    "BowGold",
    "BowGold_BloodLightning",
    "BowGold_FrostFire",
    "CrossbowGold",
    "CrossbowGold_BloodLightning",
    "CrossbowGold_FrostFire",
    "FistBjornClaw",
    "FistBjornUndeadClaw",
    "FistGold",
    "FistGold_BloodLightning",
    "FistGold_FrostFire",
    "KnifeGold",
    "KnifeGold_BloodLightning",
    "KnifeGold_FrostFire",
    "MaceGold",
    "MaceGold_BloodLightning",
    "MaceGold_FrostFire",
    "ShieldGold",
    "ShieldGoldBuckler",
    "ShieldGoldTower",
    "SledgeGold",
    "SledgeGold_BloodLightning",
    "SledgeGold_FrostFire",
    "SpearGold",
    "SpearGold_BloodLightning",
    "SpearGold_FrostFire",
    "StaffFrostOrbs",
    "StaffOrbofAhri",
    "SwordGold",
    "SwordGold_BloodLightning",
    "SwordGold_FrostFire",
    "THSwordGold",
    "THSwordGold_BloodLightning",
    "THSwordGold_FrostFire",
    # Misc overhaul — fireworks / chests / jute / boss drops
    "FireworksRocket_Blue",
    "FireworksRocket_Cyan",
    "FireworksRocket_Green",
    "FireworksRocket_Purple",
    "FireworksRocket_Red",
    "FireworksRocket_White",
    "FireworksRocket_Yellow",
    "Sparkler",
    "JuteRed",
    "JuteBlue",
    "CryptKey",
    "Wishbone",
    "AncientSeed",
    "WitheredBone",
    "DragonTear",
    "BlackCore",
    "MoltenCore",
    "Thunderstone",
    "GoblinTotem",
    "TreasureChest_meadows",
    "TreasureChest_meadows_01",
    "TreasureChest_meadows_02",
    "TreasureChest_meadows_buried",
    "TreasureChest_meadows_combat",
    "TreasureChest_blackforest",
    "TreasureChest_forestcrypt",
    "TreasureChest_forestcrypt_hildir",
    "TreasureChest_fCrypt",
    "TreasureChest_swamp",
    "TreasureChest_sunkencrypt",
    "TreasureChest_mountains",
    "TreasureChest_mountaincave",
    "TreasureChest_mountaincave_hildir",
    "TreasureChest_heath",
    "TreasureChest_heath_hildir",
    "TreasureChest_plains_stone",
    "TreasureChest_plainsfortress_hildir",
    "TreasureChest_trollcave",
    "TreasureChest_dvergrtower",
    "TreasureChest_dvergrtown",
    "TreasureChest_dvergr_loose_stone",
    "TreasureChest_ashland_stone",
    "TreasureChest_charredfortress",
    "TreasureChest_deepnorth_village",
    "TreasureChest_memorial_buried",
    "TreasureChest_morkhalla",
    "loot_chest_wood",
    "loot_chest_stone",
]


def to_64(data: bytes) -> bytes:
    im = Image.open(BytesIO(data)).convert("RGBA")
    # Drop solid black letterbox backgrounds common on old wiki dumps
    px = im.load()
    w, h = im.size
    # only clear near-black corners if fully opaque black dominates edges
    im = im.resize((64, 64), Image.Resampling.LANCZOS)
    buf = BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def fetch(name: str) -> bytes | None:
    url = WIKI_IMG + urllib.parse.quote(name)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        return data if data[:8] == b"\x89PNG\r\n\x1a\n" else None
    except Exception:
        return None


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    mapping = {}
    if ICON_MAP.exists():
        mapping = json.loads(ICON_MAP.read_text())

    ok = fail = 0
    for prefab in FORCE:
        wiki = OVERRIDES.get(prefab)
        if not wiki:
            print("NO OVERRIDE", prefab)
            fail += 1
            continue
        data = fetch(wiki)
        if not data:
            print("FETCH FAIL", prefab, wiki)
            fail += 1
            continue
        out = to_64(data)
        dest = ICON_DIR / f"{prefab}.png"
        dest.write_bytes(out)
        mapping[prefab] = f"assets/icons/{prefab}.png"
        ok += 1
        print(f"OK {prefab:40} ← {wiki} ({len(out)}b)")

    ICON_MAP.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    print(f"done ok={ok} fail={fail} map={len(mapping)}")


if __name__ == "__main__":
    main()

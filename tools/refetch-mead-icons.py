#!/usr/bin/env python3
"""Re-fetch mead/base icons that were placeholder duplicates (same MD5)."""
from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "assets" / "icons"
ICON_MAP = ROOT / "assets" / "icon-map.json"
WIKI = "https://valheim.weirdgloop.org"
UA = {
    "User-Agent": "ValheimTwitchStore/0.8 (+https://github.com/RaySunshineRR/Valheim_TwitchIntegration)"
}

# From build-store.py ICON_OVERRIDES (mead subset)
OVERRIDES = {
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
    "MeadBugRepellent": "Anti-Sting_Mead.png",
    "MeadHasty": "Brew_of_the_Wolf.png",
    "MeadStrength": "Draught_of_the_Bull.png",
    "MeadSwimmer": "Draught_of_the_Whale.png",
    "MeadTamer": "Brew_of_the_Boar.png",
    "MeadTrollPheromones": "Troll_Pheromones.png",
    "BarleyWine": "Fire_Resistance_Barley_Wine.png",
    "BarleyWineBase": "Barley_Wine_Base.png",
    "MeadBaseHealthMinor": "Minor_Healing_Mead.png",
    "MeadBaseHealthMedium": "Medium_Healing_Mead.png",
    "MeadBaseHealthMajor": "Major_Healing_Mead.png",
    "MeadBaseHealthLingering": "Lingering_Healing_Mead.png",
    "MeadBaseStaminaMinor": "Minor_Stamina_Mead.png",
    "MeadBaseStaminaMedium": "Medium_Stamina_Mead.png",
    "MeadBaseStaminaLingering": "Lingering_Stamina_Mead.png",
    "MeadBaseTasty": "Tasty_Mead.png",
    "MeadBasePoisonResist": "Poison_Resistance_Mead.png",
    "MeadBaseFrostResist": "Frost_Resistance_Mead.png",
    "MeadBaseLightFoot": "Lightfoot_Mead.png",
    "MeadBaseBzerker": "Berserkir_Mead.png",
    "MeadBaseEitrMinor": "Minor_Eitr_Mead.png",
    "MeadBaseEitrLingering": "Lingering_Eitr_Mead.png",
    "MeadBaseBugRepellent": "Anti-Sting_Mead.png",
    "MeadBaseHasty": "Brew_of_the_Wolf.png",
    "MeadBaseStrength": "Draught_of_the_Bull.png",
    "MeadBaseSwimmer": "Draught_of_the_Whale.png",
    "MeadBaseTamer": "Brew_of_the_Boar.png",
}


def fetch(name: str) -> bytes | None:
    url = f"{WIKI}/images/{urllib.parse.quote(name)}"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return data
    except Exception as e:
        print("  fail", name, type(e).__name__)
    return None


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    icon_map = {}
    if ICON_MAP.exists():
        icon_map = json.loads(ICON_MAP.read_text())

    # Prefer pillow+pngquant path via optimize script later; write raw then shrink.
    from io import BytesIO

    try:
        from PIL import Image
    except ImportError:
        Image = None  # type: ignore

    ok = 0
    fail = 0
    for prefab, wiki_name in OVERRIDES.items():
        data = fetch(wiki_name)
        if not data:
            # try File: API
            api = (
                f"{WIKI}/api.php?action=query&titles=File:{urllib.parse.quote(wiki_name)}"
                f"&prop=imageinfo&iiprop=url&format=json"
            )
            try:
                req = urllib.request.Request(api, headers=UA)
                with urllib.request.urlopen(req, timeout=20) as r:
                    meta = json.loads(r.read().decode())
                for page in meta.get("query", {}).get("pages", {}).values():
                    info = (page.get("imageinfo") or [{}])[0]
                    u = info.get("url")
                    if u:
                        req2 = urllib.request.Request(u, headers=UA)
                        with urllib.request.urlopen(req2, timeout=20) as r2:
                            data = r2.read()
            except Exception as e:
                print("  api fail", prefab, e)
        if not data or data[:8] != b"\x89PNG\r\n\x1a\n":
            print("MISS", prefab, wiki_name)
            fail += 1
            continue

        out = ICON_DIR / f"{prefab}.png"
        if Image is not None:
            im = Image.open(BytesIO(data)).convert("RGBA")
            im = im.resize((64, 64), Image.Resampling.LANCZOS)
            # flatten? keep transparency
            buf = BytesIO()
            im.save(buf, format="PNG", optimize=True)
            data = buf.getvalue()
        out.write_bytes(data)
        icon_map[prefab] = f"assets/icons/{prefab}.png"
        digest = hashlib.md5(data).hexdigest()[:8]
        print("OK", prefab, wiki_name, digest, len(data))
        ok += 1

    ICON_MAP.write_text(json.dumps(icon_map, indent=2, sort_keys=True) + "\n")
    print(f"Done ok={ok} fail={fail}")


if __name__ == "__main__":
    main()

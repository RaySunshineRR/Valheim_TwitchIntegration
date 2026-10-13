# Valheim Twitch Command Store

GitHub Pages storefront for **Heim-Heim** Twitch `#commands`.

Live site (after Pages is enabled):  
https://raysunshinerr.github.io/Valheim_TwitchIntegration/

## Features

- Tabs: **Quick · Mobs · Weapons · Armor · Food · Materials · Misc**
- Mobs split by biome sub-tabs (Meadows → Ashlands, Bosses, …)
- Items tiered by use-case / progression
- Bare `#alias` commands ready for Twitch chat
- Press Start 2P (P2P) retro type · blue theme
- Square icons from the [Valheim wiki](https://valheim.weirdgloop.org/) (64×64 PNGs)
- Search across name / command / prefab / description

## Local preview

```bash
cd Valheim_TwitchIntegration
python3 -m http.server 8080
```

Then visit http://localhost:8080

## Rebuild catalog + icons

Catalog source: `ZZ_Heim-Heim/docs/prefab-catalog.json`

```bash
python3 tools/build-store.py
```

Writes:

- `js/commands-data.js` — full store
- `assets/icons/*.png` — wiki icons
- `assets/icon-map.json` — prefab → icon path

## Enable GitHub Pages

1. Repo **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / folder: `/ (root)`
4. Save — site appears at the URL above in a minute or two

## Update catalog

Re-run `tools/build-store.py` after Heim-Heim catalog changes, commit, push to `main`.

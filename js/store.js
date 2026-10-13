(() => {
  const store = window.VALHEIM_TWITCH_STORE;
  if (!store) {
    console.error("Missing VALHEIM_TWITCH_STORE catalog");
    return;
  }

  const BIOME_ORDER = [
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
  ];

  const ICON_TABS = new Set([
    "quick",
    "mobs",
    "weapons",
    "armor",
    "food",
    "materials",
    "misc",
  ]);

  const tabs = Array.from(document.querySelectorAll(".tab"));
  const subtabsEl = document.getElementById("subtabs");
  const catalog = document.getElementById("catalog");
  const empty = document.getElementById("empty");
  const countLabel = document.getElementById("count-label");
  const search = document.getElementById("search");
  const toast = document.getElementById("toast");

  let activeTab = "quick";
  let activeBiome = null;
  let toastTimer = 0;
  let iconMap = {};

  function entriesFor(tab) {
    return Array.isArray(store[tab]) ? store[tab] : [];
  }

  function biomeSections(list) {
    const names = [];
    const seen = new Set();
    for (const e of list) {
      if (e.type === "section" && e.title && !seen.has(e.title)) {
        seen.add(e.title);
        names.push(e.title);
      }
    }
    const ordered = BIOME_ORDER.filter((b) => seen.has(b));
    for (const n of names) {
      if (!BIOME_ORDER.includes(n)) ordered.push(n);
    }
    return ordered;
  }

  function filterByBiome(list, biome) {
    if (!biome) return list;
    const out = [];
    let keep = false;
    for (const e of list) {
      if (e.type === "help") {
        out.push(e);
        continue;
      }
      if (e.type === "section") {
        keep = e.title === biome;
        if (keep) out.push(e);
        continue;
      }
      if (keep) out.push(e);
    }
    return out;
  }

  function matches(entry, q) {
    if (!q) return true;
    if (entry.type === "section") {
      return (entry.title || "").toLowerCase().includes(q);
    }
    if (entry.type === "help") {
      return (entry.text || "").toLowerCase().includes(q);
    }
    const hay = `${entry.name || ""} ${entry.cmd || ""} ${entry.desc || ""} ${entry.prefab || ""}`.toLowerCase();
    return hay.includes(q);
  }

  function showToast(message) {
    toast.hidden = false;
    toast.textContent = message;
    toast.classList.add("is-on");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toast.classList.remove("is-on");
    }, 1400);
  }

  async function copyText(text, button) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.left = "-9999px";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      document.body.removeChild(area);
    }
    button.classList.add("is-copied");
    button.textContent = "COPIED";
    showToast("Copied to clipboard");
    window.setTimeout(() => {
      button.classList.remove("is-copied");
      button.textContent = "COPY";
    }, 1200);
  }

  function iconPath(entry) {
    if (entry.prefab && iconMap[entry.prefab]) return iconMap[entry.prefab];
    if (entry.prefab) return `assets/icons/${entry.prefab}.png`;
    return null;
  }

  function makeIcon(entry) {
    const wrap = document.createElement("div");
    wrap.className = "icon";
    wrap.setAttribute("aria-hidden", "true");

    const src = iconPath(entry);
    if (!src) {
      wrap.classList.add("icon-missing");
      return wrap;
    }

    const img = document.createElement("img");
    img.className = "icon-img";
    img.src = src;
    img.width = 32;
    img.height = 32;
    img.alt = "";
    img.loading = "lazy";
    img.onerror = () => {
      wrap.classList.add("icon-missing");
      img.remove();
    };
    wrap.append(img);
    return wrap;
  }

  function renderHelp(entry) {
    const el = document.createElement("p");
    el.className = "help-line";
    el.textContent = entry.text;
    return el;
  }

  function renderSection(entry) {
    const el = document.createElement("h3");
    el.className = "section-title";
    el.textContent = entry.title;
    return el;
  }

  function fillCommandText(el, cmd) {
    const text = cmd || "";
    const re = /#|\[|\]/g;
    let last = 0;
    let match;
    while ((match = re.exec(text))) {
      if (match.index > last) {
        el.append(document.createTextNode(text.slice(last, match.index)));
      }
      const mark = document.createElement("span");
      mark.className = "cmd-mark";
      mark.textContent = match[0];
      el.append(mark);
      last = match.index + match[0].length;
    }
    if (last < text.length) {
      el.append(document.createTextNode(text.slice(last)));
    }
  }

  function renderRow(entry, inlineDesc, withIcon) {
    const row = document.createElement("article");
    row.className = withIcon ? "row row-icon" : "row";

    if (withIcon) {
      row.append(makeIcon(entry));
    }

    const main = document.createElement("div");
    main.className = "row-main";

    const name = document.createElement("h2");
    name.className = "row-name";
    name.textContent = entry.name;

    const cmdLine = document.createElement("p");
    cmdLine.className = "row-cmd";

    const cmd = document.createElement("span");
    cmd.className = "cmd-text";
    fillCommandText(cmd, entry.cmd);
    cmdLine.append(cmd);

    if (inlineDesc && entry.desc) {
      const desc = document.createElement("span");
      desc.className = "cmd-desc";
      desc.textContent = ` — ${entry.desc}`;
      cmdLine.append(desc);
    }

    main.append(name, cmdLine);

    if (!inlineDesc && entry.desc) {
      const desc = document.createElement("p");
      desc.className = "row-desc";
      desc.textContent = entry.desc;
      main.append(desc);
    }

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-btn";
    btn.textContent = "COPY";
    btn.setAttribute("aria-label", `Copy ${entry.cmd}`);
    btn.addEventListener("click", () => copyText(entry.cmd, btn));

    row.append(main, btn);
    return row;
  }

  function filterEntries(tab, q) {
    let all = entriesFor(tab);
    if (tab === "mobs" && !q) {
      all = filterByBiome(all, activeBiome);
    }
    if (!q) return all;
    // Searching: show all biomes, keep matching section headers near hits
    return all.filter((e) => {
      if (e.type === "help") return false;
      if (e.type === "section") {
        // keep section if any following entry until next section matches
        return true;
      }
      return matches(e, q);
    }).filter((e, i, arr) => {
      if (e.type !== "section") return true;
      // drop empty section headers under search
      for (let j = i + 1; j < arr.length; j++) {
        if (arr[j].type === "section") break;
        if (arr[j].type !== "help" && matches(arr[j], q)) return true;
      }
      return false;
    }).filter((e) => e.type === "section" || matches(e, q));
  }

  function renderSubtabs() {
    const isMobs = activeTab === "mobs";
    const q = (search.value || "").trim();
    subtabsEl.classList.toggle("hidden", !isMobs || !!q);
    document.body.classList.toggle("is-mobs-tab", isMobs);
    if (!isMobs) {
      subtabsEl.innerHTML = "";
      return;
    }

    const biomes = biomeSections(entriesFor("mobs"));
    if (!activeBiome || !biomes.includes(activeBiome)) {
      activeBiome = biomes[0] || null;
    }

    subtabsEl.innerHTML = "";
    for (const biome of biomes) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "subtab" + (biome === activeBiome ? " is-active" : "");
      btn.setAttribute("role", "tab");
      btn.setAttribute("aria-selected", biome === activeBiome ? "true" : "false");
      btn.dataset.biome = biome;
      btn.textContent = biome;
      btn.addEventListener("click", () => {
        activeBiome = biome;
        render();
      });
      subtabsEl.append(btn);
    }
  }

  function render() {
    renderSubtabs();
    const q = (search.value || "").trim().toLowerCase();
    const list = filterEntries(activeTab, q);
    catalog.innerHTML = "";

    const copyable = list.filter((e) => e.cmd);
    empty.classList.toggle("hidden", copyable.length > 0);
    countLabel.textContent = `${copyable.length} command${copyable.length === 1 ? "" : "s"}`;

    const frag = document.createDocumentFragment();
    const inlineDesc = activeTab === "quick";
    const withIcon = ICON_TABS.has(activeTab);

    for (const entry of list) {
      if (entry.type === "help") {
        // hide biome help when a subtab is active (less noise)
        if (activeTab === "mobs" && !q) continue;
        frag.append(renderHelp(entry));
        continue;
      }
      if (entry.type === "section") {
        // biome title already shown in subtab — skip duplicate under mobs
        if (activeTab === "mobs" && !q) continue;
        frag.append(renderSection(entry));
        continue;
      }
      frag.append(renderRow(entry, inlineDesc, withIcon));
    }
    catalog.append(frag);
  }

  function setTab(tab) {
    activeTab = tab;
    for (const el of tabs) {
      const on = el.dataset.tab === tab;
      el.classList.toggle("is-active", on);
      el.setAttribute("aria-selected", on ? "true" : "false");
    }
    render();
  }

  for (const el of tabs) {
    el.addEventListener("click", () => setTab(el.dataset.tab));
  }

  search.addEventListener("input", render);

  fetch("assets/icon-map.json")
    .then((r) => (r.ok ? r.json() : {}))
    .then((data) => {
      iconMap = data || {};
      setTab(activeTab);
    })
    .catch(() => {
      setTab(activeTab);
    });
})();

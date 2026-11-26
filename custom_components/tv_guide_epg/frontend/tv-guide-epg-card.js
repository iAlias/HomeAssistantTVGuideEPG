/**
 * TV Guide EPG card.
 * Finds the integration sensors by their canale/tipo attributes.
 */
class TvGuideEpgCard extends HTMLElement {
  constructor() {
    super();
    this._busy = false;
    this._last = null;
    this._hass = null;
    this._filter = "all";
    this._query = "";
  }

  static getStubConfig() {
    return {type: "custom:tv-guide-epg-card", title: "Guida TV"};
  }

  setConfig(cfg) {
    this._cfg = {
      show_refresh: true,
      show_timestamp: true,
      ...cfg,
    };
    if (this.card) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  _collect() {
    const byChannel = new Map();
    this._entityIds = [];
    for (const [entityId, state] of Object.entries(this._hass?.states || {})) {
      const a = state.attributes || {};
      if (!a.canale || !a.tipo) continue;
      if (this._cfg.nazione && a.nazione !== this._cfg.nazione) continue;
      if (this._cfg.channels && !this._cfg.channels.includes(a.canale)) continue;
      this._entityIds.push(entityId);
      if (!byChannel.has(a.canale)) byChannel.set(a.canale, {posizione: a.posizione ?? 999});
      byChannel.get(a.canale)[a.tipo] = {
        titolo: state.state,
        orario_inizio: a.orario_inizio,
        orario_fine: a.orario_fine,
        genere: a.genere,
        locandina: a.locandina,
        descrizione: a.descrizione,
        prossimi: Array.isArray(a.prossimi) ? a.prossimi : [],
      };
    }
    const channels = [...byChannel.entries()];
    if (this._cfg.channels) {
      channels.sort((a, b) => this._cfg.channels.indexOf(a[0]) - this._cfg.channels.indexOf(b[0]));
    } else {
      channels.sort((a, b) => a[1].posizione - b[1].posizione);
    }
    return channels;
  }

  _timeMinutes(value) {
    if (!/^\\d{2}:\\d{2}$/.test(value || "")) return null;
    const [h, m] = value.split(":").map(Number);
    return h * 60 + m;
  }

  _progress(info) {
    const start = this._timeMinutes(info?.orario_inizio);
    let end = this._timeMinutes(info?.orario_fine);
    if (start === null || end === null) return null;
    if (end <= start) end += 1440;
    const now = new Date();
    let current = now.getHours() * 60 + now.getMinutes();
    if (current < start && end > 1440) current += 1440;
    if (current < start || current > end) return null;
    return Math.max(0, Math.min(100, ((current - start) / (end - start)) * 100));
  }

  _poster(info) {
    if (!info?.locandina) return null;
    const img = this._el("img", "tvg-poster");
    img.alt = "";
    img.loading = "lazy";
    img.decoding = "async";
    img.referrerPolicy = "no-referrer";
    img.src = info.locandina;
    img.addEventListener("error", () => {
      img.remove();
    }, {once: true});
    return img;
  }

  _programRow(channel, info, kind) {
    const row = this._el("article", "tvg-row");
    const poster = this._poster(info);
    if (poster) row.appendChild(poster);
    const details = this._el("div", "tvg-details");
    const heading = this._el("div", "tvg-heading");
    heading.appendChild(this._el("strong", "tvg-channel", channel));
    heading.appendChild(this._el("span", "tvg-time", [
      info?.orario_inizio,
      info?.orario_fine
    ].filter(Boolean).join(" – ")));
    details.appendChild(heading);
    details.appendChild(this._el("div", "tvg-title", info?.titolo || "Nessun dato"));
    if (info?.genere) details.appendChild(this._el("div", "tvg-genre", info.genere));
    if (info?.descrizione) {
      const description = this._el("div", "tvg-description", info.descrizione);
      details.appendChild(description);
    }
    const progress = kind === "now" ? this._progress(info) : null;
    if (progress !== null) {
      const track = this._el("div", "tvg-progress");
      const fill = this._el("span", "tvg-progress-fill");
      fill.style.width = progress + "%";
      track.appendChild(fill);
      details.appendChild(track);
    }
    row.appendChild(details);
    if (kind === "now" && info?.prossimi?.length) {
      const upcoming = this._el("div", "tvg-upcoming");
      upcoming.appendChild(this._el("span", "tvg-upcoming-label", "A seguire"));
      for (const item of info.prossimi.slice(0, 3)) {
        const line = this._el("div", "tvg-upcoming-item");
        line.appendChild(this._el("time", "", item.orario_inizio || ""));
        line.appendChild(this._el("span", "", item.titolo || ""));
        upcoming.appendChild(line);
      }
      row.appendChild(upcoming);
    }
    return row;
  }

  _render() {
    if (!this._hass || !this._cfg) return;
    if (!this.card) {
      this.card = document.createElement("ha-card");
      const style = this._el("style");
      style.textContent = `
        .tvg-shell{padding:14px;display:grid;gap:12px;min-width:0}
        .tvg-toolbar{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
        .tvg-meta{font-size:.78rem;color:var(--secondary-text-color)}
        .tvg-btn{border:1px solid var(--primary-color);color:var(--primary-color);background:transparent;border-radius:18px;padding:6px 12px;cursor:pointer}
        .tvg-btn:disabled{opacity:.5;cursor:wait}
        .tvg-controls{display:flex;gap:8px;flex-wrap:wrap}
        .tvg-search{min-width:120px;flex:1;border:1px solid var(--divider-color);border-radius:8px;padding:8px;background:var(--card-background-color);color:var(--primary-text-color)}
        .tvg-tabs{display:flex;gap:6px;flex-wrap:wrap}
        .tvg-tab{border:1px solid var(--divider-color);background:transparent;color:var(--primary-text-color);padding:6px 10px;border-radius:16px;cursor:pointer}
        .tvg-tab[aria-pressed=true]{background:var(--primary-color);color:var(--text-primary-color,#fff);border-color:var(--primary-color)}
        .tvg-list{display:grid;gap:8px;min-width:0}
        .tvg-row{display:grid;grid-template-columns:48px minmax(0,1fr);gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--divider-color);min-width:0}
        .tvg-row:has(.tvg-upcoming){grid-template-columns:48px minmax(0,1fr)}
        .tvg-poster{width:48px;height:64px;object-fit:cover;border-radius:6px;background:var(--secondary-background-color)}
        .tvg-details{min-width:0;display:grid;gap:3px}
        .tvg-heading{display:flex;justify-content:space-between;gap:8px;min-width:0}
        .tvg-channel{font-size:.86rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .tvg-time,.tvg-genre,.tvg-description{font-size:.76rem;color:var(--secondary-text-color)}
        .tvg-title{font-weight:500;overflow-wrap:anywhere}
        .tvg-description{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
        .tvg-progress{height:3px;background:var(--divider-color);border-radius:3px;overflow:hidden;margin-top:3px}
        .tvg-progress-fill{display:block;height:100%;background:var(--primary-color)}
        .tvg-upcoming{grid-column:2;display:grid;gap:3px;padding-top:2px}
        .tvg-upcoming-label{font-size:.7rem;color:var(--secondary-text-color);text-transform:uppercase;letter-spacing:.04em}
        .tvg-upcoming-item{display:flex;gap:8px;font-size:.75rem;min-width:0}
        .tvg-upcoming-item time{color:var(--secondary-text-color);flex:none}
        .tvg-upcoming-item span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .tvg-empty{padding:12px;color:var(--secondary-text-color)}
        @media(min-width:650px){.tvg-row{grid-template-columns:56px minmax(0,1fr)}.tvg-poster{width:56px;height:74px}}
      `;
      this.toolbar = this._el("div", "tvg-toolbar");
      this.meta = this._el("div", "tvg-meta");
      this.btn = this._el("button", "tvg-btn", "Aggiorna");
      this.btn.type = "button";
      this.btn.addEventListener("click", () => this._refresh());
      this.toolbar.append(this.meta, this.btn);
      this.controls = this._el("div", "tvg-controls");
      this.search = this._el("input", "tvg-search");
      this.search.type = "search";
      this.search.placeholder = "Cerca canale o programma";
      this.search.addEventListener("input", () => { this._query = this.search.value.trim().toLocaleLowerCase(); this._renderContent(); });
      this.controls.appendChild(this.search);
      this.tabs = this._el("div", "tvg-tabs");
      [["all","Tutti"],["now","Ora in onda"],["upcoming","Prossimi"],["prime","Prima serata"]].forEach(([key,label]) => {
        const tab = this._el("button", "tvg-tab", label);
        tab.type = "button";
        tab.dataset.filter = key;
        tab.setAttribute("aria-pressed", String(this._filter === key));
        tab.addEventListener("click", () => { this._filter = key; this._renderContent(); });
        this.tabs.appendChild(tab);
      });
      this.controls.appendChild(this.tabs);
      this.content = this._el("div", "tvg-list");
      const shell = this._el("div", "tvg-shell");
      shell.append(this.toolbar, this.controls, this.content);
      this.card.append(style, shell);
      this.appendChild(this.card);
    }
    if (this._cfg.title) this.card.header = this._cfg.title;
    this.btn.style.display = this._cfg.show_refresh ? "" : "none";
    this.btn.disabled = this._busy;
    this.btn.textContent = this._busy ? "Aggiorno…" : (this._cfg.refresh_label || "Aggiorna");
    this.meta.textContent = this._cfg.show_timestamp
      ? "Ultimo aggiornamento: " + (this._last ? this._last.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}) : "non ancora aggiornato")
      : "";
    this._renderContent();
  }

  _renderContent() {
    if (!this.content || !this._hass) return;
    const channels = this._collect();
    this.tabs?.querySelectorAll("button").forEach(tab => tab.setAttribute("aria-pressed", String(tab.dataset.filter === this._filter)));
    this.content.replaceChildren();
    if (!channels.length) {
      this.content.appendChild(this._el("div", "tvg-empty", "Nessun sensore TV Guide EPG trovato."));
      return;
    }
    let count = 0;
    for (const [channel, data] of channels) {
      const now = data.ora_in_onda;
      const prime = data.prima_serata;
      const haystack = [channel, now?.titolo, prime?.titolo].join(" ").toLocaleLowerCase();
      if (this._query && !haystack.includes(this._query)) continue;
      const entries = [];
      if (this._filter === "all" || this._filter === "now") entries.push(["now", now]);
      if (this._filter === "all" || this._filter === "upcoming") {
        if (now?.prossimi?.length) entries.push(["upcoming", {...now, titolo:"Programmi in arrivo"}]);
      }
      if (this._filter === "all" || this._filter === "prime") entries.push(["prime", prime]);
      for (const [kind, info] of entries) {
        if (kind === "upcoming") {
          for (const item of info.prossimi) {
            this.content.appendChild(this._programRow(channel, item, "upcoming"));
            count++;
          }
        } else {
          this.content.appendChild(this._programRow(channel, info, kind));
          count++;
        }
      }
    }
    if (!count) this.content.appendChild(this._el("div", "tvg-empty", "Nessun programma corrisponde al filtro."));
  }

  async _refresh() {
    if (this._busy || !this._entityIds?.length || !this._hass) return;
    this._busy = true;
    this._render();
    try {
      await this._hass.callService("homeassistant", "update_entity", {entity_id: this._entityIds});
      this._last = new Date();
    } catch (err) {
      console.error("TV Guide EPG: aggiornamento non riuscito", err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  getCardSize() { return 5; }
}

if (!customElements.get("tv-guide-epg-card")) {
  customElements.define("tv-guide-epg-card", TvGuideEpgCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "tv-guide-epg-card")) {
  window.customCards.push({
    type: "custom:tv-guide-epg-card",
    name: "Guida TV EPG",
    description: "Guida TV con programmi in onda, prossimi programmi e prima serata.",
    preview: true,
    documentationURL: "https://github.com/iAlias/HomeAssistantTVGuideEPG",
  });
}

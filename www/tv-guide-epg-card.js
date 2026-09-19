class TvGuideEpgCard extends HTMLElement {
  constructor(){
    super();
    this._busy = false;
    this._last = null;
  }

  setConfig(cfg){
    if(!cfg.now_entity || !cfg.prime_entity){
      throw new Error("now_entity e prime_entity obbligatori");
    }
    this._cfg = {
      show_refresh: true,
      refresh_label: "Aggiorna",
      show_timestamp: true,
      ...cfg,
    };
  }

  _escapeAttr(str){
    return String(str).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;");
  }

  set hass(hass){
    const c = this._cfg;

    if(!this.card){
      this.card = document.createElement("ha-card");
      if(c.title) this.card.header = c.title;

      const style = document.createElement("style");
      style.textContent = `
        .tvg-body{padding:16px;display:grid;row-gap:16px}
        .tvg-toolbar{display:flex;justify-content:space-between;align-items:center;padding:8px 16px;border-bottom:1px solid var(--divider-color)}
        .tvg-btn{padding:.35rem .75rem;border:1px solid var(--primary-color);background:transparent;border-radius:999px;cursor:pointer}
        .tvg-btn[disabled]{opacity:.6;cursor:not-allowed}
        .tvg-meta{font-size:.85rem;opacity:.75}
        h3{margin:0 0 8px;font-size:1rem;font-weight:500}
        ul{list-style:none;margin:0;padding:0}
        li{display:flex;justify-content:space-between;align-items:center;gap:8px;border-bottom:1px solid var(--divider-color);padding:4px 0}
        .tvg-ch{display:flex;align-items:center;gap:8px;overflow:hidden}
        .tvg-poster{width:28px;height:28px;border-radius:4px;object-fit:cover;flex:none;background:var(--divider-color)}
        .tvg-ch-text{display:flex;flex-direction:column;overflow:hidden}
        .tvg-ch-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .tvg-ch-meta{font-size:.75rem;opacity:.65;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .val{font-weight:500;max-width:55%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      `;
      this.card.appendChild(style);

      this.toolbar = document.createElement("div");
      this.toolbar.className = "tvg-toolbar";
      this.btn = document.createElement("button");
      this.btn.className = "tvg-btn";
      this.btn.addEventListener("click", () => this._refresh(hass));
      this.meta = document.createElement("div");
      this.meta.className = "tvg-meta";
      this.toolbar.appendChild(this.meta);
      this.toolbar.appendChild(this.btn);
      this.card.appendChild(this.toolbar);

      this.container = document.createElement("div");
      this.container.className = "tvg-body";
      this.card.appendChild(this.container);

      this.appendChild(this.card);
    }

    const nowMap   = hass.states[c.now_entity]?.attributes.programmi_correnti || {};
    const primeMap = hass.states[c.prime_entity]?.attributes.prima_serata    || {};

    const channels = c.channels || Array.from(new Set([
      ...Object.keys(nowMap), ...Object.keys(primeMap)
    ]));

    const section = (label, map) => {
      let html = `<h3>${label}</h3><ul>`;
      channels.forEach(ch => {
        const info = map[ch];
        const title = info?.titolo ?? "—";
        const v = title.length > 60 ? title.slice(0,57)+"…" : title;
        const orario = info?.orario_inizio && info?.orario_fine
          ? `${info.orario_inizio}–${info.orario_fine}`
          : (info?.orario_inizio || "");
        const metaLine = [orario, info?.genere].filter(Boolean).join(" · ");
        const poster = info?.locandina
          ? `<img class="tvg-poster" src="${this._escapeAttr(info.locandina)}" alt="" loading="lazy">`
          : "";
        const tooltip = info?.descrizione ? ` title="${this._escapeAttr(info.descrizione)}"` : "";
        html += `<li${tooltip}>
          <span class="tvg-ch">${poster}<span class="tvg-ch-text"><span class="tvg-ch-name">${ch}</span>${metaLine ? `<span class="tvg-ch-meta">${metaLine}</span>` : ""}</span></span>
          <span class="val">${v}</span>
        </li>`;
      });
      return html + "</ul>";
    };

    this.container.innerHTML =
      section("Ora in onda", nowMap) + section("Prima serata", primeMap);

    const ts = this._last
      ? this._last.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"})
      : "mai";
    this.meta.textContent = c.show_timestamp ? `Ultimo aggiornamento: ${ts}` : "";
    if(c.show_refresh){
      this.btn.style.display = "";
      this.btn.textContent = this._busy ? "Aggiorno…" : (c.refresh_label || "Aggiorna");
      this.btn.disabled = this._busy;
    }else{
      this.btn.style.display = "none";
    }
  }

  async _refresh(hass){
    const ids = [this._cfg.now_entity, this._cfg.prime_entity].filter(Boolean);
    this._busy = true;
    this.hass = hass;
    try{
      await hass.callService("homeassistant","update_entity",{entity_id: ids});
      setTimeout(()=>{
        this._busy = false;
        this._last = new Date();
        this.hass = hass;
      }, 1200);
    }catch(e){
      this._busy = false;
      this.hass = hass;
      console.error("Aggiornamento palinsesto fallito:", e);
    }
  }

  getCardSize(){ return 3; }
}

customElements.define("tv-guide-epg-card", TvGuideEpgCard);

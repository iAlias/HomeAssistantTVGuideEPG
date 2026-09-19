/**
 * TV Guide EPG card.
 *
 * Reads the per-channel sensors the integration creates. Those are the only
 * entities carrying both a `canale` and a `tipo` attribute, so the card finds
 * them itself and needs no entity configuration at all. Optional config:
 *
 *   type: custom:tv-guide-epg-card
 *   title: Guida TV          # optional
 *   nazione: IT              # optional, needed only with several countries
 *   channels: [Rai 1, Rai 2] # optional, restricts and orders the channels
 */
class TvGuideEpgCard extends HTMLElement {
  constructor(){
    super();
    this._busy = false;
    this._last = null;
  }

  /** Config used when the card is added from the dashboard picker. */
  static getStubConfig(){
    return {type: "custom:tv-guide-epg-card", title: "Guida TV"};
  }

  setConfig(cfg){
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

  /** Group this integration's sensors by channel: {channel: {posizione, ora_in_onda, prima_serata}} */
  _collect(hass){
    const c = this._cfg;
    const byChannel = new Map();
    this._entityIds = [];

    for(const [entityId, st] of Object.entries(hass.states)){
      const a = st.attributes;
      if(!a || !a.canale || !a.tipo) continue;
      if(c.nazione && a.nazione !== c.nazione) continue;
      if(c.channels && !c.channels.includes(a.canale)) continue;

      this._entityIds.push(entityId);
      if(!byChannel.has(a.canale)){
        byChannel.set(a.canale, {posizione: a.posizione ?? 999});
      }
      byChannel.get(a.canale)[a.tipo] = {
        titolo: st.state,
        orario_inizio: a.orario_inizio,
        orario_fine: a.orario_fine,
        genere: a.genere,
        locandina: a.locandina,
        descrizione: a.descrizione,
      };
    }

    let channels = [...byChannel.entries()];
    if(c.channels){
      channels.sort((x,y) => c.channels.indexOf(x[0]) - c.channels.indexOf(y[0]));
    }else{
      channels.sort((x,y) => x[1].posizione - y[1].posizione);
    }
    return channels;
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
        .tvg-empty{padding:16px;opacity:.7}
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

    const channels = this._collect(hass);

    if(channels.length === 0){
      this.container.innerHTML =
        `<div class="tvg-empty">Nessun sensore di TV Guide EPG trovato.` +
        (c.nazione ? ` Nessuna istanza per la nazione "${c.nazione}".` : "") +
        `</div>`;
    }else{
      const section = (label, tipo) => {
        let html = `<h3>${label}</h3><ul>`;
        for(const [channel, data] of channels){
          const info = data[tipo];
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
            <span class="tvg-ch">${poster}<span class="tvg-ch-text"><span class="tvg-ch-name">${channel}</span>${metaLine ? `<span class="tvg-ch-meta">${metaLine}</span>` : ""}</span></span>
            <span class="val">${v}</span>
          </li>`;
        }
        return html + "</ul>";
      };

      this.container.innerHTML =
        section("Ora in onda", "ora_in_onda") + section("Prima serata", "prima_serata");
    }

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
    if(!this._entityIds || this._entityIds.length === 0) return;
    this._busy = true;
    this.hass = hass;
    try{
      await hass.callService("homeassistant","update_entity",{entity_id: this._entityIds});
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

// The integration ships and auto-loads this file, but someone upgrading from a
// version where the card was a manual /local/ resource may still have it loaded
// twice: defining the same element again throws and would break the page.
if(!customElements.get("tv-guide-epg-card")){
  customElements.define("tv-guide-epg-card", TvGuideEpgCard);
}

// Without this the card never shows up under "Add card", so it looks as though
// a guide has to be assembled entity by entity from a generic entities card.
window.customCards = window.customCards || [];
if(!window.customCards.some((card) => card.type === "tv-guide-epg-card")){
  window.customCards.push({
    type: "tv-guide-epg-card",
    name: "Guida TV EPG",
    description: "Palinsesto completo: cosa c'è ora in onda e in prima serata su ogni canale. Nessuna configurazione richiesta.",
    preview: true,
    documentationURL: "https://github.com/iAlias/HomeAssistantTVGuideEPG",
  });
}

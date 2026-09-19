# TV Guide EPG — design

Data: 2026-09-19
Stato: approvato dall'utente per sezioni, in attesa di revisione finale del documento

## Obiettivo

Nuova integrazione Home Assistant (`tv_guide_epg`), progetto indipendente basato sull'esperienza
di `Home-Assistant-TV-Guide` (`tv_guide_multi`), che porta il palinsesto TV di **più nazioni**
dentro Home Assistant. L'utente sceglie la nazione in fase di aggiunta dell'integrazione e vede
solo i sensori/la guida di quella nazione. Si possono aggiungere più istanze (una per nazione) per
seguire più palinsesti in parallelo.

## Scope del lancio (v1)

5 nazioni curate e verificate, non "tutte le nazioni del mondo" fin da subito:

| Codice | Nazione | Fonte | Tipo |
|---|---|---|---|
| IT | Italia | sorrisi.com | scraping HTML dedicato (`SorrisiSource`, portato da `tv_guide_multi`) |
| UK | Regno Unito | epgshare01.online (tag `UK1`) | XMLTV generico (`XmltvSource`) |
| DE | Germania | epgshare01.online (tag `DE1`) | XMLTV generico (`XmltvSource`) |
| FR | Francia | epgshare01.online (tag `FR1`) | XMLTV generico (`XmltvSource`) |
| ES | Spagna | epgshare01.online (tag `ES1`) | XMLTV generico (`XmltvSource`) |

L'architettura (interfaccia `ScheduleSource` + registro `countries.py`) è pensata per aggiungere
altre nazioni in seguito, una alla volta, ciascuna con le proprie fixture/test — non è necessario
implementarle tutte ora.

### Perché epgshare01.online

Verificato attivamente il 2026-09-19: servizio gratuito "per uso legale" (dichiarato sul sito),
serve file XMLTV via Cloudflare (`https://epgshare01.online/epgshare01/epg_ripper_<TAG>.xml.gz`),
aggiornati nelle ultime ore al momento del controllo, con cache 4 ore lato server. File UK
scaricato e ispezionato: 41.362 elementi `<programme>`, canali principali presenti (BBC One,
ITV1 HD, Channel 4 HD, Channel 5...), struttura standard con `title`, `sub-title`, `desc`,
`category`, `icon`, `start`/`stop`. Raggiungibilità confermata anche per DE1/FR1/ES1.

Contrasta con la fonte scartata la notte precedente (un mirror di terze parti che non rispondeva
affatto) — qui la fonte è stata scaricata, aperta e ispezionata realmente prima di essere scelta.

## Struttura del progetto

```
custom_components/tv_guide_epg/
├── __init__.py          # setup/unload config entry
├── manifest.json         # domain tv_guide_epg, config_flow: true
├── const.py              # DOMAIN, chiavi opzioni
├── config_flow.py        # step "user": scelta nazione + nome; options flow: preferiti + intervallo
├── coordinator.py        # DataUpdateCoordinator + fallback su dati validi (stesso pattern di tv_guide_multi)
├── countries.py          # registro nazione -> configurazione
├── sources/
│   ├── base.py            # ScheduleSource (interfaccia)
│   ├── sorrisi.py          # SorrisiSource (Italia, portato da tv_guide_multi/sources.py)
│   └── xmltv.py            # XmltvSource generica (UK/DE/FR/ES)
├── favorites.py           # logica preferiti (portata da tv_guide_multi)
├── sensor.py
├── binary_sensor.py
├── strings.json + translations/{it,en}.json
└── brand/
www/tv-guide-epg-card.js   # card Lovelace (adattata da tv-guide-multi-card.js)
tests/
├── conftest.py             # stub HA minimi + package sintetico (stessa tecnica di tv_guide_multi)
├── fixtures/
│   ├── sorrisi/ora_in_onda.html, prima_serata.html   # pagine reali intere (come oggi)
│   └── xmltv/uk_excerpt.xml, de_excerpt.xml, ...      # ESTRATTI (pochi canali/poche ore), non il
│                                                        # dump completo multi-MB: irrealistico da
│                                                        # tenere in un repository git
└── test_*.py
hacs.json
requirements_test.txt
.github/workflows/validate.yml   # hassfest + hacs + pytest
README.md + README.it.md
LICENSE (MIT, come tv_guide_multi)
```

## `ScheduleSource` e sorgenti concrete

Interfaccia invariata rispetto a `tv_guide_multi`:

```python
class ScheduleSource(ABC):
    @property
    @abstractmethod
    def refresh_interval(self) -> timedelta: ...

    @abstractmethod
    async def get_schedules(self) -> Tuple[Schedule, Schedule]:
        """Ritorna (ora_in_onda, prima_serata)."""
```

`refresh_interval` è nuovo rispetto a `tv_guide_multi` (lì era fisso sul coordinator): qui varia
per sorgente, quindi il coordinator lo legge dalla source passata al costruttore.

### `SorrisiSource` (IT)

Portata quasi identica da `tv_guide_multi/sources.py`: stesse due pagine "ora in tv"/"stasera in
tv" già filtrate dalla fonte, `refresh_interval = timedelta(minutes=10)`.

### `XmltvSource` (UK/DE/FR/ES)

```python
class XmltvSource(ScheduleSource):
    def __init__(self, session, *, url: str, channel_order: list[str], refresh_minutes: int = 120):
        ...

    @property
    def refresh_interval(self) -> timedelta:
        return timedelta(minutes=self._refresh_minutes)

    async def get_schedules(self) -> Tuple[Schedule, Schedule]:
        raw_gzip = await self._fetch(self._url)
        xml_bytes = gzip.decompress(raw_gzip)
        programmes_by_channel = _parse_xmltv(xml_bytes, wanted_channels=self._channel_order)
        now = _current_time_utc()
        return (
            _programme_on_air(programmes_by_channel, now),
            _programme_nearest(programmes_by_channel, target_hour=21),
        )
```

A differenza di sorrisi.com, la fonte pubblica **l'intero palinsesto del giorno**, non pagine già
filtrate: `XmltvSource` scarica una volta, e calcola localmente (pure logic, testabile con un
orario iniettato) quale programma è "in onda ora" (orario corrente tra `start` e `stop`) e quale è
di "prima serata", per ciascun canale in `channel_order`.

Dettagli che evitano ambiguità in fase di implementazione:
- **Correzione rispetto al design iniziale (applicata in implementazione).** L'idea iniziale era di
  usare l'offset pubblicato dalla fonte così com'è. La verifica sui file reali l'ha smentita: il
  feed UK pubblica `+0000` tutto l'anno (un'ora indietro rispetto all'ora civile britannica
  d'estate) e quello spagnolo mischia `+0200` e `+0000`. Ogni nazione dichiara quindi il proprio
  **fuso civile IANA** (`Europe/London`, `Europe/Berlin`, `Europe/Paris`, `Europe/Madrid`), usato
  sia per mostrare gli orari sia per individuare la prima serata; se il database dei fusi non è
  disponibile si ricade sull'offset della fonte. Senza questa correzione la prima serata spagnola
  cadeva alle 23:00 locali.
- I feed contengono voci a **durata zero** (`start == stop`: 541 nel file spagnolo, 104 in quello
  francese): non possono mai risultare "in onda" e sporcherebbero la scelta della prima serata,
  quindi vengono scartate in fase di parsing.
- "Prima serata" è semplificata a un orario fisso, le **21:00** nell'offset della fonte, uguale per
  tutte le nazioni — una semplificazione nota (la prima serata "reale" varia per paese, es. più
  tardi in Spagna), accettabile per la v1 e facile da rendere configurabile in futuro se serve.

Mappatura campi XMLTV -> schema interno:

| XMLTV | Schema interno |
|---|---|
| `title` | `titolo` |
| `start`/`stop` | `orario_inizio`/`orario_fine` |
| `category` (primo valore) | `genere` |
| `icon` (del programme, se presente) | `locandina` |
| `desc` | `descrizione` |

Campi assenti nella fonte restano `None`, stesso comportamento già in uso per sorrisi.com. Parsing
XML con `xml.etree.ElementTree` (libreria standard, nessuna nuova dipendenza); decompressione con
il modulo standard `gzip`.

## `countries.py`

Registro leggero, nessuna duplicazione di logica di ordinamento/esclusione canali (resta dentro
ciascuna sorgente):

```python
@dataclass(frozen=True)
class CountryConfig:
    name: str
    make_source: Callable[[ClientSession, int | None], ScheduleSource]  # int = minuti intervallo, se configurabile
    configurable_interval: bool

COUNTRIES: dict[str, CountryConfig] = {
    "IT": CountryConfig(
        name="Italia",
        make_source=lambda session, _minutes: SorrisiSource(session),
        configurable_interval=False,
    ),
    "UK": CountryConfig(
        name="Regno Unito",
        make_source=lambda session, minutes: XmltvSource(
            session,
            url="https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
            channel_order=["BBC.One.Lon.HD.uk", "BBC.Two.HD.uk", "ITV1.HD.uk", "Channel.4.HD.uk", "Channel.5.uk"],
            refresh_minutes=minutes or 120,
        ),
        configurable_interval=True,
    ),
    "DE": CountryConfig(
        name="Germania",
        make_source=lambda session, minutes: XmltvSource(
            session,
            url="https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz",
            channel_order=["Das.Erste.de", "ZDF.de", "RTL.de", "ProSieben.de"],
            refresh_minutes=minutes or 120,
        ),
        configurable_interval=True,
    ),
    "FR": CountryConfig(
        name="Francia",
        make_source=lambda session, minutes: XmltvSource(
            session,
            url="https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz",
            channel_order=["TF1.fr", "France.2.fr", "M6.fr"],
            refresh_minutes=minutes or 120,
        ),
        configurable_interval=True,
    ),
    "ES": CountryConfig(
        name="Spagna",
        make_source=lambda session, minutes: XmltvSource(
            session,
            url="https://epgshare01.online/epgshare01/epg_ripper_ES1.xml.gz",
            channel_order=["La.1.es", "Antena.3.es", "Telecinco.es", "laSexta.es"],
            refresh_minutes=minutes or 120,
        ),
        configurable_interval=True,
    ),
}
```

Tutti gli ID canale sopra sono stati verificati scaricando davvero i file il 2026-09-19, non
indovinati.

## Config flow

**Step "user"** (creazione istanza):
- `nazione`: `vol.In({code: cfg.name for code, cfg in COUNTRIES.items()})`
- `nome`: opzionale, default "Guida TV" (prefisso entità)
- `unique_id = f"{DOMAIN}_{nazione.lower()}"` — permette un'istanza per nazione; se già configurata,
  `_abort_if_unique_id_configured()`.

**Options flow** ("Configura", editabile in ogni momento):
- `preferiti`: stringa CSV di titoli (parziali), stesso comportamento di `tv_guide_multi`.
- `intervallo_aggiornamento`: **solo se `COUNTRIES[nazione].configurable_interval` è vero** —
  `vol.In({30: "30 minuti", 60: "1 ora", 120: "2 ore (consigliato)", 240: "4 ore"})`, default 120.
  Per l'Italia questo campo non compare (intervallo fisso a 10 minuti, come oggi).
- Cambiare `intervallo_aggiornamento` ricarica l'entry (stesso `add_update_listener` già usato per
  i preferiti in `tv_guide_multi`), così il coordinator viene ricreato con il nuovo intervallo.

## Coordinator

Stesso pattern di `tv_guide_multi/coordinator.py` (fallback sull'ultimo palinsesto valido quando un
refresh torna vuoto), con `update_interval` preso da `source.refresh_interval` invece di essere
fisso:

```python
class EpgCoordinator(DataUpdateCoordinator[Tuple[Schedule, Schedule]]):
    def __init__(self, hass, source: ScheduleSource) -> None:
        super().__init__(hass, _LOGGER, name="TV Guide EPG", update_interval=source.refresh_interval)
        self._source = source
    # _async_update_data identico a SorrisiCoordinator (stesso _merge_with_previous)
```

## Entità

Stessa ossatura di `tv_guide_multi`, con `unique_id` che include il codice nazione (necessario ora
che esistono più istanze):

| Entità | Stato | Attributi principali |
|---|---|---|
| `<nome> - Ora in onda` | programma del primo canale configurato | `programmi_correnti`, `nazione`, `fonte` |
| `<nome> - Prima serata` | programma serale del primo canale configurato | `prima_serata`, `nazione`, `fonte` |
| `In onda: <preferito>` (binary_sensor, uno per preferito) | acceso se in onda ora su questa istanza/nazione | `canali` |

Le **chiavi** degli attributi restano in italiano (coerenza con `tv_guide_multi` e il resto del
workspace); i **valori** (titoli, generi) sono nella lingua della nazione scelta.

`unique_id` esempi: `tvguide_epg_it_now`, `tvguide_epg_uk_favorite_the-office`.

## Test

Stessa tecnica di `tv_guide_multi/tests/conftest.py` (package sintetico `custom_components.tv_guide_epg`
registrato in `sys.modules`, stub minimi di `homeassistant.core`/`homeassistant.helpers.update_coordinator`).

- `test_sorrisi_source.py` — porta i test esistenti di `tv_guide_multi` (fixture HTML intere).
- `test_xmltv_source.py` — fixture **ritagliate** (2-3 canali, poche ore di programmazione) salvate
  a mano dai file reali scaricati durante la ricerca, non il dump multi-MB; verifica parsing,
  calcolo "in onda ora"/"prima serata" con un orario iniettato (no dipendenza dall'orologio di
  sistema nei test), gestione campi mancanti.
- `test_coordinator_fallback.py`, `test_favorites.py` — portati quasi identici da `tv_guide_multi`.

## Card

`www/tv-guide-epg-card.js`: stessa logica di rendering di `tv-guide-multi-card.js` (già mostra
titolo/orario/genere/locandina/descrizione); nessuna logica di scelta-nazione nella card, perché il
filtro nazione è già a monte, nell'integrazione. L'utente punta semplicemente `now_entity`/
`prime_entity` all'istanza/nazione che vuole mostrare in quella card.

## HACS / CI

- `manifest.json`: `domain: tv_guide_epg`, `config_flow: true`, `iot_class: cloud_polling`,
  `requirements`: `aiohttp`, `beautifulsoup4` (per `SorrisiSource`) — nessuna nuova dipendenza per
  `XmltvSource` (usa `gzip`/`xml.etree.ElementTree` della standard library.
- `hacs.json`: nessun `"country"` fisso (era `["IT"]` in `tv_guide_multi`), dato che copre più
  nazioni.
- `.github/workflows/validate.yml`: hassfest + hacs + job `pytest` (stesso schema di
  `tv_guide_multi`).

## Cose da sapere (per il README)

- epgshare01.online è un aggregatore gratuito di terze parti, non affiliato alle emittenti; se
  smette di funzionare o cambia formato, i test con fixture segnalano subito il problema.
- Come per `tv_guide_multi`: se una nazione smette di ricevere dati, il coordinator continua a
  servire l'ultimo palinsesto valido invece di andare subito a "Nessun dato".
- L'elenco nazioni cresce nel tempo; aggiungerne una richiede solo una nuova voce in
  `countries.py` (più eventualmente una nuova `ScheduleSource` se la fonte non parla XMLTV) e le
  relative fixture/test — nessuna modifica a coordinator, entità o card.

## Non-goal per questa v1

- Nessuna creazione di repository remoto GitHub (resta locale finché non richiesto esplicitamente).
- Nessuna copertura "tutte le nazioni del mondo": si parte con 5, si estende una alla volta.
- Nessuna traduzione dei *contenuti* (titoli/generi restano nella lingua originale della fonte);
  solo l'interfaccia (strings.json) è tradotta.

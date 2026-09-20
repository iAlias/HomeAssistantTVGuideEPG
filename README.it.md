<img src="custom_components/tv_guide_epg/brand/icon.png" width="96" alt="TV Guide EPG" align="right">

# TV Guide EPG

**Il palinsesto TV internazionale dentro Home Assistant — scegli la nazione quando aggiungi l'integrazione.**

[![Validate](https://github.com/iAlias/HomeAssistantTVGuideEPG/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/HomeAssistantTVGuideEPG/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.1%2B-41bdf5)](https://www.home-assistant.io/)
[![Versione](https://img.shields.io/badge/versione-2.1.2-orange)](custom_components/tv_guide_epg/manifest.json)
[![Licenza](https://img.shields.io/badge/licenza-MIT-green)](LICENSE)

🇬🇧 [Read in English](README.md)

Scegli la nazione quando aggiungi l'integrazione, e puoi aggiungerla di nuovo per una
seconda. L'Italia è servita da uno scraper dedicato, in uso dal 2025; le altre nazioni condividono
un unico lettore XMLTV generico. Ogni istanza espone sensori "ora in onda" e "prima serata",
sensori binari opzionali sui programmi preferiti, e una card Lovelace che li mostra come una guida
vera. La card si installa insieme all'integrazione e si registra da sola nel selettore
**Aggiungi card**.

---

## Indice

- [Nazioni supportate](#nazioni-supportate)
- [Cosa installa](#cosa-installa)
- [Installazione](#installazione)
- [Configurazione della card](#configurazione-della-card)
- [Programmi preferiti](#programmi-preferiti)
- [Come funziona](#come-funziona)
- [Cose da sapere](#cose-da-sapere)
- [Sviluppo](#sviluppo)
- [Requisiti](#requisiti)
- [Licenza](#licenza)

---

## Nazioni supportate

| Nazione | Fonte | Canali inclusi di default |
|---|---|---|
| Italia | sorrisi.com | Rai 1, Rai 2, Rai 3, Rete 4, Canale 5, Italia 1, La7, TV8, NOVE |
| Regno Unito | epgshare01.online (XMLTV) | BBC One, BBC Two, ITV1, Channel 4, Channel 5 |
| Germania | epgshare01.online (XMLTV) | Das Erste, ZDF, RTL, SAT.1, ProSieben, VOX |
| Francia | epgshare01.online (XMLTV) | TF1, France 2, France 3, France 5, M6, Arte |
| Spagna | epgshare01.online (XMLTV) | La 1, La 2, Antena 3, Cuatro, Telecinco, laSexta |

Ogni canale sopra è stato verificato sul feed reale — gli identificativi presenti nel feed ma privi
di dati sono stati volutamente esclusi. Altre nazioni potranno essere aggiunte in seguito: vedi
[Cose da sapere](#cose-da-sapere).

## Cosa installa

**Due sensori per ogni canale**, così ogni canale è utilizzabile da solo in dashboard e automazioni:

| Entità | Stato | Attributi |
|---|---|---|
| `<canale> - Ora in onda` | titolo di cosa c'è ora su quel canale | `orario_inizio`, `orario_fine`, `genere`, `locandina`, `descrizione`, `canale`, `nazione`, `fonte`, `tipo`, `posizione` |
| `<canale> - Prima serata` | titolo del programma di prima serata di quel canale | gli stessi di sopra |
| `In onda: <preferito>` (uno per preferito configurato) | acceso se quel titolo è in onda ora, su uno dei canali dell'istanza | `canali`: dizionario canale → titolo |

Sono quindi **18 entità per l'Italia** (9 canali), 10 per il Regno Unito e 12 a testa per Germania,
Francia e Spagna, più una per ogni preferito. Un canale per cui la fonte non ha dati riporta
`Nessun dato`.

Le **chiavi** degli attributi sono in italiano per coerenza con gli altri progetti Home Assistant
dell'autore; i **valori** sono nella lingua della nazione scelta.

## Installazione

### 1. L'integrazione, con HACS

1. HACS → Integrazioni → menù in alto a destra → **Repository personalizzati**
2. Incolla `https://github.com/iAlias/HomeAssistantTVGuideEPG`, categoria **Integration**
3. Installa e riavvia Home Assistant
4. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione** → cerca **TV Guide EPG**
5. Scegli una nazione e conferma il nome (diventa il prefisso dei due sensori)

Aggiungi di nuovo l'integrazione per seguire una seconda nazione. Ogni nazione può essere aggiunta
una sola volta.

> **Aggiornamento dalla 1.x?** I due sensori aggregati (`<nome> - Ora in onda` e
> `<nome> - Prima serata`, che tenevano tutti i canali negli attributi) non esistono più, sostituiti
> da due sensori per canale. Elimina card o automazioni che li usavano, aggiorna la card alla
> configurazione qui sotto, e rimuovi le due entità orfane da
> **Impostazioni → Dispositivi e servizi → Entità**.

### 2. La card

La card viaggia dentro l'integrazione ed è Home Assistant stesso a servirla: appena configuri una
istanza, l'integrazione la registra come modulo frontend e **Guida TV EPG** compare in
**Aggiungi card** con l'anteprima. Niente da copiare in `config/www`, nessuna risorsa da aggiungere
a mano.

Se in passato avevi installato la card manualmente (una risorsa `/local/tv-guide-epg-card.js`
collegata a una copia in `config/www/`), elimina quella risorsa e il file: ora è superflua e
caricherebbe una versione vecchia della card.

Dopo l'aggiornamento ricarica il browser una volta con Ctrl+F5.

## Configurazione della card

```yaml
type: custom:tv-guide-epg-card
```

Questa è tutta la configurazione: la card trova da sola i sensori dell'integrazione (sono gli unici
con gli attributi `canale` e `tipo`) e ordina i canali secondo la numerazione nazionale. Tutto il
resto è opzionale:

```yaml
type: custom:tv-guide-epg-card
title: Guida TV
nazione: IT            # serve solo se hai installato più nazioni
channels:              # limita e riordina i canali mostrati
  - Rai 1
  - Rai 2
  - La7
```

## Programmi preferiti

Da **Impostazioni → Dispositivi e servizi → TV Guide EPG → Configura** puoi indicare titoli
preferiti (anche parziali, separati da virgola, es. `Report, Casualty`). Per ciascuno viene creato
un `binary_sensor` che si accende quando un programma che lo contiene è in onda su uno dei canali
di quell'istanza — comodo per un'automazione che ti avvisa quando inizia una serie che segui.

Nella stessa schermata scegli ogni quanto scaricare il palinsesto (30 minuti / 1 ora / 2 ore /
4 ore) per le nazioni basate su XMLTV. L'Italia non compare lì: interroga pagine leggere e già
filtrate ogni 10 minuti.

## Come funziona

- Fetch e parsing passano da un'interfaccia `ScheduleSource`
  (`custom_components/tv_guide_epg/sources/base.py`); `countries.py` mappa ogni nazione a una
  sorgente concreta, così aggiungere una nazione non tocca nient'altro.
- **L'Italia** usa `SorrisiSource`, portata da `tv_guide_multi`: legge due pagine già filtrate
  ("ora in tv" e "stasera in tv") ogni 10 minuti.
- **Regno Unito / Germania / Francia / Spagna** usano `XmltvSource`, che scarica il palinsesto
  dell'intera giornata (XMLTV, compresso gzip) da [epgshare01.online](https://epgshare01.online) —
  un aggregatore EPG gratuito per uso legale — e calcola localmente quale programma è in onda (la
  sua fascia oraria copre l'istante corrente) e quale è più vicino alle 21:00. Dato che questi file
  pesano diversi megabyte, l'intervallo di polling è configurabile e di default è 2 ore.
- Se un aggiornamento torna vuoto, per entrambi i tipi di sorgente, il coordinator continua a
  servire l'ultimo palinsesto letto con successo invece di collassare subito su `Nessun dato`.

## Cose da sapere

- **Due tipi di sorgente, un'unica interfaccia.** Aggiungere una nazione significa o riusare
  `XmltvSource` con un nuovo tag epgshare01.online e un elenco di canali, oppure scrivere una
  piccola `ScheduleSource` dedicata come `SorrisiSource` quando non esiste un feed utilizzabile —
  in entrambi i casi senza toccare coordinator, entità, card o config flow.
- **epgshare01.online è un aggregatore gratuito di terze parti**, non affiliato a nessuna
  emittente. Se una nazione smette di aggiornarsi, controlla prima il loro stato.
- **La prima serata è semplificata.** "Il programma più vicino alle 21:00" è la stessa regola per
  tutte le nazioni XMLTV nella v1, anche se la prima serata reale varia da paese a paese (più tardi
  in Spagna, prima in Germania). Facile da rendere configurabile in futuro.
- **Gli identificativi dei canali non sono indovinati.** Ogni canale di default è stato verificato
  sul feed reale: per esempio `Channel.5.uk` esiste ma è vuoto, quindi la lista UK usa
  `Channel.5.HD.uk`.

## Sviluppo

```bash
pip install -r requirements_test.txt
pytest -q
```

I test coprono il parsing HTML (Italia, su pagine reali intere), il parsing XMLTV e il calcolo di
ora-in-onda/prima-serata (su un estratto ritagliato, con un orario iniettato così il risultato non
dipende da quando gira la suite), la logica dei preferiti, il registro delle nazioni e il fallback
sui dati validi — nessuna installazione di Home Assistant richiesta.

## Requisiti

- Home Assistant **2025.1.0** o successivo
- Accesso internet in uscita verso `sorrisi.com` (Italia) e/o `epgshare01.online` (altre nazioni)
- [HACS](https://hacs.xyz/) (opzionale, per gli aggiornamenti con un clic) oppure installazione manuale

## Licenza

[MIT](LICENSE). I dati dei palinsesti appartengono alle rispettive emittenti e aggregatori; questa
integrazione li mostra per uso personale dentro la propria istanza di Home Assistant.

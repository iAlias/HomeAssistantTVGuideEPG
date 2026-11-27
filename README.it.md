<img src="custom_components/tv_guide_epg/brand/icon.png" width="96" alt="TV Guide EPG" align="right">

# TV Guide EPG

**Guida TV per Home Assistant, con scelta della fonte EPG per ogni scheda Lovelace.**

[![Validate](https://github.com/iAlias/HomeAssistantTVGuideEPG/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/HomeAssistantTVGuideEPG/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.1%2B-41bdf5)](https://www.home-assistant.io/)
[![Version](https://img.shields.io/badge/version-2.3.2-orange)](custom_components/tv_guide_epg/manifest.json)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[![Offrimi un caffè](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/ialias)

🇬🇧 [Read in English](README.md)

L'integrazione crea sensori Home Assistant per i programmi in onda e per la prima serata.
La card Lovelace include ricerca, filtri, avanzamento del programma, programmi successivi e
locandine quando la fonte le fornisce.

Per l'Italia puoi scegliere tra quattro fonti: **Sorrisi, IPTV-EPG.org, ZapprTV ed EPG Italia**.
Ogni fonte ha il proprio coordinator e i propri sensori. La scelta viene salvata nella singola
scheda: puoi quindi usare fonti diverse in due card contemporaneamente.

> **Stato della versione:** i feed dei provider e la copertura dei canali vanno ancora verificati
> in un'installazione Home Assistant reale.

---

## Indice

- [Paesi e fonti supportati](#paesi-e-fonti-supportati)
- [Sensori creati](#sensori-creati)
- [Installazione](#installazione)
- [Card Lovelace](#card-lovelace)
- [Programmi preferiti](#programmi-preferiti)
- [Funzionamento](#funzionamento)
- [Note sulle fonti](#note-sulle-fonti)
- [Sviluppo e test](#sviluppo-e-test)
- [Requisiti](#requisiti)
- [Licenza](#licenza)

---

## Paesi e fonti supportati

| Paese | Fonte | Implementazione |
|---|---|---|
| Italia | Sorrisi | Parser HTML già presente nel progetto |
| Italia | IPTV-EPG.org | Feed XMLTV, associazione tramite nome del canale |
| Italia | ZapprTV | Feed JSON aggregato e identificativi pubblicati per i canali |
| Italia | EPG Italia | Feed XMLTV, associazione tramite nome del canale |
| Regno Unito | epgshare01.online | XMLTV |
| Germania | epgshare01.online | XMLTV |
| Francia | epgshare01.online | XMLTV |
| Spagna | epgshare01.online | XMLTV |

Gli adapter XMLTV italiani riconoscono un gruppo di canali nazionali, tra cui Rai, Mediaset, LA7,
TV8, NOVE, Real Time, DMAX e Cielo. La disponibilità effettiva dipende dai nomi e dai programmi
presenti nel feed. ZapprTV usa una mappatura esplicita più ristretta e non include tutti i canali
previsti dagli adapter XMLTV.

Non è garantito che ogni fonte contenga tutti i canali o che ogni programma abbia descrizione e
locandina.

## Sensori creati

Per ogni canale e fonte vengono creati due sensori:

| Sensore | Stato | Attributi principali |
|---|---|---|
| `<canale> - Ora in onda` | Titolo del programma attualmente in onda | `orario_inizio`, `orario_fine`, `genere`, `locandina`, `descrizione`, `prossimi` |
| `<canale> - Prima serata` | Programma più vicino all'orario di prima serata | Gli stessi attributi del programma |

Ogni sensore espone anche `canale`, `nazione`, `fonte`, `source_id`, `tipo` e `posizione`.
Il campo `source_id` permette alla card di mostrare soltanto i sensori della fonte selezionata.

Sono disponibili anche sensori binary per i programmi preferiti. Per l'Italia monitorano la fonte
primaria, cioè Sorrisi.

## Installazione

### Home Assistant Marketplace (Home Assistant 2026.11 e successive)

1. Apri **Impostazioni → Marketplace**.
2. Seleziona **Aggiungi da link** in alto a destra.
3. Nel campo **Link GitHub**, inserisci `https://github.com/iAlias/HomeAssistantTVGuideEPG`.
4. Seleziona **Aggiungi**. Se Marketplace non riconosce il tipo, scegli **Integrazione** e aggiungi di nuovo.
5. Apri **TV Guide EPG** nell'elenco dei repository e seleziona **Installa**.
6. Segui la procedura di configurazione. Se Home Assistant richiede un riavvio, riavvia prima di completare la configurazione.

Per aggiungere un repository personalizzato devi collegare un account GitHub a Marketplace. Il repository deve essere pubblico e contenere il file `hacs.json` nella cartella principale.

### Installazioni precedenti con HACS (Home Assistant 2026.10 e precedenti)

1. Apri **HACS → Integrazioni → ⋮ → Repository personalizzati**.
2. Aggiungi `https://github.com/iAlias/HomeAssistantTVGuideEPG` con categoria **Integrazione**.
3. Installa l'integrazione e riavvia Home Assistant.
4. Vai in **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**.
5. Cerca **TV Guide EPG**, scegli il paese e completa la configurazione.


### Installazione manuale

Copia la cartella `custom_components/tv_guide_epg` in
`<config>/custom_components/tv_guide_epg`, quindi riavvia Home Assistant.

Dopo la configurazione, l'integrazione registra la card come modulo frontend. Non dovrebbe essere
necessario copiare il file JavaScript in `config/www` o aggiungere una risorsa manualmente.
Se in passato avevi aggiunto una risorsa manuale, rimuovi quella vecchia e ricarica il browser.

## Card Lovelace

Aggiungi **Guida TV EPG** dal selettore delle card Lovelace. Nell'editor visuale trovi il menu
**Fonte EPG**. La scelta resta salvata nella singola card: modificare la fonte di una scheda non
cambia quella delle altre.

Configurazione YAML minima:

```yaml
type: custom:tv-guide-epg-card
```

Esempio con alcune opzioni:

```yaml
type: custom:tv-guide-epg-card
title: Guida TV
nazione: IT
source_id: zappr
channels:
  - Rai 1
  - Rai 2
  - Canale 5
```

Valori disponibili per `source_id` in Italia:

| Fonte | Valore |
|---|---|
| Sorrisi | `sorrisi` |
| IPTV-EPG.org | `iptv_epg` |
| ZapprTV | `zappr` |
| EPG Italia | `epgitalia` |

Normalmente basta scegliere la fonte dall'editor visuale. Il menu mostra le fonti per cui
l'integrazione ha creato sensori in Home Assistant.

La card include:
- ricerca per canale o programma;
- filtri **Tutti**, **Ora in onda**, **Prossimi** e **Prima serata**;
- barra di avanzamento del programma;
- sequenza orizzontale dei programmi successivi;
- locandine, se disponibili, con immagine di fallback in caso di errore;
- aggiornamento manuale.

## Programmi preferiti

Apri **Impostazioni → Dispositivi e servizi → TV Guide EPG → Configura** e inserisci i titoli
preferiti. Sono accettate corrispondenze parziali; separa più titoli con la virgola.
Un sensore binary si attiva quando uno dei titoli è in onda su uno dei canali della fonte primaria.

Dalle opzioni puoi anche impostare l'intervallo di aggiornamento per le fonti che lo supportano.
Alcuni provider usano un intervallo fisso.

## Funzionamento

- Ogni provider implementa l'interfaccia `ScheduleSource`.
- Ogni fonte attiva ha un `EpgCoordinator` separato. Errori e dati memorizzati in cache non
  interferiscono con le altre fonti.
- La piattaforma sensori crea entità distinte per fonte e canale. Gli identificativi delle entità
  delle fonti aggiuntive includono il relativo identificativo; dove possibile vengono mantenuti
  quelli delle vecchie entità primarie.
- La card filtra i sensori tramite `source_id`. La selezione è indipendente per ogni scheda.
- Il servizio `tv_guide_epg.refresh` aggiorna le fonti configurate per il paese indicato; senza
  paese aggiorna tutte le istanze configurate.

## Note sulle fonti

- **Sorrisi:** il progetto mantiene il parser HTML già esistente. Le condizioni pubblicate dal sito
  limitano l'estrazione automatizzata e il riutilizzo dei contenuti. Prima di distribuire o usare
  questa fonte oltre gli usi personali consentiti, verifica le condizioni aggiornate e chiedi
  l'autorizzazione scritta al provider. La presenza del parser nel repository non equivale a
  un'autorizzazione.
- **IPTV-EPG.org ed EPG Italia:** gli adapter leggono feed XMLTV esterni e associano i canali
  usando una lista di nomi alternativi. Formato, raggiungibilità, nomi e copertura possono
  cambiare. Se un canale non viene riconosciuto, non avrà dati di programma.
- **ZapprTV:** l'adapter dipende dal feed JSON e dagli identificativi pubblicati dal progetto
  ZapprTV. I dati upstream possono cambiare indipendentemente da questa integrazione. La licenza
  del codice del progetto non concede automaticamente diritti su palinsesti, loghi o immagini
  upstream.
- **Dati e immagini:** palinsesti, descrizioni, locandine e loghi restano soggetti ai diritti e
  alle condizioni dei rispettivi provider. L'integrazione non ne rivendica la proprietà.
- **Gestione errori:** se una fonte non risponde o non restituisce dati utilizzabili, il suo
  coordinator prova a mantenere l'ultimo palinsesto valido. Non viene sostituita in automatico
  con un'altra fonte.

## Sviluppo e test

Installa le dipendenze di test ed esegui:

```bash
pip install -r requirements_test.txt
pytest -q
```

Questi test non sostituiscono una prova completa su Home Assistant. Prima di considerare una fonte
pronta per l'uso stabile, verifica dalla tua installazione l'endpoint live, il formato della
risposta, la copertura dei canali, gli orari e le immagini.

## Requisiti

- Home Assistant compatibile con la versione indicata nel manifest (2025.1.0 o successiva).
- Accesso HTTPS in uscita al provider EPG selezionato.
- HACS per l'installazione gestita, oppure installazione manuale.

## Licenza

Il codice dell'integrazione è distribuito con licenza [MIT](LICENSE). La licenza si applica al
codice di questo repository, non concede diritti su palinsesti, descrizioni, loghi, locandine o
altri contenuti di terze parti.

# TV Guide EPG

Guida TV per Home Assistant. Per l'Italia sono disponibili quattro fonti selezionabili per ogni scheda Lovelace: Sorrisi, IPTV-EPG.org, ZapprTV ed EPG Italia.

## Fonti italiane

- **Sorrisi**: parser HTML già presente nel progetto.
- **IPTV-EPG.org**: feed XMLTV compresso, abbinamento automatico dei canali tramite i nomi pubblicati nel feed.
- **ZapprTV**: feed JSON aggregato; usa gli identificativi pubblicati dalla lista nazionale Zappr per i canali Rai, Mediaset, LA7, Sky e Warner Bros. Discovery.
- **EPG Italia**: feed XMLTV, abbinamento automatico dei canali tramite i nomi pubblicati nel feed.

Le fonti sono scaricate da coordinator separati. Ogni fonte genera entità con un identificativo dedicato; le schede Lovelace filtrano i sensori usando il campo `source_id`. Due schede possono quindi usare provider diversi.

## Nota sui feed

La disponibilità, la copertura dei singoli canali e le condizioni d'uso dipendono dai rispettivi provider. In particolare, il codice di scraping Sorrisi resta disponibile per uso personale: prima di distribuire pubblicamente un pacchetto che lo utilizza, verifica le condizioni del sito e richiedi eventuali autorizzazioni.

## Installazione

Installare l'integrazione da HACS, riavviare Home Assistant e aggiungere TV Guide EPG. Nella scheda Lovelace scegliere **Modifica scheda**: il menu **Fonte EPG** mostra le fonti caricate dall'integrazione.

## Test

Eseguire `pip install -r requirements_test.txt` e `pytest -q` nella cartella del repository. Verificare inoltre le fonti nella propria installazione Home Assistant: i feed sono servizi esterni e la raggiungibilità può variare in base alla rete e alla regione.

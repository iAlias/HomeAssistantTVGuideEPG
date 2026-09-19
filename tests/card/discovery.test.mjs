/**
 * Tests for the card's entity discovery.
 *
 * The card takes no entity configuration: it finds the integration's sensors
 * by their `canale`/`tipo` attributes. That makes discovery the part most
 * worth testing — if it silently matched nothing, the card would render an
 * empty guide and look broken.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const cardSource = readFileSync(path.join(here, "..", "..", "www", "tv-guide-epg-card.js"), "utf8");

// Minimal browser surface the card touches at load time.
globalThis.HTMLElement = class {};
globalThis.customElements = { define() {} };
globalThis.window = globalThis;

const TvGuideEpgCard = new Function(`${cardSource}\nreturn TvGuideEpgCard;`)();

function sensor(canale, tipo, titolo, {nazione = "IT", posizione = 1, ...rest} = {}) {
  return {
    state: titolo,
    attributes: {canale, tipo, nazione, posizione, ...rest},
  };
}

/** Entities as the previous version created them: no canale/tipo. */
const LEGACY_AGGREGATE = {
  state: "Byd Music Awards",
  attributes: {programmi_correnti: {"Rai 1": {}}, nazione: "IT", fonte: "Italia"},
};

function collect(states, config = {}) {
  const card = new TvGuideEpgCard();
  card.setConfig({type: "custom:tv-guide-epg-card", ...config});
  return card._collect({states});
}

test("finds both sensors of every channel and orders them by channel number", () => {
  const channels = collect({
    "sensor.rai_2_ora_in_onda": sensor("Rai 2", "ora_in_onda", "N.C.I.S.", {posizione: 2}),
    "sensor.rai_2_prima_serata": sensor("Rai 2", "prima_serata", "N.C.I.S.", {posizione: 2}),
    "sensor.rai_1_ora_in_onda": sensor("Rai 1", "ora_in_onda", "Tg1", {posizione: 1}),
    "sensor.rai_1_prima_serata": sensor("Rai 1", "prima_serata", "Byd Music Awards", {posizione: 1}),
  });

  assert.deepEqual(channels.map(([name]) => name), ["Rai 1", "Rai 2"]);
  assert.equal(channels[0][1].ora_in_onda.titolo, "Tg1");
  assert.equal(channels[0][1].prima_serata.titolo, "Byd Music Awards");
});

test("ignores entities that are not ours, including v1 leftovers", () => {
  const channels = collect({
    "sensor.rai_1_ora_in_onda": sensor("Rai 1", "ora_in_onda", "Tg1"),
    "sensor.guida_tv_ora_in_onda": LEGACY_AGGREGATE,
    "sensor.temperatura_salotto": {state: "21.5", attributes: {unit_of_measurement: "°C"}},
    "light.cucina": {state: "on", attributes: {}},
  });

  assert.deepEqual(channels.map(([name]) => name), ["Rai 1"]);
});

test("shows every country at once when no country filter is given", () => {
  const channels = collect({
    "sensor.rai_1_ora_in_onda": sensor("Rai 1", "ora_in_onda", "Tg1", {nazione: "IT", posizione: 1}),
    "sensor.bbc_one_ora_in_onda": sensor("BBC One", "ora_in_onda", "Casualty", {nazione: "UK", posizione: 1}),
  });

  assert.equal(channels.length, 2);
});

test("narrows to one country when nazione is set", () => {
  const states = {
    "sensor.rai_1_ora_in_onda": sensor("Rai 1", "ora_in_onda", "Tg1", {nazione: "IT", posizione: 1}),
    "sensor.bbc_one_ora_in_onda": sensor("BBC One", "ora_in_onda", "Casualty", {nazione: "UK", posizione: 1}),
    "sensor.zdf_ora_in_onda": sensor("ZDF", "ora_in_onda", "heute", {nazione: "DE", posizione: 2}),
  };

  assert.deepEqual(collect(states, {nazione: "UK"}).map(([n]) => n), ["BBC One"]);
  assert.deepEqual(collect(states, {nazione: "DE"}).map(([n]) => n), ["ZDF"]);
});

test("channels option restricts and reorders", () => {
  const channels = collect({
    "sensor.rai_1_ora_in_onda": sensor("Rai 1", "ora_in_onda", "Tg1", {posizione: 1}),
    "sensor.rai_2_ora_in_onda": sensor("Rai 2", "ora_in_onda", "N.C.I.S.", {posizione: 2}),
    "sensor.la7_ora_in_onda": sensor("La7", "ora_in_onda", "In altre parole", {posizione: 7}),
  }, {channels: ["La7", "Rai 1"]});

  assert.deepEqual(channels.map(([name]) => name), ["La7", "Rai 1"]);
});

test("carries the programme details the card renders", () => {
  const [[, data]] = collect({
    "sensor.rai_1_ora_in_onda": sensor("Rai 1", "ora_in_onda", "Byd Music Awards", {
      orario_inizio: "21:30",
      orario_fine: "00:50",
      genere: "Spettacolo",
      locandina: "https://example.com/p.jpg",
      descrizione: "In diretta dall'Arena di Verona.",
    }),
  });

  assert.deepEqual(data.ora_in_onda, {
    titolo: "Byd Music Awards",
    orario_inizio: "21:30",
    orario_fine: "00:50",
    genere: "Spettacolo",
    locandina: "https://example.com/p.jpg",
    descrizione: "In diretta dall'Arena di Verona.",
  });
});

test("registers itself in the dashboard card picker", () => {
  assert.ok(
    (globalThis.window.customCards || []).some((c) => c.type === "tv-guide-epg-card"),
    "the card must appear under 'Add card', otherwise it can only be added as raw YAML",
  );
});

test("collects nothing when no matching entity exists", () => {
  assert.deepEqual(collect({"light.cucina": {state: "on", attributes: {}}}), []);
});

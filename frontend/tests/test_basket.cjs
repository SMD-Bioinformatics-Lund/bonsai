// Run from frontend/: node --test tests/test_basket.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");

// Only the DOM surface needed by the basket and group-view initialization.
class Element extends EventTarget {
  children = [];
  disabled = false;
  label = { textContent: "" };
  counter = { textContent: "" };
  badge = { hidden: false };
  set innerHTML(value) {
    this.html = value;
    this.children = [];
    this.counter.textContent = value.match(/data-test-id="samples-in-basket-counter">([^<]*)/)?.[1] ?? "";
  }
  get innerHTML() { return this.html ?? ""; }
  appendChild(child) { this.children.push(child); child.connectedCallback?.(); }
  querySelector(selector) {
    if (selector === "#sample-basket-counter") return this.counter;
    if (selector === "#sample-basket-badge") return this.badge;
    if (selector === "span") return this.label;
    return null;
  }
  querySelectorAll() { return []; }
}

const tick = () => new Promise(resolve => setImmediate(resolve));

async function setup(savedIds = []) {
  const storage = new Map([["basket_content", JSON.stringify(savedIds)]]);
  const ids = ["basket-content", "basket-counter-container", "clear-basket-btn", "basket-offcanvas",
    "add-to-basket-btn", "replace-basket-btn"];
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  const clusterButton = new Element(), clusterLink = new Element();
  const requests = [], clusters = [], toasts = [], selectionCallbacks = [];
  let selected = [];
  const table = {
    rows: () => ({ ids: () => ({ toArray: () => selected }) }),
    columns: { adjust() {} },
    on: (_events, callback) => selectionCallbacks.push(callback),
  };
  class DataTable { constructor() { return table; } }
  DataTable.Buttons = { jszip() {} };
  const document = {
    createElement: () => new Element(),
    getElementById: id => elements[id] ?? null,
    querySelector: selector => selector === "#basket-cluster-samples .btn" ? clusterButton
      : elements[selector.slice(1)] ?? null,
    querySelectorAll: selector => selector === "#basket-cluster-samples a" ? [clusterLink] : [],
  };
  const globals = {
    HTMLElement: Element, CustomEvent, Error, document, window: {},
    customElements: { define() {} }, baseUrl: "",
    localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
    console: { error() {} },
  };
  function load(relativePath, require = () => ({})) {
    const exports = {};
    const source = fs.readFileSync(path.join(__dirname, relativePath), "utf8");
    const js = ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
    }).outputText;
    vm.runInNewContext(js, { ...globals, exports, require });
    return exports;
  }
  const state = load("../web/js/core/state/basket-state.ts");
  const basket = load("../web/js/components/sample-basket.ts");
  const counter = load("../web/js/components/samples-basket-counter.ts");
  const tableController = load("../web/js/utils/table-controller.ts", name =>
    name === "datatables.net-bs5" ? DataTable : {});
  const api = {
    getUserInfo: async () => ({}),
    getSamplesDetails: query => new Promise((resolve, reject) => requests.push({ query, resolve, reject })),
  };
  const view = load("../web/js/views/groups-view/init.ts", () => ({
    ...state, ...basket, ...counter, ...tableController,
    createGroupViewApi: () => api,
    User: class { isAdmin = false; },
    initToast() {}, initTooltip() {},
    throwSmallToast: message => toasts.push(message),
    clusterSamples: (_element, sampleIds) => clusters.push(Array.from(sampleIds)),
  }));
  await view.initGroupView(null, "", "", "");
  const component = elements["basket-content"].children[0];
  return {
    requests, clusters, toasts, component, clusterButton,
    saved: () => JSON.parse(storage.get("basket_content")),
    count: () => Number(elements["basket-counter-container"].children[0].counter.textContent),
    cards: () => component.children.map(card => card.innerHTML.match(/<h6 id="([^"]+)"/)[1]),
    select(sampleIds) { selected = sampleIds; selectionCallbacks.forEach(callback => callback()); },
    add: () => elements["add-to-basket-btn"].onclick(),
    replace: () => elements["replace-basket-btn"].onclick(),
    clear: () => elements["clear-basket-btn"].onclick(),
    reopen: () => elements["basket-offcanvas"].dispatchEvent(new Event("show.bs.offcanvas")),
    cluster: () => clusterLink.onclick({ preventDefault() {} }),
    elements,
    async respond(index, sampleIds) {
      requests[index].resolve({ data: sampleIds.map(sample_id => ({ sample_id, sample_name: sample_id, assay: "test" })) });
      await tick();
    },
  };
}

test("mixed missing IDs are removed from storage and count before clustering", async () => {
  const valid = Array.from({ length: 16 }, (_, i) => `valid-${i}`);
  const h = await setup([...valid, ...Array.from({ length: 7 }, (_, i) => `missing-${i}`)]);
  assert.equal(h.clusterButton.disabled, true);
  h.cluster();
  assert.equal(h.clusters.length, 0);
  assert.equal(h.requests[0].query.limit, 0);
  await h.respond(0, valid);
  assert.deepEqual(h.saved(), valid);
  assert.equal(h.count(), 16);
  assert.equal(h.clusterButton.disabled, true);
  await h.respond(1, valid);
  assert.deepEqual(h.cards(), valid);
  assert.equal(h.clusterButton.disabled, false);
  h.cluster();
  assert.deepEqual(h.clusters, [valid]);
});

test("an entirely missing basket becomes empty and cannot cluster", async () => {
  const h = await setup(["missing-1", "missing-2"]);
  await h.respond(0, []);
  assert.deepEqual(h.saved(), []);
  assert.equal(h.count(), 0);
  assert.match(h.component.innerHTML, /Your basket is empty/);
  assert.equal(h.clusterButton.disabled, true);
  h.cluster();
  assert.equal(h.clusters.length, 0);
});

test("failed lookup preserves saved IDs, blocks clustering, and can be retried", async () => {
  const ids = ["a", "b"];
  const h = await setup(ids);
  h.requests[0].reject(new Error("API unavailable"));
  await tick();
  assert.deepEqual(h.saved(), ids);
  assert.equal(h.count(), 2);
  assert.match(h.component.innerHTML, /Could not load your basket/);
  h.cluster();
  assert.equal(h.clusters.length, 0);
  h.reopen();
  await h.respond(1, ids);
  assert.deepEqual(h.cards(), ids);
  assert.equal(h.clusterButton.disabled, false);
});

test("Add preserves older valid samples, deduplicates overlaps, and reports the actual addition", async () => {
  const h = await setup(["old", "overlap"]);
  h.select(["overlap", "new"]);
  h.add();
  assert.deepEqual(h.saved(), ["old", "overlap", "new"]);
  assert.equal(h.toasts.at(-1), "Added 1 sample; basket now contains 3.");
  await h.respond(1, ["old", "overlap", "new"]);
  await h.respond(0, []);
  assert.deepEqual(h.saved(), ["old", "overlap", "new"]);
  assert.deepEqual(h.cards(), ["old", "overlap", "new"]);
  assert.equal(h.count(), 3);
  h.cluster();
  assert.deepEqual(h.clusters, [["old", "overlap", "new"]]);
});

test("Replace persists only the new selection and ignores a late response for the old basket", async () => {
  const h = await setup(["old-1", "old-2"]);
  h.select(["new-1", "new-2"]);
  h.replace();
  assert.deepEqual(h.saved(), ["new-1", "new-2"]);
  assert.equal(h.toasts.at(-1), "Basket replaced: 2 samples.");
  assert.equal(h.requests.length, 2); // One initial load and one atomic replacement.
  await h.respond(1, ["new-1", "new-2"]);
  await h.respond(0, ["old-1", "old-2"]);
  assert.deepEqual(h.cards(), ["new-1", "new-2"]);
  assert.equal(h.count(), 2);
  h.cluster();
  assert.deepEqual(h.clusters, [["new-1", "new-2"]]);
});

test("clearing invalidates in-flight responses and cannot resurrect old cards", async () => {
  const h = await setup(["old-1", "old-2"]);
  h.clear();
  await h.respond(0, ["old-1", "old-2"]);
  assert.deepEqual(h.saved(), []);
  assert.deepEqual(h.cards(), []);
  assert.equal(h.count(), 0);
  assert.equal(h.clusterButton.disabled, true);
});

test("older errors cannot overwrite a newer successfully resolved basket", async () => {
  const h = await setup(["a", "b"]);
  h.reopen();
  await h.respond(1, ["a", "b"]);
  h.requests[0].reject(new Error("Old request failed"));
  await tick();
  assert.deepEqual(h.cards(), ["a", "b"]);
  assert.equal(h.clusterButton.disabled, false);
});

test("response IDs outside the request never appear in the basket or clustering input", async () => {
  const h = await setup(["a", "b"]);
  await h.respond(0, ["a", "b", "unexpected"]);
  assert.deepEqual(h.saved(), ["a", "b"]);
  assert.deepEqual(h.cards(), ["a", "b"]);
  h.cluster();
  assert.deepEqual(h.clusters, [["a", "b"]]);
});

test("Replace/Add buttons track selection counts and are disabled for empty selections", async () => {
  const h = await setup();
  h.select([]);
  assert.equal(h.elements["replace-basket-btn"].disabled, true);
  assert.equal(h.elements["add-to-basket-btn"].disabled, true);
  h.select(["a", "b"]);
  assert.equal(h.elements["replace-basket-btn"].disabled, false);
  assert.equal(h.elements["add-to-basket-btn"].disabled, false);
  assert.equal(h.elements["replace-basket-btn"].label.textContent, "Replace basket with selected (2)");
  assert.equal(h.elements["add-to-basket-btn"].label.textContent, "Add selected to basket (2)");
});

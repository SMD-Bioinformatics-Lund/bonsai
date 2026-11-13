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
    return null;
  }
  querySelectorAll() { return []; }
}

const tick = () => new Promise(resolve => setImmediate(resolve));

async function setup(savedIds = []) {
  const storage = new Map([["basket_content", JSON.stringify(savedIds)]]);
  const ids = ["basket-content", "basket-counter-container", "clear-basket-btn", "basket-offcanvas",
    "add-to-basket-btn", "empty-basket-btn"];
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  const clusterButton = new Element(), clusterLink = new Element();
  const requests = [], clusters = [], selectionCallbacks = [];
  let selected = [];
  const table = {
    rows: () => ({ ids: () => ({ toArray: () => selected }) }),
    draw() {},
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
  const sampleIdFilter = load("../web/js/views/groups-view/sample-id-filter.ts");
  const tableController = load("../web/js/utils/table-controller.ts", name =>
    name === "datatables.net-bs5" ? DataTable : {});
  const api = {
    getUserInfo: async () => ({}),
    getSamplesDetails: query => new Promise((resolve, reject) => requests.push({ query, resolve, reject })),
  };
  const view = load("../web/js/views/groups-view/init.ts", () => ({
    ...state, ...basket, ...counter, ...tableController, ...sampleIdFilter,
    createGroupViewApi: () => api,
    User: class { isAdmin = false; },
    initToast() {}, initTooltip() {},
    throwSmallToast() {},
    clusterSamples: (_element, sampleIds) => clusters.push(Array.from(sampleIds)),
  }));
  await view.initGroupView(null, "", "", "");
  const component = elements["basket-content"].children[0];
  return {
    requests, clusters, component, clusterButton,
    saved: () => JSON.parse(storage.get("basket_content")),
    count: () => Number(elements["basket-counter-container"].children[0].counter.textContent),
    cards: () => component.children.map(card => card.innerHTML.match(/<h6 id="([^"]+)"/)[1]),
    select(sampleIds) { selected = sampleIds; selectionCallbacks.forEach(callback => callback()); },
    add: () => elements["add-to-basket-btn"].onclick(),
    clear: () => elements["clear-basket-btn"].onclick(),
    empty: () => elements["empty-basket-btn"].onclick(),
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

test("adding samples preserves valid entries and ignores an older response", async () => {
  const h = await setup(["old", "overlap"]);
  h.select(["overlap", "new"]);
  h.add();
  assert.deepEqual(h.saved(), ["old", "overlap", "new"]);
  await h.respond(1, ["old", "overlap", "new"]);
  await h.respond(0, []);
  assert.deepEqual(h.saved(), ["old", "overlap", "new"]);
  assert.deepEqual(h.cards(), ["old", "overlap", "new"]);
  assert.equal(h.count(), 3);
  h.cluster();
  assert.deepEqual(h.clusters, [["old", "overlap", "new"]]);
});

for (const action of ["clear", "empty"]) {
  test(`${action} basket invalidates in-flight responses and cannot resurrect old cards`, async () => {
    const h = await setup(["old-1", "old-2"]);
    h[action]();
    await h.respond(0, ["old-1", "old-2"]);
    assert.deepEqual(h.saved(), []);
    assert.deepEqual(h.cards(), []);
    assert.equal(h.count(), 0);
    assert.equal(h.clusterButton.disabled, true);
  });
}

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

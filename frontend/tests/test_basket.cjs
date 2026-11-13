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
  attributes = {};
  setAttribute(name, value) { this.attributes[name] = value; }
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
    if (selector === "[data-remove-qc-failed]" && this.innerHTML.includes("data-remove-qc-failed")) {
      return this.qcRemoveButton ??= new Element();
    }
    if (selector === "[data-cluster-with-failed-qc]" && this.innerHTML.includes("data-cluster-with-failed-qc")) {
      return this.qcContinueButton ??= new Element();
    }
    return null;
  }
  querySelectorAll() { return []; }
}

const tick = () => new Promise(resolve => setImmediate(resolve));

async function setup(savedIds = []) {
  const storage = new Map([["basket_content", JSON.stringify(savedIds)]]);
  const ids = ["basket-content", "basket-counter-container", "clear-basket-btn", "basket-offcanvas",
    "add-to-basket-btn", "empty-basket-btn", "basket-qc-feedback", "remove-failed-qc-from-basket-btn"];
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  const clusterButton = new Element(), clusterLink = new Element();
  const requests = [], clusters = [], selectionCallbacks = [], qcRequests = [], toasts = [];
  let failedIds = [], deferQc = false;
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
  const tableController = load("../web/js/utils/table-controller.ts", name =>
    name === "datatables.net-bs5" ? DataTable : {});
  const api = {
    getUserInfo: async () => ({}),
    getSamplesDetails: query => {
      if (query.fields?.includes("qc_status")) {
        const data = query.sid.map(sample_id => ({ sample_id, qc_status: { status: failedIds.includes(sample_id) ? "failed" : "passed" } }));
        if (deferQc) return new Promise((resolve, reject) => qcRequests.push({ query, resolve, reject }));
        qcRequests.push({ query });
        return Promise.resolve({ data });
      }
      return new Promise((resolve, reject) => requests.push({ query, resolve, reject }));
    },
  };
  const view = load("../web/js/views/groups-view/init.ts", () => ({
    ...state, ...basket, ...counter, ...tableController,
    createGroupViewApi: () => api,
    User: class { isAdmin = false; },
    initToast() {}, initTooltip() {},
    throwSmallToast: (...args) => toasts.push(args),
    clusterSamples: (_element, sampleIds) => clusters.push(Array.from(sampleIds)),
  }));
  await view.initGroupView(null, "", "", "");
  const component = elements["basket-content"].children[0];
  return {
    requests, clusters, component, clusterButton,
    saved: () => JSON.parse(storage.get("basket_content")),
    count: () => Number(elements["basket-counter-container"].children[0].counter.textContent),
    cards: () => component.children.flatMap(card => {
      const match = card.innerHTML.match(/<h6 id="([^"]+)"/);
      return match ? [match[1]] : [];
    }),
    qcNotice: () => elements["basket-qc-feedback"].hidden ? undefined : elements["basket-qc-feedback"],
    removeQc: () => elements["remove-failed-qc-from-basket-btn"].onclick(),
    qcCards: () => component.children.filter(child => child.className?.includes("border-danger")),
    qcRequests, toasts,
    setFailed: ids => { failedIds = ids; },
    deferQc: () => { deferQc = true; },
    select(sampleIds) { selected = sampleIds; selectionCallbacks.forEach(callback => callback()); },
    add: () => elements["add-to-basket-btn"].onclick(),
    clear: () => elements["clear-basket-btn"].onclick(),
    empty: () => elements["empty-basket-btn"].onclick(),
    reopen: () => elements["basket-offcanvas"].dispatchEvent(new Event("show.bs.offcanvas")),
    cluster: async () => { await clusterLink.onclick({ preventDefault() {} }); await tick(); },
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
  await h.cluster();
  assert.equal(h.clusters.length, 0);
  assert.equal(h.requests[0].query.limit, 0);
  await h.respond(0, valid);
  assert.deepEqual(h.saved(), valid);
  assert.equal(h.count(), 16);
  assert.equal(h.clusterButton.disabled, true);
  await h.respond(1, valid);
  assert.deepEqual(h.cards(), valid);
  assert.equal(h.clusterButton.disabled, false);
  await h.cluster();
  assert.deepEqual(h.clusters, [valid]);
});

test("QC highlights and removal appear only after an attempt and preserve eligible samples", async () => {
  const ids = ["passed-1", "failed-1", "passed-2", "failed-2"];
  const h = await setup(ids);
  await h.respond(0, ids);
  assert.equal(h.qcNotice(), undefined);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  assert.equal(h.qcCards().length, 0);
  h.setFailed(["failed-1", "failed-2"]);
  await h.cluster();
  assert.equal(h.clusters.length, 0);
  await h.respond(1, ids);
  assert.deepEqual(h.saved(), ids);
  assert.equal(h.qcCards().length, 2);
  assert.ok(h.qcCards().every(card => card.className.includes("bg-danger bg-opacity-10")));
  assert.ok(h.qcCards().every(card => !card.innerHTML.includes("QC failed")));
  assert.ok(h.qcCards().every(card => card.attributes["aria-label"].endsWith(": QC failed")));
  assert.ok(!h.component.children.includes(h.qcNotice()));
  assert.ok(!h.qcNotice().className?.includes("alert"));
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, false);
  assert.match(h.qcNotice().innerHTML, /2 samples are marked as QC failed/);
  h.removeQc();
  assert.deepEqual(h.saved(), ["passed-1", "passed-2"]);
  assert.equal(h.count(), 2);
  await h.respond(2, ["passed-1", "passed-2"]);
  assert.equal(h.qcNotice(), undefined);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  assert.equal(h.qcCards().length, 0);
  assert.equal(h.clusters.length, 0); // Removal does not automatically submit.
  await h.cluster();
  assert.deepEqual(h.clusters[0], ["passed-1", "passed-2"]);
});

test("removing a single QC-failed sample disables clustering when only one remains", async () => {
  const h = await setup(["passed", "failed"]);
  await h.respond(0, ["passed", "failed"]);
  h.setFailed(["failed"]);
  await h.cluster();
  await h.respond(1, ["passed", "failed"]);
  assert.match(h.qcNotice().innerHTML, /1 sample is marked as QC failed/);
  h.removeQc();
  await h.respond(2, ["passed"]);
  assert.deepEqual(h.saved(), ["passed"]);
  assert.deepEqual(h.cards(), ["passed"]);
  assert.ok(h.component.children.some(child => child.textContent?.includes("At least two samples")));
  assert.equal(h.clusterButton.disabled, true);
  await h.cluster();
  assert.equal(h.clusters.length, 0);
});

test("basket changes invalidate QC checks and an earlier continue action", async () => {
  const h = await setup(["passed", "failed"]);
  await h.respond(0, ["passed", "failed"]);
  h.setFailed(["failed"]);
  await h.cluster();
  await h.respond(1, ["passed", "failed"]);
  const oldContinue = h.qcNotice().querySelector("[data-cluster-with-failed-qc]");
  h.select(["added"]);
  h.add();
  oldContinue.dispatchEvent(new Event("click"));
  await h.respond(2, ["passed", "failed", "added"]);
  assert.equal(h.qcNotice(), undefined);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  assert.equal(h.clusters.length, 0);
  h.deferQc();
  const pending = h.cluster();
  h.clear();
  h.qcRequests.at(-1).resolve({ data: [{ sample_id: "failed", qc_status: { status: "failed" } }] });
  await pending;
  assert.equal(h.qcNotice(), undefined);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  assert.deepEqual(h.saved(), []);
  assert.equal(h.clusters.length, 0);
});

test("cluster anyway preserves failed samples and their warning", async () => {
  const h = await setup(["passed", "failed"]);
  await h.respond(0, ["passed", "failed"]);
  h.setFailed(["failed"]);
  await h.cluster();
  assert.equal(h.clusters.length, 0);
  await h.respond(1, ["passed", "failed"]);
  const proceed = h.qcNotice().querySelector("[data-cluster-with-failed-qc]");
  proceed.dispatchEvent(new Event("click"));
  proceed.dispatchEvent(new Event("click"));
  assert.deepEqual(h.clusters, [["passed", "failed"]]);
  assert.deepEqual(h.saved(), ["passed", "failed"]);
  assert.equal(h.qcCards().length, 1);
  assert.equal(proceed.disabled, true);
  assert.deepEqual(Array.from(h.qcRequests[0].query.fields), ["sample_id", "qc_status"]);
});

test("a failed curated QC lookup reports an error and permits retry", async () => {
  const h = await setup(["a", "b"]);
  await h.respond(0, ["a", "b"]);
  h.deferQc();
  const pending = h.cluster();
  h.qcRequests[0].reject(new Error("Unavailable"));
  await pending;
  assert.equal(h.clusters.length, 0);
  assert.equal(h.toasts.at(-1)[1], "error");
  assert.deepEqual(h.saved(), ["a", "b"]);
  assert.equal(h.clusterButton.disabled, false);
});

test("automatic QC findings and unprocessed or absent curated status do not trigger a warning", async () => {
  const h = await setup(["unprocessed", "unknown", "missing-qc"]);
  await h.respond(0, ["unprocessed", "unknown", "missing-qc"]);
  h.deferQc();
  const pending = h.cluster();
  h.qcRequests[0].resolve({ data: [
    { sample_id: "unprocessed", qc_status: { status: "unprocessed" }, automatic_qc: "failed" },
    { sample_id: "unknown", qc_status: null, automatic_qc: "failed" },
    { sample_id: "missing-qc", automatic_qc: "failed" },
  ] });
  await pending;
  assert.equal(h.qcNotice(), undefined);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  assert.deepEqual(h.clusters, [["unprocessed", "unknown", "missing-qc"]]);
});

test("a fresh curated QC check clears an earlier warning after QC is corrected", async () => {
  const h = await setup(["passed", "failed"]);
  await h.respond(0, ["passed", "failed"]);
  h.setFailed(["failed"]);
  await h.cluster();
  await h.respond(1, ["passed", "failed"]);
  assert.equal(h.qcCards().length, 1);
  h.setFailed([]);
  await h.cluster();
  await h.respond(2, ["passed", "failed"]);
  assert.equal(h.qcNotice(), undefined);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  assert.equal(h.qcCards().length, 0);
  assert.deepEqual(h.clusters, [["passed", "failed"]]);
  assert.equal(h.qcRequests.length, 2);
});

test("a sample disappearing during the QC check refreshes the basket without submitting", async () => {
  const h = await setup(["a", "b"]);
  await h.respond(0, ["a", "b"]);
  h.deferQc();
  const pending = h.cluster();
  h.qcRequests[0].resolve({ data: [{ sample_id: "a", qc_status: { status: "passed" } }] });
  await pending;
  assert.equal(h.clusters.length, 0);
  assert.match(h.toasts.at(-1)[0], /no longer available/);
  await h.respond(1, ["a"]);
  await h.respond(2, ["a"]);
  assert.deepEqual(h.saved(), ["a"]);
  assert.equal(h.clusterButton.disabled, true);
});

test("removing all QC-failed samples leaves an empty basket", async () => {
  const ids = ["failed-1", "failed-2"];
  const h = await setup(ids);
  await h.respond(0, ids);
  h.setFailed(ids);
  await h.cluster();
  await h.respond(1, ids);
  h.removeQc();
  assert.deepEqual(h.saved(), []);
  assert.equal(h.count(), 0);
  assert.match(h.component.innerHTML, /Your basket is empty/);
  assert.equal(h.clusterButton.disabled, true);
  assert.equal(h.qcNotice(), undefined);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
});

test("an entirely missing basket becomes empty and cannot cluster", async () => {
  const h = await setup(["missing-1", "missing-2"]);
  await h.respond(0, []);
  assert.deepEqual(h.saved(), []);
  assert.equal(h.count(), 0);
  assert.match(h.component.innerHTML, /Your basket is empty/);
  assert.equal(h.clusterButton.disabled, true);
  await h.cluster();
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
  await h.cluster();
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
  await h.cluster();
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
  await h.cluster();
  assert.deepEqual(h.clusters, [["a", "b"]]);
});

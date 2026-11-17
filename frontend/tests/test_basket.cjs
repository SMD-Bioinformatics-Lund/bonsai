// Run from frontend/: node --test tests/test_basket.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");
const apiErrorExports = {};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(
  path.join(__dirname, "../web/js/core/api/http/ApiError.ts"), "utf8",
), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText,
{ exports: apiErrorExports, Error });
const { ApiError } = apiErrorExports;

// Only the DOM surface needed by the basket and group-view initialization.
class Element extends EventTarget {
  children = [];
  disabled = false;
  counter = { textContent: "" };
  badge = { hidden: false };
  attributes = {};
  style = {};
  setAttribute(name, value) { this.attributes[name] = value; }
  getAttribute(name) { return this.attributes[name]; }
  classList = { toggle() {} };
  set innerHTML(value) {
    this.html = value;
    this.children = [];
    this.counter.textContent = value.match(/data-test-id="samples-in-basket-counter">([^<]*)/)?.[1] ?? "";
  }
  get innerHTML() { return this.html ?? ""; }
  appendChild(child) { this.children.push(child); child.parentElement = this; child.connectedCallback?.(); }
  remove() {
    if (this.parentElement) this.parentElement.children = this.parentElement.children.filter(child => child !== this);
  }
  querySelector(selector) {
    if (selector === "#sample-basket-counter") return this.counter;
    if (selector === "#sample-basket-badge") return this.badge;
    return null;
  }
  querySelectorAll() { return []; }
}

const tick = () => new Promise(resolve => setImmediate(resolve));

async function setup(savedIds = [], { deferSchemes = false } = {}) {
  const storage = new Map([["basket_content", JSON.stringify(savedIds)]]);
  const ids = ["basket-content", "basket-counter-container", "clear-basket-btn", "basket-offcanvas",
    "add-to-basket-btn", "empty-basket-btn", "remove-failed-qc-from-basket-btn"];
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  const clusterButton = new Element();
  const clusterLinks = Object.fromEntries(["mlst", "cgmlst", "minhash", "ska"].map(method => {
    const link = new Element();
    link.setAttribute("data-bi-typing-method", method);
    return [method, link];
  }));
  const clusterLink = clusterLinks.mlst;
  const schemeRequests = [];
  const requests = [], clusters = [], selectionCallbacks = [];
  let failedIds = [];
  let selected = [];
  const table = {
    rows: () => ({ ids: () => ({ toArray: () => selected }), count: () => selected.length }),
    draw() {},
    columns: { adjust() {} },
    on: (_events, callback) => selectionCallbacks.push(callback),
  };
  class DataTable { constructor() { return table; } }
  DataTable.Buttons = { jszip() {} };
  const document = {
    createElement: tag => Object.assign(new Element(), { tagName: tag.toUpperCase() }),
    getElementById: id => elements[id] ?? null,
    querySelector: selector => selector === "#basket-cluster-samples .btn" ? clusterButton
      : elements[selector.slice(1)] ?? null,
    querySelectorAll: selector => selector === "#basket-cluster-samples a" ? Object.values(clusterLinks) : [],
  };
  const globals = {
    HTMLElement: Element, CustomEvent, Error, document,
    window: {},
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
  const basket = load("../web/js/components/sample-basket.ts", () => ({ ApiError }));
  const counter = load("../web/js/components/samples-basket-counter.ts");
  const tableController = load("../web/js/utils/table-controller.ts", name =>
    name === "datatables.net-bs5" ? DataTable : {});
  const api = {
    getUserInfo: async () => ({}),
    validateAlleleClustering: sampleIds => deferSchemes
      ? new Promise((resolve, reject) => schemeRequests.push({ sampleIds: Array.from(sampleIds), resolve, reject }))
      : Promise.resolve({ mlst: { can_cluster: true, notice: null }, cgmlst: { can_cluster: true, notice: null } }),
    getSamplesDetails: query => new Promise((resolve, reject) => requests.push({ query, resolve, reject })),
  };
  const view = load("../web/js/views/groups-view/init.ts", () => ({
    ...state, ...basket, ...counter, ...tableController,
    createGroupViewApi: () => api,
    User: class { isAdmin = false; },
    initToast() {}, initTooltip() {},
    throwSmallToast() {},
    clusterSamples: (_element, sampleIds) => clusters.push(Array.from(sampleIds)),
  }));
  await view.initGroupView(null, "", "", "");
  const component = elements["basket-content"].children[0];
  return {
    requests, clusters, component, clusterButton, clusterLinks, schemeRequests,
    saved: () => JSON.parse(storage.get("basket_content")),
    count: () => Number(elements["basket-counter-container"].children[0].counter.textContent),
    cards: () => (component.children.find(child => child.className === "basket-samples")?.children ?? []).flatMap(card => {
      const match = card.innerHTML.match(/<h6 id="([^"]+)"/);
      return match ? [match[1]] : [];
    }),
    notices: () => component.children.find(child => child.attributes["data-test-id"] === "basket-notices"),
    noticeText: () => {
      const texts = element => [element.textContent || "", ...element.children.flatMap(texts)];
      return texts(component).join(" ");
    },
    removeQc: () => elements["remove-failed-qc-from-basket-btn"].onclick(),
    qcCards: () => (component.children.find(child => child.className === "basket-samples")?.children ?? []).filter(child => child.className?.includes("border-danger")),
    setFailed: ids => { failedIds = ids; },
    select(sampleIds) { selected = sampleIds; selectionCallbacks.forEach(callback => callback()); },
    add: () => elements["add-to-basket-btn"].onclick(),
    clear: () => elements["clear-basket-btn"].onclick(),
    empty: () => elements["empty-basket-btn"].onclick(),
    reopen: () => elements["basket-offcanvas"].dispatchEvent(new Event("show.bs.offcanvas")),
    cluster: async (method = "mlst") => { await clusterLinks[method].onclick({ preventDefault() {} }); await tick(); },
    elements,
    async respondData(index, samples) {
      requests[index].resolve({ data: samples.map(sample => ({sample_name: sample.sample_id, assay: "test", ...sample})) });
      await tick();
    },
    async respond(index, sampleIds) {
      requests[index].resolve({ data: sampleIds.map(sample_id => ({ sample_id, sample_name: sample_id, assay: "test", qc_status: { status: failedIds.includes(sample_id) ? "failed" : "passed" } })) });
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

test("QC is checked before enabling clustering and removal preserves eligible samples", async () => {
  const ids = ["passed-1", "failed-1", "passed-2", "failed-2"];
  const h = await setup(ids);
  h.setFailed(["failed-1", "failed-2"]);
  assert.equal(h.clusterButton.disabled, true);
  await h.cluster();
  assert.equal(h.clusters.length, 0);
  assert.deepEqual(Array.from(h.requests[0].query.fields), ["sample_id", "sample_name", "assay", "qc_status"]);
  await h.respond(0, ids);
  assert.equal(h.clusterButton.disabled, false);
  assert.deepEqual(h.saved(), ids);
  assert.equal(h.qcCards().length, 2);
  assert.ok(h.qcCards().every(card => card.className.includes("bg-danger bg-opacity-10")));
  assert.ok(h.qcCards().every(card => !card.innerHTML.includes("QC failed")));
  assert.ok(h.qcCards().every(card => card.attributes["aria-label"].endsWith(": QC failed")));
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, false);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].textContent, "Remove 2 failed QC from basket");
  assert.ok(!h.noticeText().includes("marked as QC failed"));
  h.removeQc();
  assert.deepEqual(h.saved(), ["passed-1", "passed-2"]);
  assert.equal(h.count(), 2);
  assert.equal(h.clusterButton.disabled, true);
  await h.respond(1, ["passed-1", "passed-2"]);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  assert.equal(h.qcCards().length, 0);
  assert.equal(h.clusters.length, 0); // Removal does not automatically submit.
  await h.cluster();
  assert.deepEqual(h.clusters[0], ["passed-1", "passed-2"]);
  assert.equal(h.requests.length, 2); // Card data and curated QC share one request per render.
});

test("the green clustering action includes failed-QC samples without another check or confirmation", async () => {
  const h = await setup(["passed", "failed"]);
  h.setFailed(["failed"]);
  await h.respond(0, ["passed", "failed"]);
  assert.equal(h.qcCards().length, 1);
  assert.equal(h.clusterButton.disabled, false);
  await h.cluster();
  assert.deepEqual(h.clusters, [["passed", "failed"]]);
  assert.deepEqual(h.saved(), ["passed", "failed"]);
  assert.equal(h.qcCards().length, 1);
  assert.equal(h.requests.length, 1);
});

test("removing a single QC-failed sample disables clustering when only one remains", async () => {
  const h = await setup(["passed", "failed"]);
  h.setFailed(["failed"]);
  await h.respond(0, ["passed", "failed"]);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].textContent, "Remove 1 failed QC from basket");
  h.removeQc();
  await h.respond(1, ["passed"]);
  assert.deepEqual(h.saved(), ["passed"]);
  assert.deepEqual(h.cards(), ["passed"]);
  assert.match(h.noticeText(), /At least two samples/);
  assert.equal(h.clusterButton.disabled, true);
  await h.cluster();
  assert.equal(h.clusters.length, 0);
});

test("opening the basket refreshes curated QC before re-enabling clustering", async () => {
  const h = await setup(["passed", "changed"]);
  await h.respond(0, ["passed", "changed"]);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  h.setFailed(["changed"]);
  h.reopen();
  assert.equal(h.clusterButton.disabled, true);
  await h.cluster();
  assert.equal(h.clusters.length, 0);
  await h.respond(1, ["passed", "changed"]);
  assert.equal(h.qcCards().length, 1);
  assert.equal(h.clusterButton.disabled, false);
  h.setFailed([]);
  h.reopen();
  assert.equal(h.clusterButton.disabled, true);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  await h.respond(2, ["passed", "changed"]);
  assert.equal(h.qcCards().length, 0);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  assert.equal(h.clusterButton.disabled, false);
  assert.equal(h.requests.length, 3);
});

test("adding samples checks their curated QC before clustering is enabled", async () => {
  const h = await setup(["a", "b"]);
  await h.respond(0, ["a", "b"]);
  h.setFailed(["added"]);
  h.select(["added"]);
  h.add();
  assert.equal(h.clusterButton.disabled, true);
  await h.cluster();
  assert.equal(h.clusters.length, 0);
  await h.respond(1, ["a", "b", "added"]);
  assert.equal(h.qcCards().length, 1);
  assert.equal(h.clusterButton.disabled, false);
  await h.cluster();
  assert.deepEqual(h.clusters, [["a", "b", "added"]]);
});

test("automatic QC findings and unprocessed or absent curated status do not trigger a warning", async () => {
  const h = await setup(["unprocessed", "unknown", "missing-qc"]);
  await h.respondData(0, [
    { sample_id: "unprocessed", qc_status: { status: "unprocessed" }, automatic_qc: "failed" },
    { sample_id: "unknown", qc_status: null, automatic_qc: "failed" },
    { sample_id: "missing-qc", automatic_qc: "failed" },
  ]);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  assert.equal(h.clusterButton.disabled, false);
  await h.cluster();
  assert.deepEqual(h.clusters, [["unprocessed", "unknown", "missing-qc"]]);
});

test("stale QC responses cannot replace the status of the current basket", async () => {
  const h = await setup(["a", "changed"]);
  h.reopen();
  await h.respond(1, ["a", "changed"]);
  h.setFailed(["changed"]);
  await h.respond(0, ["a", "changed"]);
  assert.equal(h.qcCards().length, 0);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  assert.equal(h.clusterButton.disabled, false);
});

test("removing all QC-failed samples leaves an empty basket", async () => {
  const ids = ["failed-1", "failed-2"];
  const h = await setup(ids);
  h.setFailed(ids);
  await h.respond(0, ids);
  h.removeQc();
  assert.deepEqual(h.saved(), []);
  assert.equal(h.count(), 0);
  assert.match(h.component.innerHTML, /Your basket is empty/);
  assert.equal(h.clusterButton.disabled, true);
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
  assert.equal(h.clusterButton.disabled, true);
  await h.cluster();
  assert.equal(h.clusters.length, 0);
  h.reopen();
  await h.respond(1, ids);
  assert.deepEqual(h.cards(), ids);
  assert.equal(h.clusterButton.disabled, false);
});

test("an expired basket session explains recovery and preserves saved samples", async () => {
  const ids = ["a", "b"];
  const h = await setup(ids);
  h.requests[0].reject(new ApiError(401, "Token expired"));
  await tick();
  assert.deepEqual(h.saved(), ids);
  assert.equal(h.count(), 2);
  assert.equal(h.clusterButton.disabled, true);
  assert.match(h.component.innerHTML, /Your session is no longer valid/);
  assert.match(h.component.innerHTML, /Your basket is saved/);
  assert.doesNotMatch(h.component.innerHTML, /Reopen it/);
  assert.match(h.component.innerHTML, /Reload the page to continue\./);
  assert.doesNotMatch(h.component.innerHTML, /sign in/);
  assert.equal(h.component.children.length, 0);
  assert.equal(h.requests.length, 1);
  await h.cluster();
  assert.deepEqual(h.clusters, []);

  // Reloading reconstructs the basket from saved IDs with fresh page credentials.
  const reloaded = await setup(h.saved());
  await reloaded.respond(0, ids);
  assert.deepEqual(reloaded.cards(), ids);
  assert.equal(reloaded.clusterButton.disabled, false);
});

test("a session expiring during scheme validation also explains recovery and blocks clustering", async () => {
  const ids = ["a", "b"];
  const h = await setup(ids, { deferSchemes: true });
  await h.respond(0, ids);
  h.schemeRequests[0].reject(new ApiError(401, "Token expired"));
  await tick();
  assert.deepEqual(h.saved(), ids);
  assert.equal(h.clusterButton.disabled, true);
  assert.match(h.component.innerHTML, /Your session is no longer valid/);
  assert.match(h.component.innerHTML, /Reload the page to continue\./);
  assert.equal(h.component.children.length, 0);
  await h.cluster("minhash");
  assert.deepEqual(h.clusters, []);
});

test("a failed basket refresh keeps clustering disabled until a successful QC reload", async () => {
  const ids = ["passed", "failed"];
  const h = await setup(ids);
  h.setFailed(["failed"]);
  await h.respond(0, ids);
  assert.equal(h.qcCards().length, 1);
  h.reopen();
  h.requests[1].reject(new Error("QC lookup failed"));
  await tick();
  assert.equal(h.clusterButton.disabled, true);
  assert.equal(h.elements["remove-failed-qc-from-basket-btn"].hidden, true);
  assert.deepEqual(h.saved(), ids);
  await h.cluster();
  assert.equal(h.clusters.length, 0);
  h.reopen();
  await h.respond(2, ids);
  assert.equal(h.clusterButton.disabled, false);
  assert.equal(h.qcCards().length, 1);
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


test("scheme checks disable only incompatible allele methods and show their notice", async () => {
  const h = await setup(["a", "b"], { deferSchemes: true });
  await h.respond(0, ["a", "b"]);
  assert.equal(h.component.canClusterWith("mlst"), false);
  await h.cluster("mlst");
  assert.equal(h.clusters.length, 0);
  assert.equal(h.component.canClusterWith("minhash"), true);
  h.schemeRequests[0].resolve({ mlst: { can_cluster: false, notice: "Different MLST schemes <unsafe>" }, cgmlst: { can_cluster: true } });
  await tick();
  assert.equal(h.clusterLinks.mlst.attributes["aria-disabled"], "true");
  assert.equal(h.clusterLinks.mlst.tabIndex, -1);
  assert.equal(h.clusterLinks.cgmlst.attributes["aria-disabled"], "false");
  assert.equal(h.notices().attributes.open, undefined);
  assert.match(h.noticeText(), /1 notice/);
  assert.match(h.noticeText(), /Different MLST schemes <unsafe>/);
  assert.equal(h.notices().children[1].innerHTML, "");
  await h.cluster("mlst");
  assert.equal(h.clusters.length, 0);
  await h.cluster("cgmlst");
  assert.deepEqual(h.clusters, [["a", "b"]]);
  assert.deepEqual(h.saved(), ["a", "b"]);
});


test("failed scheme validation keeps allele methods disabled and allows retry", async () => {
  const h = await setup(["a", "b"], { deferSchemes: true });
  await h.respond(0, ["a", "b"]);
  h.schemeRequests[0].reject(new Error("offline"));
  await tick();
  assert.equal(h.component.canClusterWith("mlst"), false);
  assert.equal(h.component.canClusterWith("cgmlst"), false);
  assert.equal(h.component.canClusterWith("ska"), true);
  assert.match(h.noticeText(), /1 notice/);
  assert.match(h.noticeText(), /compatibility could not be checked/);
  h.reopen();
  await h.respond(1, ["a", "b"]);
  h.schemeRequests[1].resolve({ mlst: { can_cluster: true }, cgmlst: { can_cluster: true } });
  await tick();
  assert.equal(h.component.canClusterWith("mlst"), true);
});


test("stale scheme responses cannot enable a changed or emptied basket", async () => {
  const h = await setup(["a", "b"], { deferSchemes: true });
  await h.respond(0, ["a", "b"]);
  h.reopen();
  await h.respond(1, ["a", "b"]);
  h.schemeRequests[1].resolve({ mlst: { can_cluster: false, notice: "Current mismatch" }, cgmlst: { can_cluster: false } });
  await tick();
  h.schemeRequests[0].resolve({ mlst: { can_cluster: true }, cgmlst: { can_cluster: true } });
  await tick();
  assert.equal(h.component.canClusterWith("mlst"), false);
  assert.match(h.noticeText(), /Current mismatch/);
  h.reopen();
  await h.respond(2, ["a", "b"]);
  h.clear();
  h.schemeRequests[2].resolve({ mlst: { can_cluster: true }, cgmlst: { can_cluster: true } });
  await tick();
  assert.equal(h.component.canClusterWith("mlst"), false);
  assert.deepEqual(h.saved(), []);
  assert.equal(h.notices(), undefined);
});

test("two method notices keep sample-specific details inside one closed disclosure", async () => {
  const h = await setup(["a", "b"], { deferSchemes: true });
  await h.respond(0, ["a", "b"]);
  h.schemeRequests[0].resolve({
    mlst: {
      can_cluster: false,
      notice: "Cannot cluster by MLST: the typing scheme could not be verified.",
      details: ["No detected MLST scheme is available:\nLAB-123 <unsafe>"],
    },
    cgmlst: {
      can_cluster: false,
      notice: "Cannot cluster by cgMLST: different analysis profiles. Select samples from one profile to resolve this conflict.",
      details: ["ecoli — 25 samples:\na\nb\nc\nd\ne\nand 20 more", "staphylococcus — 1 sample:\nf"],
    },
  });
  await tick();
  const disclosure = h.notices();
  assert.equal(disclosure.attributes.open, undefined);
  assert.equal(disclosure.children[0].children[1].textContent, "2 notices");
  const [mlst, cgmlst] = disclosure.children.slice(1);
  assert.equal(mlst.children[0].tagName, "H6");
  assert.equal(mlst.children[0].textContent, "MLST");
  assert.equal(cgmlst.children[0].tagName, "H6");
  assert.equal(cgmlst.children[0].textContent, "cgMLST");
  assert.equal(mlst.children[1].textContent, "The typing scheme could not be verified.");
  assert.match(cgmlst.children[1].textContent, /^Different analysis profiles\. Select samples/);
  const missing = mlst.children[2].children[0];
  assert.equal(missing.children[0].tagName, "STRONG");
  assert.equal(missing.children[0].textContent, "No detected MLST scheme is available");
  assert.equal(missing.children[1].textContent, "LAB-123 <unsafe>");
  assert.equal(missing.children[1].innerHTML, "");
  assert.equal(missing.children[1].style.whiteSpace, "pre-line");
  const group = cgmlst.children[2].children[0];
  assert.equal(group.children[0].tagName, "STRONG");
  assert.equal(group.children[0].textContent, "ecoli — 25 samples");
  assert.equal(group.children[1].textContent, "a\nb\nc\nd\ne\nand 20 more");
  assert.equal(h.clusterLinks.mlst.attributes["aria-disabled"], "true");
  assert.equal(h.clusterLinks.cgmlst.attributes["aria-disabled"], "true");
  assert.equal(h.component.canClusterWith("minhash"), true);
  assert.equal(h.component.canClusterWith("ska"), true);
  h.reopen();
  assert.equal(h.notices(), undefined);
  await h.respond(1, ["a", "b"]);
  h.schemeRequests[1].resolve({ mlst: { can_cluster: true }, cgmlst: { can_cluster: true } });
  await tick();
  assert.equal(h.notices(), undefined);
});

test("notice category removal uses every sample ID and revalidates the remaining basket", async () => {
  const removed = Array.from({ length: 8 }, (_, i) => `other-${i}`);
  const all = ["keep-a", "keep-b", ...removed];
  const h = await setup(all, { deferSchemes: true });
  await h.respond(0, all);
  h.schemeRequests[0].resolve({
    mlst: { can_cluster: true },
    cgmlst: {
      can_cluster: false,
      notice: "Cannot cluster by cgMLST: different analysis profiles.",
      groups: [{ detail: "Other assay — 8 samples:\nother-0\nother-1\nother-2\nother-3\nother-4\nand 3 more", sample_ids: removed }],
    },
  });
  await tick();
  const item = h.notices().children[1].children[2].children[0];
  const button = item.children[2];
  assert.equal(button.textContent, "Remove 8 from basket");
  button.dispatchEvent(new Event("click"));
  assert.deepEqual(h.saved(), ["keep-a", "keep-b"]);
  assert.equal(h.component.canClusterWith("cgmlst"), false);
  await h.respond(1, ["keep-a", "keep-b"]);
  h.schemeRequests[1].resolve({ mlst: { can_cluster: true }, cgmlst: { can_cluster: true } });
  await tick();
  assert.equal(h.notices(), undefined);
  assert.equal(h.component.canClusterWith("cgmlst"), true);
  assert.equal(h.count(), 2);
  // A detached button from an earlier render cannot remove current selections.
  h.select(removed);
  h.add();
  await h.respond(2, all);
  button.dispatchEvent(new Event("click"));
  assert.deepEqual(new Set(h.saved()), new Set(all));
});

test("missing typing data categories remove only the affected samples", async () => {
  const h = await setup(["typed-a", "typed-b", "missing"], { deferSchemes: true });
  await h.respond(0, ["typed-a", "typed-b", "missing"]);
  h.schemeRequests[0].resolve({
    mlst: { can_cluster: true },
    cgmlst: {
      can_cluster: false,
      notice: "Cannot cluster by cgMLST: typing data is unavailable for 1 sample.",
      groups: [{ detail: "No cgMLST typing profile is available:\nmissing <literal>", sample_ids: ["missing"] }],
    },
  });
  await tick();
  assert.equal(h.component.canClusterWith("mlst"), true);
  assert.equal(h.component.canClusterWith("cgmlst"), false);
  const item = h.notices().children[1].children[2].children[0];
  assert.equal(item.children[1].textContent, "missing <literal>");
  item.children[2].dispatchEvent(new Event("click"));
  assert.deepEqual(h.saved(), ["typed-a", "typed-b"]);
});

test("compatibility status stays visible while pending and clears on success or failure", async () => {
  const h = await setup(["a", "b"], { deferSchemes: true });
  const status = () => h.component.children.find(child => child.attributes["data-test-id"] === "basket-validation-status");
  await h.respond(0, ["a", "b"]);
  assert.equal(status().attributes.role, "status");
  assert.equal(status().children[1].textContent, "Checking MLST/cgMLST compatibility…");
  assert.equal(h.component.canClusterWith("mlst"), false);
  assert.equal(h.notices(), undefined);
  h.schemeRequests[0].resolve({ mlst: { can_cluster: true }, cgmlst: { can_cluster: true } });
  await tick();
  assert.equal(status(), undefined);
  assert.equal(h.component.canClusterWith("mlst"), true);
  h.reopen();
  await h.respond(1, ["a", "b"]);
  assert.ok(status());
  h.schemeRequests[1].reject(new Error("unavailable"));
  await tick();
  assert.equal(status(), undefined);
  assert.match(h.noticeText(), /compatibility could not be checked/);
});

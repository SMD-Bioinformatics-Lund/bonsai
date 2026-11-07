// Run from frontend/: node --test tests/test_group_memberships.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");

function load(relative, globals = {}) {
  const exports = {};
  const source = fs.readFileSync(path.join(__dirname, relative), "utf8");
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, { exports, require: name => name === "./utils/queryParams"
    ? load("../web/js/core/api/utils/queryParams.ts", { URLSearchParams }) : {},
    console: { warn() {}, error() {} }, ...globals });
  return exports;
}

function selectorHarness(lookup = async () => [
  { sample_id: "one", group_id: "common" }, { sample_id: "one", group_id: "unique-one" },
  { sample_id: "two", group_id: "common" }, { sample_id: "two", group_id: "unique-two" },
]) {
  let selected = ["one", "two"];
  const choices = { values: [], getSelected() { return this.values; },
    setSelected(values) { this.values = values; }, clearSelected() { this.values = []; } };
  const apply = { disabled: false };
  class Element extends EventTarget {
    attachShadow() { this.shadowRoot = { appendChild() {}, getElementById: id => id === "groups" ? choices : apply }; }
  }
  const { GroupSelector } = load("../web/js/components/group-selector.ts", {
    HTMLElement: Element, CustomEvent, AbortController,
    customElements: { define() {} },
    document: { createElement: () => ({ content: { cloneNode() {} } }) },
    require: () => ({ emitEvent() {} }),
  });
  const selector = new GroupSelector(), changes = [];
  selector.getSelectedSamples = () => selected;
  selector.getGroupMembership = lookup;
  selector.addToGroup = async (group, samples) => changes.push(["add", group, Array.from(samples)]);
  selector.removeFromGroup = async (group, samples) => changes.push(["remove", group, Array.from(samples)]);
  return { selector, choices, changes, apply, setSamples: ids => { selected = ids; } };
}

test("unchanged common groups preserve every individual membership", async () => {
  const h = selectorHarness();
  await h.selector.onSelectedSamplesChange();
  assert.deepEqual(Array.from(h.choices.values), ["common"]);
  await h.selector.onApply();
  assert.deepEqual(h.changes, []);
});

test("deselecting a common group removes only that group", async () => {
  const h = selectorHarness();
  await h.selector.onSelectedSamplesChange();
  h.choices.values = [];
  await h.selector.onApply();
  assert.deepEqual(h.changes, [["remove", "common", ["one"]], ["remove", "common", ["two"]]]);
});

test("adding a common group retains undisplayed memberships", async () => {
  const h = selectorHarness();
  await h.selector.onSelectedSamplesChange();
  h.choices.values = ["common", "new"];
  await h.selector.onApply();
  assert.deepEqual(h.changes, [["add", "new", ["one"]], ["add", "new", ["two"]]]);
});

test("a failed membership lookup disables Apply and submits no changes", async () => {
  const h = selectorHarness(async () => { throw new Error("Offline"); });
  await h.selector.onSelectedSamplesChange();
  await h.selector.onApply();
  assert.equal(h.apply.disabled, true);
  assert.deepEqual(h.changes, []);
});

test("an older response cannot replace the current selection", async () => {
  const requests = [];
  const h = selectorHarness(() => new Promise(resolve => requests.push(resolve)));
  const old = h.selector.onSelectedSamplesChange();
  h.setSamples(["new"]);
  const current = h.selector.onSelectedSamplesChange();
  requests[1]([{ sample_id: "new", group_id: "new-group" }]);
  await current;
  requests[0]([{ sample_id: "one", group_id: "old-group" }, { sample_id: "two", group_id: "old-group" }]);
  await old;
  assert.deepEqual(Array.from(h.choices.values), ["new-group"]);
});

test("changing selection during Apply cannot remove another selection's unique groups", async () => {
  const h = selectorHarness();
  await h.selector.onSelectedSamplesChange();
  h.choices.values = ["common", "new"];
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  h.selector.addToGroup = async (group, samples) => {
    h.changes.push(["add", group, Array.from(samples)]);
    if (samples[0] === "one") await pending;
  };
  const applying = h.selector.onApply();
  h.setSamples(["two"]);
  await h.selector.onSelectedSamplesChange();
  release();
  await applying;
  assert.deepEqual(h.changes, [["add", "new", ["one"]], ["add", "new", ["two"]]]);
});

test("membership lookup chunks 125 IDs without losing any edges", async () => {
  const requests = [];
  const { ApiService } = load("../web/js/core/api/index.ts");
  const api = new ApiService({ request: async (url, options) => {
    requests.push({ url, options });
    return new URL(url, "http://test").searchParams.getAll("s").map(sample_id => ({ sample_id, group_id: "common" }));
  } });
  const ids = Array.from({ length: 125 }, (_, i) => `record-${i}`);
  const signal = new AbortController().signal;
  const edges = await api.getMembershipsBySamples(ids, signal);
  assert.deepEqual(requests.map(x => new URL(x.url, "http://test").searchParams.getAll("s").length), [100, 25]);
  assert.equal(edges.length, 125);
  assert.deepEqual(Array.from(edges, x => x.sample_id), ids);
  assert.ok(requests.every(x => x.options.signal === signal));
});

test("an empty membership selection makes no unfiltered request", async () => {
  const { ApiService } = load("../web/js/core/api/index.ts");
  const api = new ApiService({ request: async () => { throw new Error("Should not query every membership"); } });
  assert.deepEqual(Array.from(await api.getMembershipsBySamples([])), []);
});

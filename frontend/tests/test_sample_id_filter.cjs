const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

function loadFilter(document = {}) {
  const exports = {};
  const source = fs.readFileSync(path.join(__dirname, "../web/js/views/groups-view/sample-id-filter.ts"), "utf8");
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, { exports, document });
  return exports;
}

test("pasted IDs accept spreadsheet separators and ignore blanks and duplicates", () => {
  const { parseSampleIds } = loadFilter();
  assert.deepEqual(Array.from(parseSampleIds(" A\r\nB\tC, D;A;;\n Sample with spaces \n")),
    ["A", "B", "C", "D", "Sample with spaces"]);
  assert.deepEqual(Array.from(parseSampleIds(" \t,;\n")), []);
});

test("exact matching accepts all identifier types and returns every shared Lab ID record", () => {
  const { matchSampleIds } = loadFilter();
  const result = matchSampleIds(["SAMPLE-12", "LAB-A", "uuid-3", "A[1].*", "sample-12", "absent"], [
    { sampleId: "uuid-1", sampleName: "SAMPLE-12", labId: "LAB-A" },
    { sampleId: "uuid-2", sampleName: "SAMPLE-123", labId: "LAB-A" },
    { sampleId: "uuid-3", sampleName: "Other" },
    { sampleId: "uuid-4", sampleName: "A[1].*", labId: null },
    { sampleId: "uuid-5", sampleName: "A1xyz" },
  ]);
  assert.deepEqual(Array.from(result.sampleIds), ["uuid-1", "uuid-2", "uuid-3", "uuid-4"]);
  assert.deepEqual(Array.from(result.unmatchedIds), ["sample-12", "absent"]);
  assert.equal(result.matchedIds.size, 4);
  assert.deepEqual(Array.from(matchSampleIds(["SAMPLE-12"], [
    { sampleId: "uuid-2", sampleName: "SAMPLE-123" },
  ]).sampleIds), []);
});

function setup(scope = "this group") {
  const element = () => ({
    hidden: true, value: "", textContent: "", dataset: {}, children: [], listeners: {},
    classList: { add() {} },
    replaceChildren(...children) { this.children = children; },
    appendChild(child) { this.children.push(child); },
    addEventListener(name, handler) { this.listeners[name] = handler; },
    focus() { this.focused = true; },
  });
  const ids = ["controls", "form", "input", "modal", "clear", "feedback", "summary", "unmatched", "unmatched-title", "unmatched-list"];
  const elements = Object.fromEntries(ids.map(id => [`sample-id-filter-${id}`, element()]));
  elements["sample-id-filter-feedback"].dataset.scope = scope;
  const rows = [
    { id: "uuid-1", dataset: { sampleName: "SAMPLE-12", labId: "LAB-A" } },
    { id: "uuid-2", dataset: { sampleName: "SAMPLE-123", labId: "LAB-A" } },
    { id: "uuid-3", dataset: { sampleName: "Other", labId: "LAB-B" } },
  ];
  const filters = new Map([["otherFilter", (_text, _data, index) => index !== 1]]);
  const searchParent = element();
  let visible = [];
  const api = {
    table: () => ({ container: () => ({ querySelector: () => ({ parentElement: searchParent }) }) }),
    rows: () => ({ nodes: () => ({ toArray: () => rows }) }),
    row: index => ({ id: () => rows[index].id }),
    search: { fixed(name, predicate) {
      if (predicate === null) filters.delete(name);
      else filters.set(name, predicate);
      return api;
    } },
    draw() {
      visible = rows.filter((row, index) => [...filters.values()].every(fn => fn("", [], index))).map(row => row.id);
      return api;
    },
  };
  const module = loadFilter({ getElementById: id => elements[id], createElement: element });
  module.initSampleIdFilter({ getTable: () => api });
  return {
    elements, filters, searchParent, visible: () => visible,
    apply(input) {
      elements["sample-id-filter-input"].value = input;
      let prevented = false;
      elements["sample-id-filter-form"].listeners.submit({ preventDefault() { prevented = true; } });
      assert.ok(prevented);
    },
  };
}

test("ID filtering combines with other filters and reports unmatched IDs safely within scope", () => {
  const h = setup();
  h.apply("LAB-A;uuid-3;LAB-A;<img src=x>");

  assert.deepEqual(h.visible(), ["uuid-1", "uuid-3"]);
  assert.equal(h.elements["sample-id-filter-summary"].textContent, "3 unique IDs entered; 2 matched (3 samples).");
  assert.equal(h.elements["sample-id-filter-unmatched-title"].textContent, "Not found in this group (1)");
  assert.equal(h.elements["sample-id-filter-unmatched-list"].children[0].textContent, "<img src=x>");
  assert.equal(h.elements["sample-id-filter-feedback"].hidden, false);
  assert.equal(h.elements["sample-id-filter-clear"].hidden, false);
  assert.equal(h.searchParent.children[0], h.elements["sample-id-filter-controls"]);
});

test("clear and empty input remove only the ID filter; reopening discards unapplied edits", () => {
  const h = setup("this table");
  h.apply("uuid-3");
  h.elements["sample-id-filter-input"].value = "cancelled draft";
  h.elements["sample-id-filter-modal"].listeners["show.bs.modal"]();
  assert.equal(h.elements["sample-id-filter-input"].value, "uuid-3");
  h.elements["sample-id-filter-modal"].listeners["shown.bs.modal"]();
  assert.ok(h.elements["sample-id-filter-input"].focused);

  for (const clear of [() => h.elements["sample-id-filter-clear"].listeners.click(), () => h.apply(" \n;,")]) {
    h.apply("uuid-3");
    clear();
    assert.deepEqual(h.visible(), ["uuid-1", "uuid-3"]);
    assert.deepEqual([...h.filters.keys()], ["otherFilter"]);
    assert.equal(h.elements["sample-id-filter-feedback"].hidden, true);
    assert.equal(h.elements["sample-id-filter-clear"].hidden, true);
  }
});

test("an entirely unmatched list shows no rows rather than clearing the filter", () => {
  const h = setup("this table");
  h.apply("missing");
  assert.deepEqual(h.visible(), []);
  assert.equal(h.elements["sample-id-filter-summary"].textContent, "1 unique ID entered; 0 matched (0 samples).");
  assert.equal(h.elements["sample-id-filter-unmatched-title"].textContent, "Not found in this table (1)");
});

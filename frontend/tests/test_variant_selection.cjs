// Run from frontend/: node --test tests/test_variant_selection.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

const source = fs.readFileSync(path.join(__dirname, "../web/js/views/variants-table/variants-view.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;

class ClickTarget {
  constructor(row, control) { this.row = row; this.control = control; }
  closest(selector) {
    if (selector === "tr") return this.row;
    return selector.split(", ").includes(this.control) ? this : null;
  }
}

function page(analysis, storage = new Map()) {
  function checkbox(dataset = {}) {
    const handlers = {};
    return { dataset, checked: true, disabled: false,
      addEventListener: (name, fn) => { handlers[name] = fn; },
      change(checked) { this.checked = checked; handlers.change?.(); },
      click() {
        this.change(!this.checked);
        bodyClick({ target: new ClickTarget(null, "input") });
      },
    };
  }
  const boxes = [0, 1].map(id => checkbox({ variantId: String(id), analysisId: analysis, analysisType: "amr" }));
  const header = checkbox(), unrelated = checkbox();
  let bodyClick;
  const body = {
    querySelectorAll: () => boxes,
    addEventListener: (name, fn) => { if (name === "click") bodyClick = fn; },
  };
  const input = { value: "stale" }, counter = { textContent: "9" };
  const ids = {
    "select-all-variants": header, "tbprofiler-variant-table": body,
    "curations-input": input, "selected-variants-counter": counter,
  };
  const exports = {};
  vm.runInNewContext(compiled, {
    exports,
    require: () => ({ initTooltip() {} }),
    Element: ClickTarget,
    document: {
      querySelector: () => null,
      querySelectorAll: selector => selector.startsWith("#tbprofiler-variant-table") ? [body]
        : selector.includes("data-variant-id") ? boxes : [...boxes, header, unrelated],
      getElementById: id => ids[id] || null,
    },
    localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  });
  exports.initVariantsView();
  return {
    boxes, header, unrelated, counter, payload: () => JSON.parse(input.value),
    clickRow(index, control) {
      const row = { querySelector: () => boxes[index] };
      bodyClick({ target: new ClickTarget(row, control) });
    },
  };
}

test("restored browser checkboxes and stale form selections are cleared together", () => {
  const p = page("analysis-a");
  assert.deepEqual(p.payload(), []);
  assert.ok(p.boxes.every(box => !box.checked));
  assert.equal(p.counter.textContent, "0");
});

test("selecting variants in another sample tab cannot change this tab's payload", () => {
  const storage = new Map();
  const a = page("analysis-a", storage), b = page("analysis-b", storage);
  a.boxes[0].change(true);
  b.boxes[0].change(true);
  a.boxes[1].change(true);
  assert.deepEqual(a.payload(), [0, 1].map(id => ({
    variant_id: String(id), analysis_id: "analysis-a", analysis_type: "amr",
  })));
  assert.deepEqual(b.payload(), [{ variant_id: "0", analysis_id: "analysis-b", analysis_type: "amr" }]);
});

test("select all submits each variant once, ignores unrelated inputs, and can clear selection", () => {
  const p = page("analysis-a");
  p.header.change(true);
  p.boxes[0].change(true);
  assert.equal(p.payload().length, 2);
  assert.equal(p.unrelated.checked, false);
  p.header.change(false);
  assert.deepEqual(p.payload(), []);
  assert.equal(p.counter.textContent, "0");
});

test("row text toggles its checkbox and updates the submitted selection once", () => {
  const p = page("analysis-a");
  p.clickRow(0);
  assert.equal(p.boxes[0].checked, true);
  assert.equal(p.payload()[0].variant_id, "0");
  assert.equal(p.counter.textContent, "1");
  p.clickRow(0);
  assert.equal(p.boxes[0].checked, false);
  assert.deepEqual(p.payload(), []);
});

test("row links, buttons, tooltips and form controls do not select a variant", () => {
  const p = page("analysis-a");
  for (const control of ["a", "button", "input", "select", "textarea", "label", "form", "[role='button']", "[data-bs-toggle]", "[contenteditable='true']"]) {
    p.clickRow(0, control);
    assert.deepEqual(p.payload(), [], control);
  }
  p.boxes[0].click();
  assert.equal(p.payload().length, 1);
  assert.equal(p.boxes[0].checked, true);
});

test("a disabled row checkbox cannot be selected by clicking its row", () => {
  const p = page("analysis-a");
  p.boxes[0].disabled = true;
  p.clickRow(0);
  assert.deepEqual(p.payload(), []);
});

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

function setup() {
  const events = [];
  let sortable;
  const search = { value: "", addEventListener(_, handler) { this.input = handler; } };
  const filter = { checked: true, addEventListener() {} };
  const list = { innerHTML: "" };
  class Element {
    querySelector(selector) {
      return { ".ge-columns-list": list, "input[type=search]": search, "#show-unselected": filter }[selector];
    }
    querySelectorAll(selector) {
      if (selector !== ".ge-column-item:not(.is-disabled)") return [];
      return [...list.innerHTML.matchAll(/class="list-group-item[^\"]*?\s*"\s+data-id="([^\"]+)"/g)]
        .filter(match => !match[0].includes("is-disabled"))
        .map(match => ({ dataset: { id: match[1] } }));
    }
    dispatchEvent(event) { events.push(event); }
  }
  const exports = {};
  const source = fs.readFileSync(path.join(__dirname, "../web/js/components/column-selector.ts"), "utf8");
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText, {
    exports, HTMLElement: Element, customElements: { define() {} },
    CustomEvent: class { constructor(type, init) { Object.assign(this, { type }, init); } },
    require: () => ({ create: (_list, options) => { sortable = options; } }),
  });
  const selector = new exports.ColumnSelector();
  selector.items = [
    { id: "sample_id", label: "ID", enabled: true },
    { id: "mlst", label: "MLST type", enabled: true },
    { id: "sample_name", label: "Name", enabled: true },
    { id: "stx", label: "STX type", enabled: true },
    { id: "qc", label: "QC", enabled: false },
  ];
  return {
    selector, events,
    search(value) { search.value = value; search.input(); },
    drag(ids) {
      list.innerHTML = ids.map(id => `<li class="list-group-item" data-id="${id}"></li>`).join("");
      sortable.onEnd();
    },
  };
}

test("dragging filtered columns keeps hidden selections in their original slots", () => {
  const h = setup();
  h.search("type");
  assert.deepEqual(Array.from(h.selector.querySelectorAll(".ge-column-item:not(.is-disabled)"), row => row.dataset.id), ["mlst", "stx"]);

  h.drag(["stx", "mlst"]);

  assert.deepEqual(Array.from(h.selector.items, item => item.id), ["sample_id", "stx", "sample_name", "mlst", "qc"]);
  assert.deepEqual(Array.from(h.events.at(-1).detail.items.filter(item => item.enabled), item => item.id), ["sample_id", "stx", "sample_name", "mlst"]);
  h.search("");
  assert.match(h.selector.querySelector(".ge-columns-list").innerHTML, /data-id="sample_id"/);
});

test("unfiltered dragging still reorders all selected columns and retains disabled choices", () => {
  const h = setup();
  h.drag(["stx", "sample_name", "mlst", "sample_id"]);

  assert.deepEqual(Array.from(h.selector.items, item => item.id), ["stx", "sample_name", "mlst", "sample_id", "qc"]);
  assert.equal(h.selector.items.at(-1).enabled, false);
});

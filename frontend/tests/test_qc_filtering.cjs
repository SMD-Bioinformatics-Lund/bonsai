// Run from frontend/: npm test
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const { JSDOM } = require("jsdom");
const ts = require("typescript");

const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
const { window } = dom;
global.Node = window.Node;
global.Option = window.Option;
Object.defineProperty(global, "navigator", { value: window.navigator, configurable: true });
const $ = require("jquery")(window);
const DataTable = require("datatables.net-bs5")(window, $);
require("datatables.net-searchbuilder-bs5")(window, $);

function readSource(relativePath) {
  const filename = path.join(__dirname, "../web/js", relativePath);
  return ts.createSourceFile(filename, fs.readFileSync(filename, "utf8"), ts.ScriptTarget.Latest, true);
}

function findDeclaration(source, name) {
  let declaration;
  function visit(node) {
    if (node.name?.getText(source) === name && (
      ts.isVariableDeclaration(node) || ts.isFunctionDeclaration(node) || ts.isClassDeclaration(node)
    )) declaration = node;
    ts.forEachChild(node, visit);
  }
  visit(source);
  assert.ok(declaration, `Missing production declaration: ${name}`);
  return declaration;
}

// Load the actual table configuration, QC updater and controller. Leave unrelated
// page widgets out of the harness; filtering runs through the real libraries.
const groupSource = readSource("views/groups-view/init.ts");
const controllerSource = readSource("utils/table-controller.ts");
const code = `
  const sampleTableConfig = ${findDeclaration(groupSource, "sampleTableConfig").initializer.getText(groupSource)};
  ${findDeclaration(controllerSource, "TableController").getText(controllerSource)}
  ${findDeclaration(groupSource, "updateQcTableCells").getText(groupSource)}
  exports.getConfig = (headers) => (${findDeclaration(groupSource, "tableConfig").initializer.getText(groupSource)});
  exports.updateQcTableCells = updateQcTableCells;
`;
const production = {};
vm.runInNewContext(ts.transpileModule(code, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, {
  exports: production, DataTable, document: window.document, initTooltip() {}, console,
});

const specialNames = ["A&B", "A<B", "A>B", 'A"B', "A'B"];
const samples = [
  ...specialNames.map((name, index) => ({ id: `sample-${index}`, name, status: "passed" })),
  { id: "sample-failed", name: "Failed sample", status: "failed" },
  { id: "sample-pending", name: "Pending sample", status: "unprocessed" },
];
const escape = (value) => value.replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");

function setup(t, { qcFirst = false, hideQc = false, includeQc = true } = {}) {
  const nameColumn = { id: "sample_name", label: "Name", searchable: true };
  const qcColumn = { id: "qc_status", label: "QC", searchable: false };
  const columns = !includeQc ? [nameColumn] : qcFirst ? [qcColumn, nameColumn] : [nameColumn, qcColumn];
  window.document.body.innerHTML = `<table id="sample-table"><thead><tr>${columns.map(column =>
    `<th data-column-id="${column.id}" data-filterable="true" data-searchable="${column.searchable}"
      data-visible="${column.id !== "qc_status" || !hideQc}">${column.label}</th>`
  ).join("")}</tr></thead><tbody>${samples.map(sample =>
    `<tr id="${sample.id}">${columns.map(column => column.id === "qc_status"
      ? `<td data-search="${sample.status}">\n<span class="fw-light">${sample.status}</span>\n<i
          data-bs-title="Comment mentioning passed, failed and unprocessed"></i>\n</td>`
      : `<td>${escape(sample.name)}</td>`).join("")}</tr>`
  ).join("")}</tbody></table>`;
  const config = production.getConfig(window.document.querySelectorAll("th"));
  const controller = new production.TableController("sample-table", {
    ...config, layout: { top1: "searchBuilder" }, paging: false, order: [],
  });
  const table = controller.getTable();
  t.after(() => table.destroy());
  return {
    table, controller,
    filter(columnId, condition, value) {
      const index = columns.findIndex(column => column.id === columnId);
      assert.notEqual(index, -1);
      table.searchBuilder.rebuild({ logic: "AND", criteria: [{
        data: columns[index].label, origData: index, condition, value: [value], type: "string",
      }] });
    },
    visibleIds: () => table.rows({ search: "applied" }).ids().toArray(),
    qcCell: (sampleId) => table.cell(`#${sampleId}`, columns.findIndex(column => column.id === "qc_status")).node(),
  };
}

for (const name of specialNames) {
  test(`advanced text filtering matches the visible name ${name}`, (t) => {
    const page = setup(t);
    page.filter("sample_name", "contains", name);
    assert.deepEqual(page.visibleIds(), samples.filter(sample => sample.name === name).map(sample => sample.id));
  });
}

for (const status of ["passed", "failed", "unprocessed"]) {
  test(`QC equals ${status} matches only that status despite global-search exclusion`, (t) => {
    const page = setup(t);
    page.filter("qc_status", "=", status);
    assert.deepEqual(page.visibleIds(), samples.filter(sample => sample.status === status).map(sample => sample.id));
  });
}

for (const [sampleId, previous, next] of [
  ["sample-0", "passed", "failed"], ["sample-failed", "failed", "passed"],
]) {
  test(`a QC edit from ${previous} to ${next} refreshes the active filter`, (t) => {
    const page = setup(t);
    page.filter("qc_status", "=", previous);
    production.updateQcTableCells(page.controller, {
      status: next, action: next === "failed" ? "resequence" : null,
      comment: next === "failed" ? "Review coverage" : "",
    }, [sampleId]);

    assert.deepEqual(page.visibleIds(), samples
      .filter(sample => sample.status === previous && sample.id !== sampleId).map(sample => sample.id));
    const cell = page.qcCell(sampleId);
    assert.equal(cell.dataset.search, next);
    assert.equal(cell.querySelector("span").textContent, next);
    assert.ok(cell.querySelector(`.text-${next === "passed" ? "success" : "danger"}`));
    if (next === "failed") {
      assert.equal(cell.querySelector("i").dataset.bsTitle, "Action: resequence - Review coverage");
    } else {
      assert.equal(cell.querySelector("i"), null);
    }
    page.filter("qc_status", "=", next);
    assert.deepEqual(new Set(page.visibleIds()), new Set([
      ...samples.filter(sample => sample.status === next).map(sample => sample.id), sampleId,
    ]));
  });
}

test("QC filtering follows the column ID when columns move", (t) => {
  const page = setup(t, { qcFirst: true });
  page.filter("qc_status", "=", "failed");
  assert.deepEqual(page.visibleIds(), ["sample-failed"]);
  page.filter("sample_name", "contains", "A&B");
  assert.deepEqual(page.visibleIds(), ["sample-0"]);
});

test("QC filtering still works when the QC column is hidden", (t) => {
  const page = setup(t, { hideQc: true });
  assert.equal(page.table.column(1).visible(), false);
  page.filter("qc_status", "=", "unprocessed");
  assert.deepEqual(page.visibleIds(), ["sample-pending"]);
});

test("a table without QC retains normal text filtering", (t) => {
  const page = setup(t, { includeQc: false });
  page.filter("sample_name", "contains", "A&B");
  assert.deepEqual(page.visibleIds(), ["sample-0"]);
});

test("global search still excludes QC and matches decoded names", (t) => {
  const page = setup(t);
  page.table.search("unprocessed").draw();
  assert.deepEqual(page.visibleIds(), []);
  page.table.search("A&B").draw();
  assert.deepEqual(page.visibleIds(), ["sample-0"]);
});

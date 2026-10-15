// Run from frontend: node --test tests/test_overview_table.cjs
// Use the existing TypeScript dependency and Node's test runner.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const ts = require("typescript");

function load(filename, requireModule = () => ({}), globals = {}) {
  const compiled = ts.transpileModule(
    fs.readFileSync(path.join(__dirname, "../web/js", filename), "utf8"),
    { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } },
  );
  const exports = {};
  new Function("exports", "require", ...Object.keys(globals), compiled.outputText)(
    exports, requireModule, ...Object.values(globals),
  );
  return exports;
}

test("overview keeps server formatting and sort/search overrides, aligning columns by ID", async () => {
  const data = {
    columns: [
      { id: "tags", sortable: true, searchable: false, visible: true, filterable: true },
      { id: "date", sortable: true, searchable: true, visible: false, filterable: false },
    ],
    rows: [{ sample_id: "sample-1", cells: [{ display: "<b>Flag</b>", filter: "Flag " },
      { display: "2026-10-15", sort: "2026-10-15T12:34:56" }] }],
  };
  const headers = ["date", "tags"].map((columnId) => ({ dataset: { columnId } }));
  const table = { dataset: { source: "/bonsai/groups/samples-data" }, querySelectorAll: () => headers };
  const { loadOverviewTable } = load("views/groups-view/overview-data.ts", undefined, {
    fetch: async (url, options) => {
      assert.equal(url, table.dataset.source);
      assert.equal(options.credentials, "same-origin");
      return { ok: true, json: async () => data };
    },
  });
  const config = await loadOverviewTable(table);
  assert.equal(config.deferRender, true);
  assert.equal(config.rowId, "sample_id");
  assert.deepEqual(config.data, data.rows);
  assert.equal(config.columns[0].data, "cells.1");
  assert.equal(config.columns[0].visible, false);
  assert.equal(headers[1].dataset.filterable, "true");
  const date = data.rows[0].cells[1];
  for (const type of ["sort", "type"]) {
    assert.equal(config.columns[0].render(date, type), date.sort);
  }
  for (const type of ["display", "filter", "export"]) {
    assert.equal(config.columns[0].render(date, type), date.display);
  }
  assert.equal(config.columns[1].render(data.rows[0].cells[0], "filter"), "Flag ");
  assert.equal(config.columns[1].render(data.rows[0].cells[0], "export"), "<b>Flag</b>");
});

test("failed requests and mismatched columns fail explicitly", async () => {
  const table = { dataset: { source: "/data" }, querySelectorAll: () => [{ dataset: { columnId: "missing" } }] };
  for (const response of [
    { ok: false, status: 503 },
    { ok: true, json: async () => ({ columns: [], rows: [] }) },
  ]) {
    const { loadOverviewTable } = load("views/groups-view/overview-data.ts", undefined,
      { fetch: async () => response });
    await assert.rejects(loadOverviewTable(table), /503|Missing summary column/);
  }
});

function controllerFixture(deferred, hasNode) {
  const sourceCell = { display: "unprocessed" };
  const node = hasNode ? { innerHTML: sourceCell.display } : null;
  const draws = [];
  const selected = ["sample-1", "sample-51"];
  const cell = {
    any: () => true, node: () => node,
    data: (value) => Object.assign(sourceCell, value),
    invalidate: (source) => {
      assert.equal(source, "dom");
      sourceCell.display = node.innerHTML;
    },
  };
  const api = {
    table: () => ({ node: () => ({ dataset: deferred ? { source: "/data" } : {} }) }),
    columns: () => ({ header: () => ({ toArray: () => [{ dataset: { columnId: "qc_status" } }] }) }),
    cell: (id, index) => {
      assert.equal(id, "#sample-51");
      assert.equal(index, 0);
      return cell;
    },
    draw: (reset) => draws.push(reset),
    rows: (selector) => {
      assert.deepEqual(selector, { selected: true });
      return { ids: () => ({ toArray: () => selected }) };
    },
  };
  class DataTable { constructor() { return api; } }
  DataTable.Buttons = { jszip: () => {} };
  const { TableController } = load("utils/table-controller.ts",
    (name) => name === "datatables.net-bs5" ? { default: DataTable } : {},
    { document: { createElement: () => ({ innerHTML: "" }) } });
  return { controller: new TableController("sample-table", {}), sourceCell, draws, selected };
}

test("selected rows include IDs whose DOM rows have not been created", () => {
  const { controller, selected } = controllerFixture(true, false);
  assert.deepEqual(controller.getSelectedRows(), selected);
});

test("QC updates persist for both deferred and existing DOM cells without resetting the page", () => {
  for (const [deferred, hasNode] of [[true, false], [true, true], [false, true]]) {
    const { controller, sourceCell, draws } = controllerFixture(deferred, hasNode);
    controller.updateCells(["sample-51"], "qc_status", (cell) => {
      cell.innerHTML = '<span class="text-danger">failed</span>';
    });
    assert.equal(sourceCell.display, '<span class="text-danger">failed</span>');
    assert.deepEqual(draws, [false]);
  }
});

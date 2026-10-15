// Run with: node --test tests/test_summary_renderers.cjs (from frontend/).
// Transpile the small renderer module with the existing TypeScript dependency.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const ts = require("typescript");

const filename = path.join(__dirname, "../web/js/views/groups-view/sample-table-data.ts");
const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
});
const moduleExports = {};
new Function("exports", compiled.outputText)(moduleExports);
const { renderSummaryCell: render, loadOverviewTable } = moduleExports;

test("sample values are text in display cells and plain data in exports", () => {
  const column = { id: "sample_name", type: "string" };
  const value = '<img src=x onerror="alert(1)">';
  assert.equal(
    render(column, value, "display", ""),
    "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;",
  );
  assert.equal(render(column, value, "filter", ""), value);
  assert.equal(render(column, value, "sort", ""), value);
});

test("sample links retain the deployment prefix and encode the ID", () => {
  assert.equal(
    render(
      { id: "sample_id", type: "string" },
      "a/b",
      "display",
      "/staging/bonsai/sample/__sample_id__",
    ),
    '<a href="/staging/bonsai/sample/a%2Fb">Open</a>',
  );
});

test("numbers and dates keep sortable values while formatting display values", () => {
  const number = { id: "n50", type: "number" };
  assert.equal(render(number, 2000000, "display", ""), "2,000,000");
  assert.equal(render(number, 2000000, "sort", ""), 2000000);
  assert.equal(render(number, 0, "sort", ""), 0);
  assert.equal(render(number, null, "sort", ""), "");
  const date = { id: "created_at", type: "date" };
  assert.equal(render(date, "2026-10-15T12:00:00Z", "display", ""), "2026-10-15");
  assert.equal(render(date, "2026-10-15T12:00:00Z", "sort", ""), "2026-10-15T12:00:00Z");
  assert.equal(render(date, "2026-10-15T12:00:00Z", "filter", ""), "2026-10-15");
});

test("QC, group and tag markup escapes text and tooltip attributes", () => {
  const qc = render(
    { id: "qc_status", type: "object" },
    {
      status: "failed",
      action: "resequence",
      comment: '"><script>',
    },
    "display",
    "",
  );
  assert.ok(qc.includes("text-danger"));
  assert.ok(qc.includes("Action: resequence - &quot;&gt;&lt;script&gt;"));
  const groups = render(
    { id: "groups", type: "object" },
    [{ id: '" onmouseover="alert(1)', display_name: "<script>" }],
    "display",
    "",
  );
  assert.ok(groups.includes("&lt;script&gt;"));
  assert.ok(groups.includes("&quot; onmouseover=&quot;"));
  assert.equal(
    render(
      { id: "tags", type: "object" },
      [{ label: "Flag", severity: "warning", description: "<script>" }],
      "filter",
      "",
    ),
    "Flag",
  );
});

test("HTML comment tooltips escape content at both nesting levels", () => {
  const column = { id: "comments", type: "object" };
  const comments = [
    { comment: "<img src=x>", username: '"<script>', displayed: true },
    { comment: "hidden", username: "author", displayed: false },
  ];
  const html = render(column, comments, "display", "");
  assert.ok(html.includes('data-bs-html="true"'));
  assert.ok(html.includes("&amp;lt;img"));
  assert.ok(!html.includes("<img"));
  assert.ok(!html.includes("hidden"));
  assert.equal(render(column, comments, "filter", ""), '<img src=x> "<script>');
});

test("overview loading uses IDs to align columns and enables deferred rendering", async () => {
  const originalFetch = global.fetch;
  const headers = ["sample_id", "sample_name"].map((id) => ({ dataset: { columnId: id } }));
  const table = {
    dataset: { source: "/groups/samples-data", sampleUrl: "/sample/__sample_id__" },
    querySelectorAll: () => headers,
  };
  try {
    global.fetch = async () => ({
      ok: true,
      json: async () => ({
        columns: [
          { id: "sample_name", type: "string", filterable: true },
          { id: "sample_id", type: "string", filterable: false },
        ],
        rows: [{ sample_id: "a", sample_name: "Isolate" }],
      }),
    });
    const config = await loadOverviewTable(table);
    assert.equal(config.deferRender, true);
    assert.equal(config.rowId, "sample_id");
    assert.deepEqual(
      config.columns.map((column) => column.data),
      ["sample_id", "sample_name"],
    );
    assert.equal(headers[1].dataset.filterable, "true");

    global.fetch = async () => ({ ok: false, status: 503 });
    await assert.rejects(loadOverviewTable(table), /503/);
  } finally {
    global.fetch = originalFetch;
  }
});

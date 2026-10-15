const { test, expect } = require("@playwright/test");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const webpack = require("webpack");

let bundle;
test.beforeAll(async () => {
  const output = fs.mkdtempSync(path.join(os.tmpdir(), "bonsai-table-browser-"));
  bundle = path.join(output, "fixture.js");
  await new Promise((resolve, reject) => {
    const compiler = webpack({
      mode: "development",
      devtool: false,
      entry: path.join(__dirname, "table-fixture.ts"),
      output: { path: output, filename: "fixture.js" },
      resolve: { extensions: [".ts", ".js"] },
      module: { rules: [{ test: /\.ts$/, loader: "ts-loader", options: { transpileOnly: true } }] },
      plugins: [new webpack.ProvidePlugin({ process: "process/browser" })],
    });
    compiler.run((error, stats) =>
      compiler.close(() => {
        if (error || stats.hasErrors()) reject(error || new Error(stats.toString("errors-only")));
        else resolve();
      }),
    );
  });
});

const columns = [
  { id: "sample_id", type: "string", renderer: "sample_btn_renderer", searchable: false },
  { id: "sample_name", type: "string", renderer: "text_renderer", searchable: true },
  { id: "qc_status", type: "object", renderer: "qc_status_renderer", searchable: false },
].map((column) => ({ ...column, sortable: true, visible: true, filterable: false }));
const rows = Array.from({ length: 60 }, (_, index) => ({
  sample_id: `sample-${index}`,
  sample_name: `${index % 2 === 0 ? "included" : "excluded"} ${index}`,
  qc_status: { status: "unprocessed", action: null, comment: null },
}));

async function mount(page, { source = "summary", failOnce = false } = {}) {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("http://table.test/", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<div id="sample-table-loading">Loading samples...</div>
      <div id="sample-table-container" class="d-none">
      <table id="sample-table" ${source === "summary" ? 'data-source="/data" data-sample-url="/sample/__sample_id__"' : ""}>
      <thead><tr>${columns.map((column) => `<th data-column-id="${column.id}" data-filterable="false">${column.id}</th>`).join("")}</tr></thead>
      <tbody>${source === "dom" ? rows.map((row) => `<tr id="${row.sample_id}"><td>Open</td><td>${row.sample_name}</td><td>unprocessed</td></tr>`).join("") : ""}</tbody>
      </table></div><script src="/fixture.js"></script><script>tableTest.start()</script>`,
    }),
  );
  await page.route("http://table.test/fixture.js", (route) =>
    route.fulfill({ path: bundle, contentType: "text/javascript" }),
  );
  let requests = 0;
  await page.route("http://table.test/data", (route) => {
    requests += 1;
    return requests === 1 && failOnce
      ? route.fulfill({ status: 503, body: "Unavailable" })
      : route.fulfill({ json: { columns, rows } });
  });
  await page.goto("http://table.test/");
  return errors;
}

test("unvisited rows retain selection and bulk QC updates when paged into view", async ({
  page,
}) => {
  const errors = await mount(page);
  await expect(page.locator("#sample-table tbody tr")).toHaveCount(10);
  expect(await page.evaluate(() => tableTest.api().row("#sample-51").node())).toBeNull();
  await page.evaluate(() => tableTest.select(["sample-1", "sample-51"]));
  expect(await page.evaluate(() => tableTest.selected())).toEqual(["sample-1", "sample-51"]);
  await page.evaluate(() => tableTest.qc());
  expect(await page.evaluate(() => tableTest.api().row("#sample-51").node())).toBeNull();
  await page.evaluate(() => tableTest.api().page(5).draw("page"));
  await expect(page.locator("#sample-51")).toHaveClass(/selected/);
  await expect(page.locator("#sample-51 td").nth(2)).toContainText("failed");
  await expect(page.locator("#sample-51 [data-bs-toggle=tooltip]")).toHaveAttribute(
    "data-bs-title",
    "Action: resequence - Needs another run",
  );
  expect(await page.evaluate(() => tableTest.selected())).toHaveLength(2);
  await page.evaluate(() => tableTest.qc());
  expect(await page.evaluate(() => tableTest.api().page())).toBe(5);
  expect(errors).toEqual([]);
});

test("filtered select-all includes unrendered matches and exports updated values", async ({
  page,
}) => {
  const errors = await mount(page);
  await expect(page.locator("#sample-table tbody tr")).toHaveCount(10);
  await page.evaluate(() => {
    tableTest.api().column(1).search("included").draw();
    tableTest.api().button(".buttons-select-all").trigger();
  });
  expect(await page.evaluate(() => tableTest.selected())).toHaveLength(30);
  expect(
    await page.evaluate(() =>
      tableTest.selected().every((id) => Number(id.split("-")[1]) % 2 === 0),
    ),
  ).toBe(true);
  await page.evaluate(() => tableTest.qc());
  const exported = await page.evaluate(
    () =>
      tableTest.api().buttons.exportData({
        orthogonal: "export",
        modifier: { selected: true },
      }).body,
  );
  expect(exported).toHaveLength(30);
  expect(exported.every((row) => row[0].startsWith("sample-") && row[2] === "failed")).toBe(true);
  expect(await page.evaluate(() => tableTest.api().row("#sample-59").data().qc_status.status)).toBe(
    "unprocessed",
  );
  expect(errors).toEqual([]);
});

test("legacy Jinja tables keep off-page selection and QC updates", async ({ page }) => {
  const errors = await mount(page, { source: "dom" });
  await expect(page.locator("#sample-table tbody tr")).toHaveCount(10);
  await page.evaluate(() => {
    tableTest.select(["sample-1", "sample-51"]);
    tableTest.qc();
    tableTest.api().page(5).draw("page");
  });
  await expect(page.locator("#sample-51")).toHaveClass(/selected/);
  await expect(page.locator("#sample-51 td").nth(2)).toContainText("failed");
  expect(await page.evaluate(() => tableTest.selected())).toHaveLength(2);
  expect(errors).toEqual([]);
});

test("a failed data request offers a working retry", async ({ page }) => {
  const errors = await mount(page, { failOnce: true });
  await expect(page.locator("#sample-table-loading")).toContainText("Unable to load samples");
  expect(await page.evaluate(() => tableTest.api())).toBeUndefined();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.locator("#sample-table tbody tr")).toHaveCount(10);
  await expect(page.locator("#sample-table-loading")).toHaveCount(0);
  expect(errors).toEqual([]);
});

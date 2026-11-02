// Run from frontend/: node --test tests/test_sample_actions.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

const uuid = "01a16798-d07e-7110-aeaf-25664a6bd39d";
class ApiError extends Error {
  constructor(message, data) {
    super(message);
    this.data = data;
  }
}

function setup({ ids = [uuid], confirm = true, error, submissionFails = false } = {}) {
  const toasts = [], logs = [], prompts = [], deleted = [], removed = [];
  let hidden = 0;
  const spinner = { show() {}, hide() { hidden++; } };
  const container = { querySelector: selector => selector === "spinner-element" ? spinner : { value: "0.5" } };
  const api = {
    deleteSamples: async samples => { deleted.push(samples); },
    findSimilarSamples: async () => { if (submissionFails) throw error; return { id: "job" }; },
    checkJobStatus: async () => { throw error; },
  };
  const table = {
    getSelectedRows: () => ids,
    removeSamples: samples => removed.push(samples),
    getTable: () => ({
      columns: () => ({ header: () => ({ toArray: () => [{ dataset: { columnId: "sample_name" } }] }) }),
      cell: () => ({ node: () => ({ textContent: "Readable sample name" }) }),
    }),
  };
  const exports = {};
  const source = fs.readFileSync(path.join(__dirname, "../web/js/core/actions/sample-actions.ts"), "utf8");
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, {
    exports, Error,
    require: () => ({
      ApiError, pollJob: fn => fn(),
      throwSmallToast: (...args) => toasts.push(args),
      showSpinner() {}, hideSpinner: () => { hidden++; }, emitEvent() {},
      TypingMethod: { MINHASH: "minhash" }, ClusterMethod: { SINGLE: "single" },
    }),
    console: { error: (...args) => logs.push(args), log() {} },
    window: { confirm: message => { prompts.push(message); return confirm; } },
    document: { getElementById: () => container },
  });
  return { actions: exports, api, table, toasts, logs, prompts, deleted, removed,
    btn: { closest: () => container }, hidden: () => hidden };
}

test("empty selections and cancelled confirmation never submit deletion", () => {
  for (const options of [{ ids: [] }, { confirm: false }]) {
    const h = setup(options);
    h.actions.deleteSelectedSamples(h.table, h.api);
    assert.equal(h.deleted.length, 0);
    assert.equal(h.removed.length, 0);
    assert.equal(h.prompts.length, options.ids ? 0 : 1);
  }
});

test("confirmed deletion shows names/count without UUIDs and submits selected IDs", async () => {
  const h = setup();
  h.actions.deleteSelectedSamples(h.table, h.api);
  await new Promise(resolve => setImmediate(resolve));
  assert.match(h.prompts[0], /1 selected sample/);
  assert.match(h.prompts[0], /Readable sample name/);
  assert.ok(!h.prompts[0].includes(uuid));
  assert.deepEqual(h.deleted, [[uuid]]);
  assert.deepEqual(h.removed, [[uuid]]);
});

for (const view of ["table", "detail"]) {
  for (const submissionFails of [false, true]) {
    test(`${view} similarity handles ${submissionFails ? "submission" : "worker"} errors without leaking UUIDs`, async () => {
      const error = new Error(`No record found for sample_id: "${uuid}"`);
      const h = setup({ error, submissionFails });
      if (view === "table") await h.actions.getSimilarSamplesAndCheckRows(h.btn, h.table, h.api, null);
      else await h.actions.findAndClusterSimilarSamples(uuid, null, h.api);
      assert.match(h.toasts[0][0], /Similarity data is not available/);
      assert.equal(h.toasts[0][1], "warning");
      assert.ok(!h.toasts[0][0].includes(uuid));
      assert.ok(h.logs[0].includes(uuid) && h.logs[0].includes(error));
      assert.equal(h.hidden(), 1);
    });
  }
}

test("unexpected API details stay in the console", async () => {
  const error = new ApiError(`Failed for ${uuid}`, { title: `Sample ${uuid}`, detail: `Unknown error ${uuid}` });
  const h = setup({ error, submissionFails: true });
  await h.actions.getSimilarSamplesAndCheckRows(h.btn, h.table, h.api, null);
  assert.match(h.toasts[0][0], /contact the server administrator/);
  assert.ok(!h.toasts[0][0].includes(uuid));
  assert.ok(h.logs[0].includes(error));
});

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
  const toasts = [], logs = [], prompts = [], deleted = [], removed = [], groupRemovals = [], events = [];
  let hidden = 0;
  const spinner = { show() {}, hide() { hidden++; } };
  const container = { querySelector: selector => selector === "spinner-element" ? spinner : { value: "0.5" } };
  const api = {
    deleteSamples: async samples => { deleted.push(samples); },
    removeSamplesFromGroup: async (groupId, samples) => {
      if (error) throw error;
      groupRemovals.push([groupId, samples]);
    },
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
      showSpinner() {}, hideSpinner: () => { hidden++; },
      emitEvent: (...args) => events.push(args),
      TypingMethod: { MINHASH: "minhash" }, ClusterMethod: { SINGLE: "single" },
    }),
    console: { error: (...args) => logs.push(args), log() {} },
    window: { confirm: message => { prompts.push(message); return confirm; } },
    document: { getElementById: () => container },
  });
  return { actions: exports, api, table, toasts, logs, prompts, deleted, removed, groupRemovals, events,
    btn: { closest: () => container }, hidden: () => hidden };
}

function setupQcReset({ action = "", comment = "", submit = async (_sampleId, data) => data } = {}) {
  const { actions } = setup();
  const reset = { value: "unprocessed", checked: true, defaultChecked: true };
  const actionField = { value: action };
  const commentField = { value: comment };
  const confirm = { disabled: true };
  const fields = {
    "#passed-qc-btn": {},
    "#failed-qc-btn": {},
    "#unprocessed-qc-btn": reset,
    "#failed-qc-action": actionField,
    "#failed-qc-comment-container": { querySelector: () => commentField },
    "#qc-submit-btn": confirm,
    "input[name='qc-validation']:checked": reset,
  };
  const requests = [];
  actions.initSetSampleQc(() => [uuid], (sampleId, data) => {
    requests.push([sampleId, { ...data }]);
    return submit(sampleId, data);
  }, () => {}, { querySelector: (selector) => fields[selector] });
  return { reset, confirm, commentField, requests };
}

test("reselecting Unprocessed enables Confirm only when there are details to clear", async () => {
  const clean = setupQcReset();
  clean.reset.onclick();
  assert.ok(clean.confirm.disabled);

  for (const details of [{ action: "resequence" }, { comment: "Previous failure" }]) {
    const h = setupQcReset(details);
    h.reset.onclick();
    assert.equal(h.confirm.disabled, false);
    assert.deepEqual(h.requests, []);

    await h.confirm.onclick({ preventDefault() {} });
    assert.deepEqual(h.requests, [[uuid, { status: "unprocessed", action: null, comment: "" }]]);
    assert.equal(h.commentField.value, "");
    h.reset.onclick();
    assert.ok(h.confirm.disabled);
  }
});

test("clearing details from Unprocessed can be retried after a failed save", async () => {
  let rejectFirst;
  const firstRequest = new Promise((_, reject) => { rejectFirst = reject; });
  const h = setupQcReset({
    action: "resequence",
    submit: async (_sampleId, data) => h.requests.length === 1 ? firstRequest : data,
  });

  h.reset.onclick();
  const firstSave = h.confirm.onclick({ preventDefault() {} });
  h.reset.onclick();
  assert.ok(h.confirm.disabled);
  rejectFirst(new Error("QC save failed"));
  await firstSave;

  assert.equal(h.confirm.disabled, false);
  await h.confirm.onclick({ preventDefault() {} });
  assert.deepEqual(h.requests[1], h.requests[0]);
  assert.ok(h.confirm.disabled);
});

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

test("empty selections and cancelled group removal leave memberships and selection unchanged", () => {
  for (const options of [{ ids: [] }, { confirm: false }]) {
    const h = setup(options);
    h.actions.removeSamplesFromGroup("group-1", h.table, h.api);
    assert.equal(h.groupRemovals.length, 0);
    assert.equal(h.removed.length, 0);
    assert.equal(h.events.length, 0);
    assert.equal(h.prompts.length, options.ids ? 0 : 1);
    assert.equal(h.table.selectedRows, undefined);
  }
});

test("confirmed group removal explains scope and removes only the selected memberships", async () => {
  const h = setup({ ids: [uuid, "sample-2"] });
  h.actions.removeSamplesFromGroup("group-1", h.table, h.api);
  await new Promise(resolve => setImmediate(resolve));

  assert.match(h.prompts[0], /2 selected samples from this group/);
  assert.match(h.prompts[0], /samples will remain in Bonsai/);
  assert.ok(!h.prompts[0].includes(uuid));
  assert.deepEqual(h.groupRemovals, [["group-1", [uuid, "sample-2"]]]);
  assert.deepEqual(h.removed, [[uuid, "sample-2"]]);
  assert.deepEqual(Array.from(h.table.selectedRows), []);
  assert.equal(h.events[0][0], "samples:group-memberships-changed");
  assert.equal(h.deleted.length, 0);
});

test("failed group removal preserves table rows and selection", async () => {
  const h = setup({ error: new Error("Removal failed") });
  h.actions.removeSamplesFromGroup("group-1", h.table, h.api);
  await new Promise(resolve => setImmediate(resolve));

  assert.equal(h.removed.length, 0);
  assert.equal(h.events.length, 0);
  assert.equal(h.table.selectedRows, undefined);
  assert.equal(h.toasts.at(-1)[1], "error");
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

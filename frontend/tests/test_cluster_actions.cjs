// Run from frontend/: node --test tests/test_cluster_actions.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

class ApiError extends Error {
  constructor(message, data) {
    super(message);
    this.data = data;
  }
}

function loadModule(relativePath, dependencies) {
  const exports = {};
  const source = fs.readFileSync(path.join(__dirname, relativePath), "utf8");
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, { exports, Error, ...dependencies });
  return exports;
}

function setup({ error = "ValueError: Duplicate names found", submissionError, typingMethod = "ska" } = {}) {
  const sampleIds = ["sample-id-1", "sample-id-2", "sample-id-3", "sample-id-4"];
  const toasts = [], logs = [], requests = [];
  let hidden = 0;
  const button = {};
  const { pollJob } = loadModule("../web/js/core/api/polling/pollJob.ts", {
    require: () => ({ JobStatusEnum: { FINISHED: "finished", FAILED: "failed" } }),
  });
  const actions = loadModule("../web/js/core/actions/cluster-actions.ts", {
    require: () => ({
      ApiError, pollJob,
      TypingMethod: { SKA: "ska", MINHASH: "minhash" },
      DistanceMethod: { HAMMING: "hamming" }, ClusterMethod: { SINGLE: "single" },
      throwSmallToast: (...args) => toasts.push(args),
      showSpinner() {}, hideSpinner: () => { hidden++; },
    }),
    console: { error: (...args) => logs.push(args) },
    document: { querySelector: () => ({ querySelector: () => button }) },
  });
  const element = { getAttribute: () => typingMethod };
  const api = {
    clusterSamples: async (...args) => {
      requests.push(args);
      if (submissionError) throw submissionError;
      return { id: "job" };
    },
    checkJobStatus: async () => ({ status: "failed", error }),
  };
  return { actions, api, element, sampleIds, toasts, logs, requests, hidden: () => hidden };
}

test("failed SNV job explains duplicate sequence IDs and logs diagnostics", async () => {
  const h = setup();
  await h.actions.clusterSamples(h.element, h.sampleIds, h.api);

  const [message, severity] = h.toasts.at(-1);
  assert.match(message, /SNV clustering failed for 4 selected samples/);
  assert.match(message, /duplicate sequence IDs/);
  assert.match(message, /contact the server administrator/);
  assert.ok(!message.includes("ValueError"));
  assert.ok(h.sampleIds.every(id => !message.includes(id)));
  assert.equal(severity, "error");
  const diagnostics = h.logs[0][1];
  assert.equal(diagnostics.typingMethod, "ska");
  assert.equal(diagnostics.sampleIds, h.sampleIds);
  assert.equal(diagnostics.error.message, "ValueError: Duplicate names found");
  assert.equal(h.requests[0][1].sampleIds, h.sampleIds);
  assert.equal(h.hidden(), 1);
});

test("SNV duplicate names returned during submission use the same message", async () => {
  const h = setup({ submissionError: new ApiError("Request failed", { detail: "Duplicate names found" }) });
  await h.actions.clusterSamples(h.element, h.sampleIds, h.api);
  assert.match(h.toasts.at(-1)[0], /duplicate sequence IDs/);
  assert.equal(h.hidden(), 1);
});

test("other worker and API errors retain their messages", async () => {
  for (const options of [
    { error: "No SKA index file is available" },
    { typingMethod: "minhash" },
    { submissionError: new ApiError("Request failed", { detail: "No SKA index is available" }) },
  ]) {
    const h = setup(options);
    await h.actions.clusterSamples(h.element, h.sampleIds, h.api);
    assert.equal(h.toasts.at(-1)[0], options.submissionError?.data.detail ?? options.error ?? "ValueError: Duplicate names found");
    assert.equal(h.hidden(), 1);
  }
});

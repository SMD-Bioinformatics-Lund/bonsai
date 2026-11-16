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

function setup({
  error = "ValueError: Duplicate names found", submissionError, typingMethod = "ska",
  sampleIds = ["sample-id-1", "sample-id-2", "sample-id-3", "sample-id-4"],
  samples = [], lookupError,
} = {}) {
  const toasts = [], logs = [], requests = [], lookups = [];
  let hidden = 0;
  const button = {};
  const { pollJob } = loadModule("../web/js/core/api/polling/pollJob.ts", {
    require: () => ({ JobStatusEnum: { FINISHED: "finished", FAILED: "failed" } }),
  });
  const actions = loadModule("../web/js/core/actions/cluster-actions.ts", {
    require: () => ({
      ApiError, pollJob,
      TypingMethod: { SKA: "ska", MINHASH: "minhash", MLST: "mlst", CGMLST: "cgmlst" },
      DistanceMethod: { HAMMING: "hamming" }, ClusterMethod: { SINGLE: "single" },
      throwSmallToast: (...args) => toasts.push(args),
      showSpinner() {}, hideSpinner: () => { hidden++; },
    }),
    console: { error: (...args) => logs.push(args) },
    document: { querySelector: () => ({ querySelector: () => button }) },
  });
  const element = { getAttribute: () => typingMethod };
  const api = {
    getSamplesDetails: async (query) => {
      lookups.push(query);
      if (lookupError) throw lookupError;
      return { data: samples };
    },
    clusterSamples: async (...args) => {
      requests.push(args);
      if (submissionError) throw submissionError;
      return { id: "job" };
    },
    checkJobStatus: async () => ({ status: "failed", error }),
  };
  return { actions, api, element, sampleIds, toasts, logs, requests, lookups, hidden: () => hidden };
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

test("missing data lists up to four Lab IDs and summarizes five without a lookup", async () => {
  for (const [typingMethod, prefix, reason, worker] of [
    ["cgmlst", "No cgMLST typing profile is available for the following samples: ", "cgMLST typing profiles are unavailable", false],
    ["mlst", "No MLST typing profile is available for the following samples: ", "MLST typing profiles are unavailable", false],
    ["ska", "No SKA index is available for the following samples: ", "SKA indexes are unavailable", false],
    ["ska", "FileNotFoundError: No SKA index file is available for the following samples: ", "SKA index files are unavailable", true],
    ["minhash", "ValueError: Could not load exactly one MinHash signature per selected sample: ", "MinHash signatures are unavailable or invalid", true],
  ]) {
    for (const count of [1, 4, 5]) {
      const sampleIds = Array.from({ length: 8 }, (_, i) => `sample-id-${i}`);
      const samples = sampleIds.map((sample_id, i) => ({ sample_id, external_sample_id: `LAB-${i}` }));
      const labels = samples.slice(0, count).map(sample => typingMethod === "minhash" ? sample.sample_id : sample.external_sample_id);
      const message = prefix + labels.join(", ");
      const h = setup({
        typingMethod, sampleIds, samples,
        ...(worker ? { error: message } : { submissionError: new ApiError("Request failed", { detail: message }) }),
      });
      await h.actions.clusterSamples(h.element, h.sampleIds, h.api);

      const expected = count > 4 ? "5 samples" : samples.slice(0, count).map(sample => sample.external_sample_id).join(", ");
      assert.deepEqual(h.toasts.at(-1), [`Cannot cluster: ${reason} for ${expected}.`, "error"]);
      assert.equal(h.lookups.length, typingMethod === "minhash" && count <= 4 ? 1 : 0);
      if (h.lookups.length) {
        assert.deepEqual(Array.from(h.lookups[0].sid), sampleIds.slice(0, count));
      }
      assert.equal(h.logs[0][1].error.message, worker ? message : "Request failed");
      assert.equal(h.hidden(), 1);
      assert.equal(h.toasts.filter(([, severity]) => severity === "error").length, 1);
    }
  }
});

test("internal IDs use Lab IDs, or a count if lookup fails or a Lab ID is missing", async () => {
  const sampleIds = ["01991d8e-5d6d-7000-8000-000000000001", "sample-id-2"];
  for (const options of [
    { samples: [{ sample_id: sampleIds[0], external_sample_id: "LAB-123" }], expected: "LAB-123" },
    { samples: [{ sample_id: sampleIds[0], external_sample_id: " " }], expected: "1 sample" },
    { samples: [], expected: "1 sample" },
    { lookupError: new Error("Lookup failed"), expected: "1 sample" },
  ]) {
    const h = setup({
      sampleIds, ...options,
      submissionError: new ApiError("Request failed", {
        detail: `No SKA index is available for the following samples: ${sampleIds[0]}`,
      }),
    });
    await h.actions.clusterSamples(h.element, h.sampleIds, h.api);
    assert.equal(h.toasts.at(-1)[0], `Cannot cluster: SKA indexes are unavailable for ${options.expected}.`);
    assert.equal(h.hidden(), 1);
  }
});

test("uncallable allele submissions provide structured basket feedback without removing IDs", async () => {
  for (const typingMethod of ["mlst", "cgmlst"]) {
    const affected = [{ sample_id: "sample-id-2", label: "LAB-2" }];
    const h = setup({ typingMethod, submissionError: new ApiError("Request failed", {
      type: "urn:bonsai:problem:no-usable-allele-calls",
      typing_method: typingMethod,
      detail: "No usable calls for LAB-2",
      samples: affected,
    }) });
    const reports = [];
    await h.actions.clusterSamples(h.element, h.sampleIds, h.api, (...args) => reports.push(args));
    assert.deepEqual(reports, [[typingMethod, affected]]);
    assert.match(h.toasts.at(-1)[0], /1 sample has no usable allele calls/);
    assert.match(h.toasts.at(-1)[0], /Remove the affected samples from the basket/);
    assert.equal(h.sampleIds.length, 4);
    assert.equal(h.lookups.length, 0);
    assert.equal(h.hidden(), 1);
  }
});

test("ordinary validation errors and unrelated sample IDs never offer basket removal", async () => {
  for (const problem of [
    { type: "urn:bonsai:problem:invalid-data", samples: [{ sample_id: "sample-id-2", label: "LAB-2" }] },
    { type: "urn:bonsai:problem:no-usable-allele-calls", samples: [{ sample_id: "outside-request", label: "OTHER" }] },
    { type: "urn:bonsai:problem:no-usable-allele-calls", samples: [null] },
    { type: "urn:bonsai:problem:no-usable-allele-calls", typing_method: "cgmlst", samples: [{ sample_id: "sample-id-2", label: "LAB-2" }] },
  ]) {
    const h = setup({ typingMethod: "mlst", submissionError: new ApiError("Request failed", {
      typing_method: "mlst", detail: "Invalid allele data", ...problem,
    }) });
    const reports = [];
    await h.actions.clusterSamples(h.element, h.sampleIds, h.api, (...args) => reports.push(args));
    assert.deepEqual(reports, []);
    assert.equal(h.toasts.at(-1)[0], "Invalid allele data");
  }
});

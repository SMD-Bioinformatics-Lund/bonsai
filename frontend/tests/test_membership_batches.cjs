// Run from frontend/: node --test tests/test_membership_batches.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

function load(relativePath, dependencies = {}) {
  const exports = {};
  const source = fs.readFileSync(path.join(__dirname, relativePath), "utf8");
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, { exports, URLSearchParams, require: () => dependencies });
  return exports;
}

const queryParams = load("../web/js/core/api/utils/queryParams.ts");
const { ApiService } = load("../web/js/core/api/index.ts", queryParams);

for (const count of [0, 1, 100, 101, 205]) {
  test(`membership lookup retrieves all ${count} samples within the API's 100-ID limit`, async () => {
    const sampleIds = Array.from({ length: count }, (_, i) => `sample-${i}`);
    const signal = new AbortController().signal;
    const requested = [];
    const api = new ApiService({
      async request(endpoint, options) {
        const ids = new URL(endpoint, "http://api").searchParams.getAll("s");
        assert.ok(ids.length > 0 && ids.length <= 100);
        assert.equal(options.signal, signal);
        assert.equal(options.method, "GET");
        requested.push(...ids);
        return ids.map(sample_id => ({ sample_id, group_id: "group-1" }));
      },
    });

    const memberships = await api.getMembershipsBySamples(sampleIds, signal);

    assert.deepEqual(requested, sampleIds);
    assert.deepEqual(Array.from(memberships, edge => edge.sample_id), sampleIds);
  });
}

test("a failed membership batch rejects the lookup instead of returning partial memberships", async () => {
  let requests = 0;
  const failure = new Error("Membership lookup failed");
  const api = new ApiService({
    async request() {
      if (++requests === 2) throw failure;
      return [{ sample_id: "sample-0", group_id: "group-1" }];
    },
  });

  await assert.rejects(api.getMembershipsBySamples(Array.from({ length: 205 }, (_, i) => `sample-${i}`)), failure);
  assert.equal(requests, 2);
});

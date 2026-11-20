const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");

function setup(responses, refreshToken = "") {
  const requests = [];
  const storage = new Map();
  function load(name, require = () => ({})) {
    const exports = {};
    const source = fs.readFileSync(path.join(__dirname, `../web/js/core/api/http/${name}.ts`), "utf8");
    vm.runInNewContext(ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText, {
      exports, require, Error,
      localStorage: {
        getItem: key => storage.get(key) ?? null,
        setItem: (key, value) => storage.set(key, value),
        removeItem: key => storage.delete(key),
      },
      fetch: async (url, options) => {
        requests.push({ url, options });
        assert.ok(responses.length > 0, "Unexpected additional request");
        return responses.shift();
      },
    });
    return exports;
  }
  const { ApiError } = load("ApiError");
  const { AuthService } = load("AuthService");
  const { HttpClient } = load("HttpClient", () => ({ ApiError }));
  const auth = new AuthService("/staging/bonsai/api/v1");
  auth.setTokens("expired-access-token", refreshToken);
  return { http: new HttpClient("/staging/bonsai/api/v1", auth), requests, ApiError };
}

function response(status, data) {
  return { status, ok: status >= 200 && status < 300,
    text: async () => JSON.stringify(data), json: async () => data };
}

test("a basket POST rejected without a refresh token preserves HTTP 401 without retrying", async () => {
  const h = setup([response(401, { detail: "Token expired" })]);
  await assert.rejects(h.http.request("/samples/summary", {
    method: "POST", body: JSON.stringify({ sid: ["a", "b"] }),
  }), error => {
    assert.ok(error instanceof h.ApiError);
    assert.equal(error.status, 401);
    assert.equal(error.data.detail, "Token expired");
    return true;
  });
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].url, "/staging/bonsai/api/v1/samples/summary");
});

test("a temporary server error preserves its status without attempting authentication refresh", async () => {
  const h = setup([response(503, { detail: "Unavailable" })]);
  await assert.rejects(h.http.request("/samples/summary"), error => error.status === 503);
  assert.equal(h.requests.length, 1);
});

test("a configured refresh token still refreshes and retries once with the new access token", async () => {
  const h = setup([
    response(401, { detail: "Token expired" }),
    response(200, { accessToken: "fresh-access-token", refreshToken: "fresh-refresh-token" }),
    response(200, { data: [] }),
  ], "refresh-token");
  const options = { method: "POST", body: JSON.stringify({ sid: ["a", "b"] }) };
  const result = await h.http.request("/samples/summary", options);
  assert.equal(result.data.length, 0);
  assert.equal(h.requests.length, 3);
  assert.equal(h.requests[1].url, "/staging/bonsai/api/v1/auth/refresh");
  assert.equal(h.requests[2].options.headers.Authorization, "Bearer fresh-access-token");
  assert.equal(h.requests[2].options.body, options.body);
});

test("a repeated 401 after token refresh stops retrying", async () => {
  const h = setup([
    response(401, {}),
    response(200, { accessToken: "fresh-access-token", refreshToken: "fresh-refresh-token" }),
    response(401, { detail: "Still unauthorized" }),
  ], "refresh-token");
  await assert.rejects(h.http.request("/samples/summary"), error => error.status === 401);
  assert.equal(h.requests.length, 3);
});

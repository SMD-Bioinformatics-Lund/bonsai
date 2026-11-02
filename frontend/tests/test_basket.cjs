// Run from frontend/: node --test tests/test_basket.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");
const { JSDOM } = require("jsdom");

const apiUrl = "https://api.example.test/bonsai";
const key = (user = "alice", api = apiUrl) => `basket_content:${JSON.stringify([api, user])}`;
const response = ids => ({ data: ids.map(id => ({ sample_id: id, sample_name: `Name ${id}`, assay: "WGS" })) });
const flush = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};

function harness(t, { stored = {}, fetch = async query => response(query.sid) } = {}) {
  const dom = new JSDOM(`<div id="basket-content"></div><div id="basket-counter-container"></div>
    <div id="basket-offcanvas"></div><button id="clear-basket-btn"></button>
    <div id="basket-cluster-samples"><a data-bi-typing-method="minhash"></a></div>`, {
    url: "https://frontend.example.test/bonsai/groups", runScripts: "outside-only",
  });
  t.after(() => dom.window.close());
  const context = dom.getInternalVMContext();
  context.baseUrl = "/bonsai";
  const logs = [], clusters = [], toasts = [];
  context.console = { error: (...args) => logs.push(args), warn: (...args) => logs.push(args) };
  for (const [name, value] of Object.entries(stored)) dom.window.localStorage.setItem(name, value);
  const cache = new Map();
  function load(file) {
    if (cache.has(file)) return cache.get(file);
    const module = { exports: {} };
    cache.set(file, module.exports);
    let source = fs.readFileSync(path.join(__dirname, "../web/js", file), "utf8");
    // Expose the private initializer only in the test, leaving its public API unchanged.
    if (file === "views/groups-view/init.ts") source = source.replace("function initBasket(", "export function initBasket(");
    const code = ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText;
    const requireModule = name => {
      if (name.endsWith("/core/actions/cluster-actions")) return { clusterSamples: (...args) => clusters.push(args) };
      if (name.endsWith("/utils/notification")) return { throwSmallToast: (...args) => toasts.push(args) };
      const target = path.posix.normalize(path.posix.join(path.posix.dirname(file), `${name}.ts`));
      if (["core/state/basket-state.ts", "components/sample-basket.ts", "components/samples-basket-counter.ts", "utils/event-bus.ts"].includes(target)) return load(target);
      return {};
    };
    vm.runInContext(`(function(require, module, exports) {${code}\n})`, context)(requireModule, module, module.exports);
    return module.exports;
  }
  const { BasketState } = load("core/state/basket-state.ts");
  const { BasketComponent } = load("components/sample-basket.ts");
  const { SampleBasketCounter } = load("components/samples-basket-counter.ts");
  function mount(state) {
    const counter = new SampleBasketCounter();
    counter.basketState = state;
    const panel = new BasketComponent(state, fetch);
    dom.window.document.getElementById("basket-counter-container").appendChild(counter);
    dom.window.document.getElementById("basket-content").appendChild(panel);
    return { counter, panel };
  }
  return { window: dom.window, document: dom.window.document, BasketState, mount, load,
    fetch, logs, clusters, toasts,
    count: () => Number(dom.window.document.getElementById("sample-basket-counter").textContent),
    cards: () => [...dom.window.document.querySelectorAll(".sample_in_basket")],
  };
}

test("saved selections are isolated by account and API, and persist for the same account", t => {
  const h = harness(t, { stored: { basket_content: '["legacy"]' } });
  const first = new h.BasketState(apiUrl, "alice");
  assert.equal(first.getSampleIds().length, 0);
  first.addSamples(["a", "b", "a"]);
  assert.deepEqual([...new h.BasketState(apiUrl, "alice").getSampleIds()], ["a", "b"]);
  assert.equal(new h.BasketState(apiUrl, "bob").getSampleIds().length, 0);
  assert.equal(new h.BasketState("https://other-api.test", "alice").getSampleIds().length, 0);
});

for (const saved of ['{"wrong":"shape"}', 'not json', '["a",null,4,"","a"]']) {
  test(`invalid persisted basket does not create a misleading count: ${saved}`, async t => {
    const h = harness(t, { stored: { [key()]: saved } });
    const state = new h.BasketState(apiUrl, "alice");
    h.mount(state);
    await flush();
    const expected = saved.startsWith('["a"') ? 1 : 0;
    assert.equal(h.count(), expected);
    assert.equal(h.cards().length, expected);
  });
}

test("missing and duplicate records reconcile cards, badge and saved IDs", async t => {
  const h = harness(t, { stored: { [key()]: '["a","gone","b"]' },
    fetch: async query => {
      assert.deepEqual([...query.fields], ["sample_id", "sample_name", "assay"]);
      return response(["b", "a", "a"]);
    } });
  const state = new h.BasketState(apiUrl, "alice");
  h.mount(state);
  await flush();
  assert.deepEqual([...state.getSampleIds()], ["a", "b"]);
  assert.equal(h.count(), 2);
  assert.equal(h.cards().length, 2);
  assert.deepEqual(h.cards().map(card => card.querySelector("h6").textContent), ["Name a", "Name b"]);
  assert.deepEqual(JSON.parse(h.window.localStorage.getItem(key())), ["a", "b"]);
});

test("a basket containing only unavailable samples becomes visibly empty with count zero", async t => {
  const h = harness(t, { stored: { [key()]: '["gone"]' }, fetch: async () => response([]) });
  const state = new h.BasketState(apiUrl, "alice");
  const { panel } = h.mount(state);
  await flush();
  assert.equal(h.count(), 0);
  assert.equal(h.cards().length, 0);
  assert.match(panel.textContent, /Your basket is empty/);
  assert.equal(h.document.getElementById("sample-basket-badge").hidden, true);
});

test("overlapping loads neither duplicate cards nor let an older failure replace the newest result", async t => {
  const old = deferred(), latest = deferred();
  const requests = [old, latest];
  const h = harness(t, { fetch: () => requests.shift().promise });
  const state = new h.BasketState(apiUrl, "alice");
  const { panel } = h.mount(state);
  state.addSamples(["a", "b"]);
  const current = panel.render();
  latest.resolve(response(["a", "b"]));
  await current;
  old.reject(new Error("obsolete request failed"));
  await flush();
  assert.equal(h.cards().length, 2);
  assert.equal(h.count(), 2);
  assert.equal(panel.querySelector('[role="alert"]'), null);
  // A second pair of successful loads exercises the original duplicate-card bug.
  const first = deferred(), second = deferred();
  requests.push(first, second);
  const p1 = panel.render(), p2 = panel.render();
  second.resolve(response(["a", "b"]));
  await p2;
  first.resolve(response(["a", "b"]));
  await p1;
  assert.equal(h.cards().length, 2);
});

test("clearing the basket during a pending load cannot resurrect old cards", async t => {
  const pending = deferred();
  const h = harness(t, { fetch: () => pending.promise });
  const state = new h.BasketState(apiUrl, "alice");
  const { panel } = h.mount(state);
  state.addSamples(["a"]);
  state.clear();
  pending.resolve(response(["a"]));
  await flush();
  assert.equal(h.cards().length, 0);
  assert.equal(h.count(), 0);
  assert.match(panel.textContent, /Your basket is empty/);
});

test("failed loads preserve the selection, show an error and allow retry", async t => {
  let fail = true;
  const h = harness(t, { stored: { [key()]: '["a","b"]' }, fetch: async query => {
    if (fail) throw new Error("API unavailable");
    return response(query.sid);
  } });
  const state = new h.BasketState(apiUrl, "alice");
  const { panel } = h.mount(state);
  await flush();
  assert.equal(h.count(), 2);
  assert.deepEqual([...state.getSampleIds()], ["a", "b"]);
  assert.match(panel.querySelector('[role="alert"]').textContent, /saved selection has been kept/);
  fail = false;
  panel.querySelector("button").click();
  await flush();
  assert.equal(h.cards().length, 2);
  h.cards()[0].querySelector("button").click();
  await flush();
  assert.equal(h.cards().length, 1);
  assert.equal(h.count(), 1);
});

test("unexpected response data does not erase the saved basket", async t => {
  const h = harness(t, { stored: { [key()]: '["a"]' }, fetch: async () => response(["unrequested"]) });
  const state = new h.BasketState(apiUrl, "alice");
  const { panel } = h.mount(state);
  await flush();
  assert.deepEqual([...state.getSampleIds()], ["a"]);
  assert.ok(panel.querySelector('[role="alert"]'));
});

test("basket initialization handles deletion events and clusters only freshly verified samples", async t => {
  let available = ["a", "b"];
  let fail = false;
  const h = harness(t, { fetch: async () => {
    if (fail) throw new Error("API unavailable");
    return response(available);
  } });
  const { initBasket } = h.load("views/groups-view/init.ts");
  const api = { getSamplesDetails: h.fetch };
  const state = initBasket(api, `${apiUrl}/`, "alice");
  state.addSamples(["a", "b", "gone"]);
  await flush();
  assert.equal(h.count(), 2);
  const link = h.document.querySelector("#basket-cluster-samples a");
  const click = () => link.onclick(new h.window.MouseEvent("click", { cancelable: true }));
  await click();
  assert.deepEqual([...h.clusters[0][1]], ["a", "b"]);
  available = ["b"];
  h.load("utils/event-bus.ts").emitEvent("samples:deleted", { sampleIds: ["a"] });
  await flush();
  assert.equal(h.count(), 1);
  assert.equal(h.cards().length, 1);
  await click();
  assert.equal(h.clusters.length, 1);
  fail = true;
  await click();
  assert.equal(h.clusters.length, 1);
});

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

const source = fs.readFileSync(path.join(__dirname, "../web/js/views/sample-view/bracken-table.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;

function table(count) {
  const body = { rows: Array.from({ length: count }, () => ({ hidden: false })) };
  const attributes = new Map();
  let onClick;
  const button = count > 5 ? {
    hidden: true, textContent: "Show less",
    setAttribute: (key, value) => attributes.set(key, value),
    getAttribute: key => attributes.get(key),
    addEventListener: (name, fn) => { if (name === "click") onClick = fn; },
    click: () => onClick(),
  } : null;
  return {
    body, button,
    querySelector: selector => selector === "tbody" ? body : button,
  };
}

function initialize(tables) {
  const exports = {};
  vm.runInNewContext(compiled, { exports, document: { querySelectorAll: () => tables } });
  exports.initBrackenTables();
}

test("long Bracken tables show five rows and toggle all remaining rows", () => {
  const t = table(8);
  initialize([t]);
  assert.equal(t.body.rows.filter(row => !row.hidden).length, 5);
  assert.equal(t.button.hidden, false);
  assert.equal(t.button.textContent, "Show more (3)");
  assert.equal(t.button.getAttribute("aria-expanded"), "false");
  assert.equal(t.button.getAttribute("aria-controls"), t.body.id);

  t.button.click();
  assert.ok(t.body.rows.every(row => !row.hidden));
  assert.equal(t.button.textContent, "Show less");
  assert.equal(t.button.getAttribute("aria-expanded"), "true");

  t.button.click();
  assert.equal(t.body.rows.filter(row => !row.hidden).length, 5);
});

test("short tables stay visible and multiple cards expand independently", () => {
  const short = table(5), a = table(6), b = table(9);
  initialize([short, a, b]);
  assert.ok(short.body.rows.every(row => !row.hidden));
  assert.notEqual(a.body.id, b.body.id);
  a.button.click();
  assert.equal(a.body.rows.filter(row => !row.hidden).length, 6);
  assert.equal(b.body.rows.filter(row => !row.hidden).length, 5);
});

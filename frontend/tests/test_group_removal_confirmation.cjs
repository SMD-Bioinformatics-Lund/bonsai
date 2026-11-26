const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

function groupPicker(confirm) {
  const requests = [], prompts = [], events = [];
  let selected = [];
  const selector = {
    getSelected: () => selected,
    setSelected: values => { selected = values; },
    clearSelected: () => { selected = []; },
  };
  const buttons = Object.fromEntries(["apply", "clear"].map(id => [id, {
    addEventListener(_, handler) { this.click = handler; },
    removeEventListener() {},
  }]));
  class Element {
    attachShadow() {
      this.shadowRoot = {
        appendChild() {},
        getElementById: id => id === "groups" ? selector : buttons[id],
      };
    }
    dispatchEvent(event) { events.push(event); }
  }
  const exports = {};
  const source = fs.readFileSync(path.join(__dirname, "../web/js/components/group-selector.ts"), "utf8");
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, {
    exports, AbortController, HTMLElement: Element,
    CustomEvent: class { constructor(type, init) { Object.assign(this, { type }, init); } },
    document: { createElement: () => ({ content: { cloneNode() {} } }) },
    customElements: { define() {}, whenDefined: () => new Promise(() => {}) },
    window: { confirm: message => { prompts.push(message); return confirm; } },
    require: () => ({ emitEvent() {} }),
    console,
  });
  const picker = new exports.GroupSelector();
  picker.getSelectedSamples = () => ["sample-1", "sample-2"];
  picker.getGroupMembership = async () => [
    { sample_id: "sample-1", group_id: "old-group" },
    { sample_id: "sample-2", group_id: "old-group" },
  ];
  picker.addToGroup = async (group, samples) => { requests.push(["add", group, ...samples]); };
  picker.removeFromGroup = async (group, samples) => { requests.push(["remove", group, ...samples]); };
  picker.connectedCallback();
  return { picker, selector, buttons, requests, prompts, events };
}

test("cancelling group deselection cancels all changes before any API request", async () => {
  const h = groupPicker(false);
  await h.picker.onSelectedSamplesChange();
  h.selector.setSelected(["new-group"]);
  await h.buttons.apply.click();

  assert.equal(h.prompts.length, 1);
  assert.match(h.prompts[0], /2 selected sample.*1 deselected group/);
  assert.deepEqual(h.requests, []);
  assert.deepEqual(h.events, []);
});

test("confirmed group deselection applies the intended changes once", async () => {
  const h = groupPicker(true);
  await h.picker.onSelectedSamplesChange();
  h.selector.setSelected([]);
  await h.buttons.apply.click();

  assert.equal(h.prompts.length, 1);
  assert.deepEqual(h.requests, [
    ["remove", "old-group", "sample-1"], ["remove", "old-group", "sample-2"],
  ]);
  assert.equal(h.events[0].type, "apply:success");
});

test("adding a group without removals needs no removal confirmation", async () => {
  const h = groupPicker(false);
  await h.picker.onSelectedSamplesChange();
  h.selector.setSelected(["old-group", "new-group"]);
  await h.buttons.apply.click();

  assert.deepEqual(h.prompts, []);
  assert.deepEqual(h.requests, [
    ["add", "new-group", "sample-1"], ["add", "new-group", "sample-2"],
  ]);
});

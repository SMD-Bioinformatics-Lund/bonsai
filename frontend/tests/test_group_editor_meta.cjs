const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

const exportsForTest = {};
const source = fs.readFileSync(path.join(__dirname, "../web/js/views/group-editor/render/meta.ts"), "utf8");
vm.runInNewContext(ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, { exports: exportsForTest });

test("group fields retain literal quotes and markup without creating HTML handlers or elements", () => {
  const fields = Object.fromEntries(["#group-name", "#group-key", "textarea"].map(id => [id, {
    value: "", addEventListener() {},
  }]));
  const container = { innerHTML: "", querySelector: selector => fields[selector] };
  const model = {
    mode: "edit", groupKey: "test-group",
    displayName: 'x" autofocus onfocus="alert(1)',
    description: '</textarea><img src=x onerror="alert(1)"> & "notes"',
  };

  exportsForTest.renderMeta(container, model);

  assert.doesNotMatch(container.innerHTML, /onfocus|onerror|<img/);
  assert.equal(fields["#group-name"].value, model.displayName);
  assert.equal(fields["#group-key"].value, model.groupKey);
  assert.equal(fields.textarea.value, model.description);
});

test("an absent optional description displays as an empty field", () => {
  const field = { value: "", addEventListener() {} };
  const container = { innerHTML: "", querySelector: () => field };

  exportsForTest.renderMeta(container, {
    mode: "create", groupKey: "", displayName: "New group", description: null,
  });

  assert.equal(field.value, "");
  assert.doesNotMatch(container.innerHTML, /null/);
});

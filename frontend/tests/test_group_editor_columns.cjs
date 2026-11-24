const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

function loadEditorModule(filename, imports = {}) {
  const exports = {};
  const source = fs.readFileSync(path.join(__dirname, "../web/js/views/group-editor", filename), "utf8");
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, {
    exports,
    require: name => imports[name] ?? {},
    HTMLElement: class {
      selector = { items: [] };
      querySelector(name) { return name === "column-selector" ? this.selector : null; }
      dispatchEvent() {}
    },
    customElements: { define() {} },
    CustomEvent: class {},
  });
  return exports;
}

const model = loadEditorModule("model.ts");
const { GroupEditor } = loadEditorModule("index.ts", {
  "./model": model,
  "./init": { initGroupEditor() {} },
  "./render/actions": { renderActions() {} },
  "./render/columns": loadEditorModule("render/columns.ts"),
  "./render/meta": { renderMeta() {} },
  "./render/samples": { renderSamples() {} },
});

async function openEditor(tableColumns) {
  const editor = new GroupEditor();
  const groupUpdates = [];
  const columnUpdates = [];
  const groupId = "test-group";
  editor.mode = "edit";
  editor.model = model.GroupEditModel.initial("edit");
  editor.availableColumns = [
    { id: "sample_name", label: "Name", default_visible: true },
    { id: "quast_n50", label: "N50", default_visible: false },
  ];
  editor.api = {
    async getGroup() { return { group_id: groupId, display_name: "Example group", table_columns: tableColumns }; },
    async updateGroup(id, data) { groupUpdates.push([id, data.display_name]); },
    async updateAllowedColumns(id, ids) { columnUpdates.push([id, [...ids]]); },
  };
  await editor.load(groupId);
  return { editor, groupUpdates, columnUpdates };
}

test("renaming an unrestricted group preserves its column availability", async () => {
  const { editor, groupUpdates, columnUpdates } = await openEditor([]);
  assert.equal(editor.selector.items.find(item => item.id === "quast_n50").enabled, true);

  editor.model.displayName = "Renamed group";
  await editor.save();

  assert.deepEqual(groupUpdates, [["test-group", "Renamed group"]]);
  assert.deepEqual(columnUpdates, []);
});

test("save updates allowed columns only when the selection differs", async () => {
  const { editor, columnUpdates } = await openEditor(["sample_name"]);
  const n50 = editor.selector.items.find(item => item.id === "quast_n50");
  assert.equal(n50.enabled, false);

  n50.enabled = true;
  n50.enabled = false;
  await editor.save();
  assert.deepEqual(columnUpdates, []);

  n50.enabled = true;
  await editor.save();
  await editor.save();
  assert.deepEqual(columnUpdates, [["test-group", ["sample_name", "quast_n50"]]]);
});

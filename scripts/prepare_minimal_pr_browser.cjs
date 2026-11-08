// Build the repository's installed DataTables plugins for isolated browser checks.
// No package downloads or live services are used.
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const webpack = require('webpack');
const root = process.argv[2];
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'branches.json')));
const output = path.join(root, 'browser-assets');
fs.mkdirSync(output, {recursive: true});
const entry = path.join(output, 'foundation-entry.js');
fs.writeFileSync(entry, `
import DataTable from 'datatables.net-bs5';
import JSZip from 'jszip';
import 'datatables.net-buttons-bs5';
import 'datatables.net-buttons/js/buttons.html5.mjs';
import 'datatables.net-buttons/js/buttons.colVis.mjs';
import 'datatables.net-datetime';
import 'datatables.net-columncontrol-bs5';
import 'datatables.net-searchbuilder-bs5';
import 'datatables.net-searchpanes-bs5';
import 'datatables.net-select-bs5';
window.auditDataTable = DataTable; window.auditJSZip = JSZip;
`);
for (const id of ['QC-FILTER-EMPTY','SELECTED-FILTER-STALE','VARIANT-SELECT-ALL-INVALID']) {
  const candidate = manifest.candidates.find(row => row.id === id);
  const source = path.join(root, 'snapshots', id, candidate.head.slice(0,10));
  const files = {
    controller: 'frontend/web/js/utils/table-controller.ts',
    group: 'frontend/web/js/views/groups-view/init.ts',
    variants: 'frontend/web/js/views/variants-table/variants-view.ts',
  };
  for (const [label, filename] of Object.entries(files)) {
    let input = fs.readFileSync(path.join(source, filename), 'utf8');
    // Export the existing initializer only; its implementation is untouched.
    if (label === 'variants') input += '\nexport { initVariantSelection };\n';
    const compiled = ts.transpileModule(input, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018,esModuleInterop:true}}).outputText;
    fs.writeFileSync(path.join(output, `${id}-${label}.js`), compiled);
  }
}
webpack({mode:'development',entry,output:{path:output,filename:'foundation.js'},
  resolve:{modules:['/app/frontend/node_modules']},devtool:false}, (error, stats) => {
  if (error || stats.hasErrors()) { console.error(error || stats.toString({all:false,errors:true})); process.exitCode = 1; }
  else console.log('DataTables browser fixture compiled from installed dependencies.');
});

const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs'), vm = require('node:vm'), ts = require('typescript');

function load(file, globals={}) {
  const exports={};
  const code=ts.transpileModule(fs.readFileSync(__dirname+'/../web/js/views/group-editor/'+file,'utf8'),
    {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  vm.runInNewContext(code,{exports,require:name=>name==='./model'?load('model.ts'):new Proxy({}, {get:()=>()=>{}}),
    HTMLElement:class extends EventTarget {},CustomEvent,customElements:{define(){}},
    window:{location:{pathname:'/groups/id/edit'}},console,...globals});
  return exports;
}

function harness(mode='edit') {
  const {GroupEditModel}=load('model.ts'),{GroupEditor}=load('index.ts');
  const editor=new GroupEditor(), calls=[], events=[];
  const initial={group_id:'id',group_key:'key',display_name:'Original',description:'Description',table_columns:['one'],sample_count:0};
  const selector={items:[{id:'one',enabled:true},{id:'two',enabled:false}]};
  const buttons=[{disabled:false},{disabled:false}];
  editor.model=GroupEditModel.initial(mode);editor.mode=mode;
  editor.querySelector=()=>selector;editor.querySelectorAll=()=>buttons;
  editor.setAttribute=()=>{};
  editor.render=()=>{};
  editor._api={getGroup:async()=>({...initial}),createGroup:async data=>{calls.push(['create',data]);return initial;},
    updateGroup:async(id,data)=>{calls.push(['core',data]);return {...initial,...data};},
    updateAllowedColumns:async(id,ids)=>{calls.push(['columns',Array.from(ids)]);return initial;}};
  editor.addEventListener('group-editor:error',e=>events.push(e.detail.message));
  return {editor,calls,events,selector,buttons,async ready(){if(mode==='edit')await editor.load('id');}};
}

test('pending save ignores repeated Save and Reset',async()=>{
  const h=harness();await h.ready();h.editor.model.displayName='Changed';const releases=[];
  h.editor._api.updateGroup=async()=>{h.calls.push(['core']);await new Promise(r=>releases.push(r));return {};};
  const first=h.editor.save(),second=h.editor.save();h.editor.reset();
  try{assert.equal(h.calls.length,1);assert.ok(h.buttons.every(b=>b.disabled));}
  finally{releases.forEach(r=>r());await Promise.all([first,second]);}
  assert.ok(h.buttons.every(b=>!b.disabled));
});

test('stale editor sends only its independently changed field',async()=>{
  const h=harness();await h.ready();h.editor.model.description='Other tab description';await h.editor.save();
  assert.deepEqual(JSON.parse(JSON.stringify(h.calls)),[['core',{description:'Other tab description'}]]);
});

test('columns are captured before awaiting the core write',async()=>{
  const h=harness();await h.ready();h.editor.model.displayName='Changed';h.selector.items[1].enabled=true;let release;
  h.editor._api.updateGroup=async()=>new Promise(r=>release=r);
  const pending=h.editor.save();h.selector.items[0].enabled=false;release({});await pending;
  assert.deepEqual(h.calls,[['columns',['one','two']]]);
});

test('partial failure is explicit and retry does not resend saved core data',async()=>{
  const h=harness();await h.ready();h.editor.model.displayName='Changed';h.selector.items[1].enabled=true;
  let fail=true;h.editor._api.updateAllowedColumns=async()=>{if(fail)throw new Error('Offline');return {};};
  await h.editor.save();assert.match(h.events[0],/details were saved/i);
  fail=false;await h.editor.save();assert.equal(h.calls.filter(c=>c[0]==='core').length,1);
});

test('a known created group is reused after a later failure',async()=>{
  const h=harness('create');h.editor.model.groupKey='key';h.editor.model.displayName='New';let fail=true;
  h.editor._api.updateAllowedColumns=async()=>{if(fail)throw new Error('Offline');return {};};
  await h.editor.save();fail=false;await h.editor.save();
  assert.equal(h.calls.filter(c=>c[0]==='create').length,1);assert.equal(h.editor.model.mode,'edit');
});

test('an uncertain core response does not imply nothing was saved',async()=>{
  const h=harness();await h.ready();h.editor.model.displayName='Changed';
  h.editor._api.updateGroup=async()=>{throw new TypeError('Response lost');};await h.editor.save();
  assert.match(h.events[0],/may have been saved|could not confirm/i);
});

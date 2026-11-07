const assert=require('node:assert/strict');
const {test}=require('node:test');
const fs=require('node:fs'),vm=require('node:vm'),ts=require('typescript');

function setup(initial={}) {
  const saved=new Map(Object.entries(initial)),window=new EventTarget(),exports={};
  const localStorage={getItem:k=>saved.get(k)??null,setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)};
  const code=ts.transpileModule(fs.readFileSync(__dirname+'/../web/js/core/state/basket-state.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  vm.runInNewContext(code,{exports,window,localStorage,document:{body:{dataset:{bonsaiUser:'alice'}}},console});
  return {State:exports.BasketState,saved,change(key,value){saved.set(key,JSON.stringify(value));window.dispatchEvent(Object.assign(new Event('storage'),{key}));}};
}

test('accounts have independent selections',()=>{
  const h=setup(),alice=new h.State('alice');alice.addSamples(['record-a']);
  assert.deepEqual(Array.from(new h.State('bob').getSampleIds()),[]);
});

test('clearing another account does not clear a saved selection',()=>{
  const h=setup();new h.State('alice').addSamples(['record-a']);new h.State('bob').clear();
  assert.deepEqual(Array.from(new h.State('alice').getSampleIds()),['record-a']);
});

test('a same-account storage update refreshes existing observers',()=>{
  const h=setup(),alice=new h.State('alice');alice.addSamples(['record-a']);let observed;
  alice.onSelection(ids=>observed=Array.from(ids));h.change('basket_content:alice',[]);
  assert.deepEqual(Array.from(alice.getSampleIds()),[]);assert.deepEqual(observed,[]);
});

test('an unattributed legacy basket is never assigned to the next account',()=>{
  const h=setup({basket_content:'["legacy-record"]'});
  assert.deepEqual(Array.from(new h.State('alice').getSampleIds()),[]);
});

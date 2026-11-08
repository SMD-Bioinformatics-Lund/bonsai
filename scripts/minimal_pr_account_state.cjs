const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');

function page(name,storage=new Map()) {
  const html=fs.readFileSync(__dirname+'/../bonsai_app/templates/bootstrap_base.html','utf8');
  const source='// Keep rendered account state'+html.split('<script>\n        // Keep rendered account state')[1].split('</script>')[0];
  const window=new EventTarget();let reloads=0;
  const localStorage={getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value)};
  vm.runInNewContext(source.replace(/\{\{[^]*?\}\}/,JSON.stringify(name)),{window,localStorage,location:{reload(){reloads++;}}});
  return {window,storage,reloads:()=>reloads};
}

test('account state change refreshes a previously rendered tab',()=>{
  const first=page('alice');page('bob',first.storage);
  first.window.dispatchEvent(Object.assign(new Event('storage'),{key:'bonsai_active_account'}));
  assert.equal(first.reloads(),1);
});

test('account state mismatch on history restoration refreshes the view',()=>{
  const first=page('alice');page('',first.storage);
  first.window.dispatchEvent(new Event('pageshow'));
  assert.equal(first.reloads(),1);
});

test('account state in an independent browser remains independent',()=>{
  const first=page('alice');page('bob');
  first.window.dispatchEvent(new Event('pageshow'));
  assert.equal(first.reloads(),0);
});

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Core = require('../web/assets/core.js');

test('battery split remains disjoint and deterministic',()=>{
  const a=Core.splitDemo(42,.25,'battery');
  assert.deepEqual(a,Core.splitDemo(42,.25,'battery'));
  assert.equal(a.overlap,false);
  assert.equal(a.counts.train+a.counts.val+a.counts.test,8);
});
test('cycle split reports identity collision when it occurs',()=>{
  const d=Core.splitDemo(42,.25,'cycle');
  assert.equal(d.overlap,true);
  assert.equal(d.counts.train+d.counts.val+d.counts.test,32);
});
test('signal pipeline preserves next-step sample count',()=>{
  const data=Core.prepareSignal({step:3,window:16,norm:'minmax'});
  assert.equal(data.count,80);
  assert.equal(data.windows,64);
  assert.equal(data.shape,'[16, 3]');
  assert.equal(data.processed[1].index,3);
});
test('exported experiment protocol is executable and restricted',()=>{
  const c=Core.experimentConfig({task:'soc',model:'rdb_attn_bilstm',window:64,seed:42,splitUnit:'cycle',testFraction:.2});
  assert.deepEqual(Object.keys(c.data).includes('path'),true);
  assert.equal(c.features.window,64);
  assert.equal(c.split.seed,42);
  assert.equal(c.data.synthetic,false);
  assert.throws(()=>Core.experimentConfig({task:'rul',splitUnit:'cycle'}),/battery-level/);
  assert.throws(()=>Core.experimentConfig({window:0}),/Window/);
});
test('bundled result is a real Python-generated schema',()=>{
  const report=JSON.parse(fs.readFileSync(path.join(__dirname,'../web/data/demo_run.json'),'utf8'));
  assert.equal(Core.validReport(report),true);
  assert.equal(report.source.synthetic,true);
  assert.equal(report.selection.uses_test_for_model_selection,false);
});
test('dataset source catalog contains no non-HTTPS download link',()=>{
  const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../web/data/catalog.json'),'utf8'));
  assert.ok(catalog.length>=10);
  for(const item of catalog){assert.match(item.source,/^https:\/\//);assert.ok(item.license);}
});

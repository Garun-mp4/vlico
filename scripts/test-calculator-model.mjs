import assert from 'node:assert/strict';
import {initial, visible, change, validate, restore, STORAGE_KEY} from '../backend/static/calculator/model.js';
const schema={fields:{lights:{kind:'multi',choices:[['spots','Spots'],['none','None'],['unknown','Unknown']]},length:{kind:'number',integer:false,max:100},name:{kind:'text'},room:{kind:'choice',choices:[['living','Living']]}}};
let a=initial();a=change(a,'lights','spots',true);a=change(a,'spots','6');
assert.equal(visible('spots',a),true);a=change(a,'lights','none',true);assert.deepEqual(a.lights,['none']);assert.equal(visible('spots',a),false);
a=change(a,'lights','tracks',true);assert.deepEqual(a.lights,['tracks']);
assert.equal(visible('length',{...a,size_mode:'area'}),false);assert.equal(visible('area',{...a,shape:'l'}),true);
const fields={length:{kind:'number',integer:false,max:100}};
assert.deepEqual(validate({...initial(),length:'5,25'},{fields:['length']},fields),{});
for(const length of ['NaN','-1','0','5.123','101'])assert.ok(validate({...initial(),length},{fields:['length']},fields).length);
assert.deepEqual(validate({...initial(),length:'1.5'},{fields:['length']},{length:{...fields.length,integer:true}}).length!==undefined,true);
globalThis.sessionStorage={getItem:key=>key===STORAGE_KEY?JSON.stringify({schema:'v1',room:'living'}):null};assert.equal(restore(schema).room,'');
globalThis.sessionStorage={getItem:()=>JSON.stringify({schema:'v2',room:'bogus',lights:['spots','hack'],contact:'private'})};
assert.deepEqual(restore(schema).lights,['spots']);assert.equal(restore(schema).room,'');assert.equal(restore(schema).contact,undefined);

globalThis.sessionStorage={getItem:()=>JSON.stringify({schema:'v2',lights:['spots','none','spots'],length:'1e309'})};
assert.deepEqual(restore(schema).lights,[]);assert.equal(restore(schema).length,undefined);
globalThis.sessionStorage={getItem:()=>JSON.stringify({schema:'v2',lights:['spots','spots'],length:'5,25'})};
assert.deepEqual(restore(schema).lights,['spots']);assert.equal(restore(schema).length,'5,25');
assert.ok(validate({...initial(),length:'0.1',width:'0.1'},{fields:['length','width']},{length:fields.length,width:fields.length}).length);

assert.deepEqual(validate({...initial(),length:'0.1',width:'0.95'},{fields:['length','width']},{length:fields.length,width:fields.length}),{});
console.log('Calculator model: conditional fields, exclusive answers, decimal validation, minimum area and versioned restoration passed.');

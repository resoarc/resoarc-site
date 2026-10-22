import test from 'node:test';
import assert from 'node:assert/strict';
import {snapshotToInitialSheets} from '../src/snapshot.mjs';
import {restoreNumericCells} from '../src/numeric-types.mjs';
test('snapshot matrix converts to sparse entries without losing formula',()=>{
 const old=[{name:'売上',data:[[{v:'SKU'},null],[{v:12,ct:{t:'n'}},{f:'=A2*2',v:24}]]}];
 const restored=snapshotToInitialSheets(old);
 assert.equal(restored[0].celldata.length,3);
 assert.deepEqual(restored[0].celldata[2],{r:1,c:1,v:{f:'=A2*2',v:24}});
 assert.equal(restored[0].data,undefined);
});
test('already sparse snapshot stays intact',()=>{
 const current=[{name:'Sheet1',celldata:[{r:2,c:5,v:{v:'test'}}]}];
 assert.deepEqual(snapshotToInitialSheets(current),current);
});
test('numeric restoration preserves leading-zero text',()=>{
 const src=[{name:'Sheet1',data:[[{v:'003'},{v:'4',ct:{t:'s'}},{v:'=4*2',f:'=B1*2'}]]}];
 const types=new Map([['Sheet1',new Map([['0,1',4],['0,2',8]])]]);
 const fixed=restoreNumericCells(src,types);
 assert.equal(fixed[0].data[0][0].v,'003');
 assert.equal(fixed[0].data[0][1].v,4);
 assert.equal(fixed[0].data[0][1].ct.t,'n');
 assert.equal(fixed[0].data[0][2].v,8);
 assert.notEqual(fixed,src);
});
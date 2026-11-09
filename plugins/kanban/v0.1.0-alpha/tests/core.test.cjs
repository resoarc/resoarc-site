const test=require('node:test'),a=require('node:assert/strict'),core=require('../src/js/core.js');
const rows=[{$id:{value:'1'},Status:{value:'Open'},Title:{value:'A'}},{$id:{value:'2'},Status:{value:'Done'},Title:{value:'B'}},{$id:{value:'3'},Status:{value:'Open'},Title:{value:'C'}}];
test('kanban valid config',()=>a.equal(core.normalize([{groupField:'Status',labelField:'Title'}]).limit,60));
test('kanban rejects invalid limit',()=>a.equal(core.normalize([{groupField:'Status',labelField:'Title',limit:0}]),null));
test('kanban groups by exact value in stable order',()=>{const out=core.groups(rows,{groupField:'Status',labelField:'Title',limit:5});a.equal(out.groups.length,2);a.equal(out.groups[0].records.length,2);a.equal(out.groups[1].name,'Done');});
test('kanban honors upper bound',()=>{const out=core.groups(rows,{groupField:'Status',labelField:'Title',limit:1});a.equal(out.shown,1);a.equal(out.truncated,true);});
test('kanban does not mutate records',()=>{core.groups(rows,{groupField:'Status',labelField:'Title',limit:5});a.equal(rows[0].Title.value,'A');});

test('kanban detail link uses PC, mobile and guest-space routes',()=>{
 a.equal(core.recordLink('/k/42/','42','99',false),'/k/42/show#record=99');
 a.equal(core.recordLink('/k/m/42/','42','99',true),'/k/m/42/show?record=99');
 a.equal(core.recordLink('/k/guest/7/42/','42','99',false),'/k/guest/7/42/show#record=99');
 a.equal(core.recordLink('/k/guest/7/m/42/','42','99',true),'/k/guest/7/m/42/show?record=99');
});
test('kanban skips invalid app or record links',()=>{
 a.equal(core.recordLink('/k/guest/trash/42','42','99',true),'/k/m/42/show?record=99');
 a.equal(core.recordLink('/k/42','../42','99',false),null);
 a.equal(core.recordLink('/k/42','42','javascript:alert(1)',false),null);
 a.equal(core.recordLink('/k/42','42','0',false),null);
});

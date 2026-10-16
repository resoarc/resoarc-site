const test=require('node:test'),a=require('node:assert/strict'),core=require('../src/js/core.js');
const rows=[{$id:{value:'1'},Status:{value:'Open'},Title:{value:'A'}},{$id:{value:'2'},Status:{value:'Done'},Title:{value:'B'}},{$id:{value:'3'},Status:{value:'Open'},Title:{value:'C'}}];
test('kanban valid config',()=>a.equal(core.normalize([{groupField:'Status',labelField:'Title'}]).limit,60));
test('kanban rejects invalid limit',()=>a.equal(core.normalize([{groupField:'Status',labelField:'Title',limit:0}]),null));
test('kanban groups by exact value in stable order',()=>{const out=core.groups(rows,{groupField:'Status',labelField:'Title',limit:5});a.equal(out.groups.length,2);a.equal(out.groups[0].records.length,2);a.equal(out.groups[1].name,'Done');});
test('kanban honors upper bound',()=>{const out=core.groups(rows,{groupField:'Status',labelField:'Title',limit:1});a.equal(out.shown,1);a.equal(out.truncated,true);});
test('kanban does not mutate records',()=>{core.groups(rows,{groupField:'Status',labelField:'Title',limit:5});a.equal(rows[0].Title.value,'A');});

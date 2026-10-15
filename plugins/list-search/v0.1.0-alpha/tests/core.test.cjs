const test=require('node:test'),a=require('node:assert/strict'),core=require('../src/js/core.js');
test('search config validates supported modes',()=>a.equal(core.normalize([{code:'Name',operator:'contains'}]).length,1));
test('search config rejects unsupported operator',()=>a.equal(core.normalize([{code:'Name',operator:'script'}]),null));
test('search contains and normalization',()=>a.equal(core.filter([{Name:{value:'ＡBC'}},{Name:{value:'zzz'}}],{code:'Name',operator:'contains'},'abc').length,1));
test('search equality',()=>a.equal(core.filter([{Name:{value:'foo'}},{Name:{value:'foobar'}}],{code:'Name',operator:'equals'},'foo').length,1));
test('search prefix',()=>a.equal(core.filter([{Name:{value:'foo bar'}},{Name:{value:'bar foo'}}],{code:'Name',operator:'startsWith'},'foo').length,1));
test('search returns copy and does not mutate input',()=>{const items=[{Name:{value:'x'}}];const out=core.filter(items,{code:'Name'},'');a.notEqual(items,out);a.equal(items.length,1);});

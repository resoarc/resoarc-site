/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { createApp } from '/assets/qaiuick/qaiuick.js';
import { createStore } from '/assets/qaiuick/store.js';
import { seedOnce, resetSamples } from './sample-data.js';

const namespace = 'resoarc-qaiuick-sample-budget-v1';
const store = createStore({ namespace });
const examples = [
  {id:'expense-1',category:'食費',amount:980,note:'お昼の定食'},
  {id:'expense-2',category:'交通',amount:760,note:'電車'},
  {id:'expense-3',category:'日用品',amount:1480,note:'洗剤'},
  {id:'expense-4',category:'食費',amount:2250,note:'食材の買い物'},
  {id:'expense-5',category:'趣味',amount:3300,note:'画材'},
];
const yen = n => Number(n).toLocaleString('ja-JP') + ' 円';
const state={items:[],draft:{category:'食費',amount:'',note:''},error:''};
const app=createApp({
  root:'#app',state,
  computed:{
    total:s=>yen(s.items.reduce((sum,item)=>sum+Number(item.amount),0)),
    foodTotal:s=>yen(s.items.filter(item=>item.category==='食費')
      .reduce((sum,item)=>sum+Number(item.amount),0)),
    count:s=>s.items.length,
    empty:s=>s.items.length===0,
  },
  actions:{
    async add(s){
      const amount=Number(s.draft.amount),note=s.draft.note.trim();
      if(!note || !Number.isSafeInteger(amount) || amount<1 || amount>10000000){
        s.error='用途と1〜10000000円の整数を入力してください';return;
      }
      await store.save({category:s.draft.category,amount,note});
      s.items=await store.list();s.draft={category:'食費',amount:'',note:''};s.error='';
    },
    async remove(s,{arg}){await store.remove(arg);s.items=await store.list();s.error='';},
    async reset(s){s.items=await resetSamples(store,examples);s.error='';},
  },
  onError(error){state.error=error.message;app.render();},
});

// The initial examples are inserted only when no saved list exists.
try { state.items = await seedOnce(store, namespace, examples); app.render(); }
catch (error) { state.error = `保存データを読み込めません: ${error.message}`; app.render(); }

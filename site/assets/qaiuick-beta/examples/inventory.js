/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { createApp } from '/assets/qaiuick/qaiuick.js';
import { createStore } from '/assets/qaiuick/store.js';
import { seedOnce, resetSamples } from './sample-data.js';

const namespace = 'resoarc-qaiuick-sample-inventory-v1';
const store = createStore({ namespace });
const examples = [
  { id:'stock-1', name:'M3ボルト', category:'部品', qty:48, min:20 },
  { id:'stock-2', name:'USB-Cケーブル', category:'部品', qty:8, min:12 },
  { id:'stock-3', name:'養生テープ', category:'消耗品', qty:6, min:5 },
  { id:'stock-4', name:'六角レンチ', category:'工具', qty:3, min:4 },
  { id:'stock-5', name:'小型ケース', category:'部品', qty:25, min:10 },
];
const state = { items: [], draft:{name:'',qty:'1',min:'5',category:'部品'}, error:'' };
const app = createApp({
  root:'#app', state,
  computed:{
    itemCount:s => s.items.length,
    totalUnits:s => s.items.reduce((sum,item)=>sum + Number(item.qty||0),0),
    lowStock:s => s.items.filter(item=>Number(item.qty)<Number(item.min)).length,
    empty:s => s.items.length === 0,
  },
  actions:{
    async add(s){
      const name=s.draft.name.trim();
      const qty=Number(s.draft.qty), min=Number(s.draft.min);
      if(!name || !Number.isInteger(qty) || qty<0 || qty>99999 ||
        !Number.isInteger(min) || min<0 || min>99999) {
        s.error='品目名と0〜99999の整数を指定してください';return;
      }
      await store.save({ name, qty, min, category:s.draft.category });
      s.items=await store.list(); s.draft={name:'',qty:'1',min:'5',category:'部品'};s.error='';
    },
    async restock(s,{arg}){
      const item=await store.get(arg);if(!item)return;
      item.qty=Math.min(99999, Number(item.qty)+10);
      await store.save(item);s.items=await store.list();s.error='';
    },
    async remove(s,{arg}){await store.remove(arg);s.items=await store.list();s.error='';},
    async reset(s){s.items=await resetSamples(store,examples);s.error='';},
  },
  onError(error){state.error=error.message;app.render();},
});

// The initial examples are inserted only when no saved list exists.
try { state.items = await seedOnce(store, namespace, examples); app.render(); }
catch (error) { state.error = `保存データを読み込めません: ${error.message}`; app.render(); }

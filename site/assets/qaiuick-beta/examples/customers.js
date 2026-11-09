/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { createApp } from '/assets/qaiuick/qaiuick.js';
import { createStore } from '/assets/qaiuick/store.js';
import { seedOnce, resetSamples } from './sample-data.js';

const namespace='resoarc-qaiuick-sample-customers-v1';
const store=createStore({ namespace });
const examples=[
  {id:'customer-1',name:'佐藤 葵',company:'星野商事',region:'東京'},
  {id:'customer-2',name:'田中 智',company:'浜風製作所',region:'広島'},
  {id:'customer-3',name:'鈴木 春',company:'星野商事',region:'大阪'},
  {id:'customer-4',name:'山田 陽',company:'青葉デザイン',region:'福岡'},
  {id:'customer-5',name:'高橋 凛',company:'山崎工業',region:'東京'},
];
const state={items:[],query:'',draft:{name:'',company:'',region:''},error:''};
const matches=(item,query)=>[item.name,item.company,item.region]
  .some(value=>String(value).toLocaleLowerCase('ja-JP').includes(query));
const app=createApp({
  root:'#app',state,
  computed:{
    filtered:s=>s.items.filter(item=>matches(item,s.query.trim().toLocaleLowerCase('ja-JP'))),
    count:s=>s.items.length,
    visibleCount:s=>s.items.filter(item=>matches(item,s.query.trim().toLocaleLowerCase('ja-JP'))).length,
    companyCount:s=>new Set(s.items.map(item=>item.company)).size,
    empty:s=>!s.items.some(item=>matches(item,s.query.trim().toLocaleLowerCase('ja-JP'))),
  },
  actions:{
    async add(s){
      const name=s.draft.name.trim(),company=s.draft.company.trim(),region=s.draft.region.trim();
      if(!name||!company||!region){s.error='すべての項目を入力してください';return;}
      await store.save({name,company,region});
      s.items=await store.list();s.draft={name:'',company:'',region:''};s.query='';s.error='';
    },
    async remove(s,{arg}){await store.remove(arg);s.items=await store.list();s.error='';},
    async reset(s){s.items=await resetSamples(store,examples);s.query='';s.error='';},
  },
  onError(error){state.error=error.message;app.render();},
});

// The initial examples are inserted only when no saved list exists.
try { state.items = await seedOnce(store, namespace, examples); app.render(); }
catch (error) { state.error = `保存データを読み込めません: ${error.message}`; app.render(); }

/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { createApp } from '/assets/qaiuick/qaiuick.js';
import { createStore } from '/assets/qaiuick/store.js';
import { seedOnce, resetSamples } from './sample-data.js';

const namespace = 'resoarc-qaiuick-sample-tickets-v1';
const store = createStore({ namespace });
const stages=['未対応','対応中','完了'];
const examples=[
  {id:'ticket-1',title:'ログイン方法の確認',owner:'田中',status:'未対応'},
  {id:'ticket-2',title:'集計表の表示について',owner:'山本',status:'対応中'},
  {id:'ticket-3',title:'添付ファイルの保存方法',owner:'佐々木',status:'完了'},
  {id:'ticket-4',title:'モバイル画面の使い方',owner:'鈴木',status:'未対応'},
];
const state={items:[],draft:{title:'',owner:''},error:''};
const app=createApp({
  root:'#app',state,
  computed:{
    openCount:s=>s.items.filter(item=>item.status!=='完了').length,
    doneCount:s=>s.items.filter(item=>item.status==='完了').length,
    count:s=>s.items.length,
    empty:s=>s.items.length===0,
  },
  actions:{
    async add(s){
      const title=s.draft.title.trim(),owner=s.draft.owner.trim();
      if(!title||!owner){s.error='内容と担当者を入力してください';return;}
      await store.save({title,owner,status:'未対応'});
      s.items=await store.list();s.draft={title:'',owner:''};s.error='';
    },
    async advance(s,{arg}){
      const record=await store.get(arg);if(!record)return;
      const current=stages.indexOf(record.status);
      record.status=stages[(current+1)%stages.length];
      await store.save(record);s.items=await store.list();s.error='';
    },
    async remove(s,{arg}){await store.remove(arg);s.items=await store.list();s.error='';},
    async reset(s){s.items=await resetSamples(store,examples);s.error='';},
  },
  onError(error){state.error=error.message;app.render();},
});

// The initial examples are inserted only when no saved list exists.
try { state.items = await seedOnce(store, namespace, examples); app.render(); }
catch (error) { state.error = `保存データを読み込めません: ${error.message}`; app.render(); }

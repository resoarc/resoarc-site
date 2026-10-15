/*!
 * ResoArc File SHA-256 Tool v1.0.0
 * Copyright (c) 2026 ResoArc Open Technology Project
 * MIT License (see /licenses/RESOARC-MIT.txt)
 * Processes selected file only in local browser memory. No network requests.
 */
(()=>{
  "use strict";
  const $=id=>document.getElementById(id);
  const MAX=100*1024*1024;
  const pick=$("hash-file"),drop=$("hash-drop"),go=$("hash-go"),reset=$("hash-reset"),expected=$("hash-expected"),out=$("hash-result"),status=$("hash-status"),copy=$("hash-copy"),verdict=$("hash-verdict"),meta=$("hash-meta");
  let selected=null;
  function setStatus(msg,kind=""){status.textContent=msg;status.dataset.status=kind;}
  function clear(){out.value="";copy.disabled=true;verdict.textContent="";meta.textContent="";}
  function selectedFile(file){
    selected=file||null; clear();
    if(!selected){drop.querySelector("strong").textContent="ファイルを選択する";go.disabled=true;setStatus("ファイルはブラウザー内で処理されます。");return;}
    drop.querySelector("strong").textContent=selected.name;
    go.disabled=selected.size>MAX;
    meta.textContent=selected.name+" · "+selected.size.toLocaleString("ja-JP")+" バイト";
    if(selected.size>MAX){setStatus("100 MiBを超えるファイルは処理できません。","error");}
    else setStatus("「SHA-256を計算」を押してください。");
  }
  pick.addEventListener("change",()=>selectedFile(pick.files?.[0]));
  drop.addEventListener("dragover",e=>{e.preventDefault();drop.classList.add("drag");});
  drop.addEventListener("dragleave",()=>drop.classList.remove("drag"));
  drop.addEventListener("drop",e=>{e.preventDefault();drop.classList.remove("drag"); if(e.dataTransfer?.files?.length)selectedFile(e.dataTransfer.files[0]);});
  drop.addEventListener("keydown",e=>{if((e.key==="Enter"||e.key===" ") && e.target===drop){e.preventDefault();pick.click();}});
  go.addEventListener("click",async()=>{
    if(!selected)return; const current=selected;
    go.disabled=true;clear();setStatus("ブラウザー内で計算しています…");
    try{
      if(!globalThis.crypto?.subtle)throw Error("このブラウザーでは暗号化APIを利用できません。HTTPSで開いてください。");
      if(current.size>MAX)throw Error("100 MiBを超えるファイルは処理できません。");
      const buffer=await current.arrayBuffer();
      const digest=await crypto.subtle.digest("SHA-256",buffer);
      if(current!==selected)return;
      const hex=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,"0")).join("");
      out.value=hex;copy.disabled=false;
      const ref=expected.value.trim().toLowerCase().replace(/\s+/g,"");
      if(ref){
        if(!/^[a-f0-9]{64}$/.test(ref)){verdict.textContent="照合値は64桁の16進数で入力してください。";verdict.dataset.kind="error";}
        else if(hex===ref){verdict.textContent="照合結果：一致";verdict.dataset.kind="success";}
        else {verdict.textContent="照合結果：不一致。ファイルや照合値を確認してください。";verdict.dataset.kind="error";}
      }
      setStatus("計算完了。ファイル内容はサーバーへ送信していません。","success");
    }catch(e){setStatus("計算できませんでした："+(e?.message||String(e)),"error");}
    finally {go.disabled=!selected||selected.size>MAX;}
  });
  expected.addEventListener("input",()=>{verdict.textContent="";});
  copy.addEventListener("click",async()=>{
    if(!out.value)return;
    try{await navigator.clipboard.writeText(out.value);setStatus("ハッシュ値をコピーしました。","success");}
    catch{out.focus();out.select();setStatus("コピーできませんでした。表示された値を選択してコピーしてください。","error");}
  });
  reset.addEventListener("click",()=>{pick.value="";expected.value="";selectedFile(null);});
  selectedFile(null);
})();
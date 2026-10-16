on(['app.record.detail.show','app.record.edit.show'],e=>{
 const root=panel();if(!root)return e;
 const href=template(cfg.url,e.record,true);
 let target;try{target=new URL(href,location.href)}catch(_){return e;}
 if(target.protocol!=='https:'||((target.origin!==location.origin)&&String(cfg.allowExternal||'false')!=='true'))return e;
 const link=el('a',cfg.label||'関連情報を開く');link.href=target.href;link.target='_blank';link.rel='noopener noreferrer';link.style.cssText='font-weight:600;color:#176c68';root.append(link);
 return e;
});

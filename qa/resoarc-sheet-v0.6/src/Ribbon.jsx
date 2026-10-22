import React from 'react';

const TABS=['ファイル','ホーム','挿入','ページレイアウト','数式','データ','校閲','表示'];
function Item({label,onClick,title,disabled=false,large=false,selected=false,children}){
 return <button type="button" className={'ribbon-item'+(large?' ribbon-large':'')+(selected?' ribbon-selected':'')} title={title||label} aria-label={label} disabled={disabled} onClick={onClick}>
 <span className="ribbon-item-mark" aria-hidden="true">{children}</span><span className="ribbon-item-label">{label}</span></button>;
}
function Group({label,children}){return <div className="ribbon-group"><div className="ribbon-group-content">{children}</div><span className="ribbon-group-label">{label}</span></div>}
export default function Ribbon({tab,onTab,busy,hasSource,safeReady,onCommand,format,filename}){
 const button=(label,cmd,symbol,disabled=false,title)=> <Item key={cmd} label={label} onClick={()=>onCommand(cmd)} disabled={busy||disabled} title={title}>{symbol}</Item>;
 return <div className="excel-ribbon">
  <div className="ribbon-tabs" role="tablist" aria-label="メインメニュー">
   {TABS.map(t=><button type="button" role="tab" key={t} aria-selected={tab===t} className={'ribbon-tab'+(tab===t?' active':'')+(t==='ファイル'?' file-tab':'')} onClick={()=>onTab(t)}>{t}</button>)}
   <div className="ribbon-tabs-spacer"/>
   <span className="ribbon-name-hint" title={filename}>{filename}</span>
  </div>
  <div className="ribbon-content" role="tabpanel" aria-label={tab+' タブ'}>
   {tab==='ファイル'&&<>
    <Group label="ブック">{button('新規','new','▤')}{button('開く','open','⌕')}{button('保存','save','▣')}{button('安全保存','safe','◇',!hasSource||!safeReady,'原本の構造を残してセル値のみ保存')}</Group>
    <Group label="エクスポート">{button('CSV保存','csv','≡')}{button('バックアップ','backup','▱')}{button('復元','restore','↺')}</Group>
   </>}
   {tab==='ホーム'&&<>
    <Group label="履歴">{button('元に戻す','undo','↶')}{button('やり直す','redo','↷')}</Group>
    <Group label="フォント">
     <div className="ribbon-stack"><div className="ribbon-selectrow">
      <label className="sr-only" htmlFor="font-select">フォント</label>
      <select id="font-select" value={format.font} disabled={busy} onChange={e=>onCommand('font',e.target.value)}><option value="Arial">Arial</option><option value="Yu Gothic">游ゴシック</option><option value="Meiryo">メイリオ</option><option value="Noto Sans JP">Noto Sans JP</option><option value="Times New Roman">Times New Roman</option></select>
      <label className="sr-only" htmlFor="font-size">フォントサイズ</label>
      <select id="font-size" value={format.size} disabled={busy} onChange={e=>onCommand('fontSize',Number(e.target.value))}>{[8,9,10,11,12,14,16,18,20,24,28,32,36].map(n=><option key={n} value={n}>{n}</option>)}</select>
     </div>
     <div className="ribbon-formatrow">
      {button('太字','bold','B',false,'太字 (Ctrl+B)')}{button('斜体','italic','I')}{button('下線','underline','U')}
      <label className="color-label" title="文字色">A <input aria-label="文字色" type="color" value={format.color} disabled={busy} onChange={e=>onCommand('fontColor',e.target.value)}/></label>
      <label className="color-label" title="塗りつぶし">▨ <input aria-label="塗りつぶし" type="color" value={format.fill} disabled={busy} onChange={e=>onCommand('fill',e.target.value)}/></label>
     </div></div>
    </Group>
    <Group label="配置">{button('左揃え','left','☰')}{button('中央揃え','center','☷')}{button('右揃え','right','≡')}</Group>
    <Group label="数値">{button('標準','general','123')}{button('パーセント','percent','%')}{button('小数点','decimal','0.0')}</Group>
    <Group label="セル">{button('内容を消去','clear','⌫')}{button('セルの書式','formatDialog','▤',false,'セルの書式設定 (Ctrl+1)')}</Group>
   </>}
   {tab==='挿入'&&<><Group label="セルとシート">{button('上に行を挿入','insertRow','＋↕')}{button('左に列を挿入','insertCol','＋↔')}{button('新しいシート','addSheet','＋▤')}</Group><div className="ribbon-explainer">グラフ・画像の新規作成は今後対応予定です。既存グラフは「安全保存」で保持できます。</div></>}
   {tab==='ページレイアウト'&&<div className="ribbon-explainer">ページサイズ・余白・印刷範囲などは現在未対応です。既存のページ設定は「安全保存」で保持できます。</div>}
   {tab==='数式'&&<><Group label="関数を入力">{button('合計','sum','Σ')}{button('平均','average','x̄')}{button('最大','max','↑')}{button('最小','min','↓')}</Group><div className="ribbon-explainer">数式は下の数式バーから直接入力できます。例: =SUM(A1:A5)</div></>}
   {tab==='データ'&&<><Group label="データ編集">{button('行を挿入','insertRow','＋↕')}{button('列を挿入','insertCol','＋↔')}{button('内容を消去','clear','⌫')}</Group><div className="ribbon-explainer">並べ替え・フィルターは現段階では表計算エンジン側の機能を利用してください。</div></>}
   {tab==='校閲'&&<><Group label="サポート">{button('使い方','help','ⓘ')}{button('互換性監査','audit','⌕',!hasSource)}</Group></>}
   {tab==='表示'&&<><Group label="ウィンドウ">{button('先頭行を固定','freezeRow','▦')}{button('先頭列を固定','freezeCol','▥')}{button('固定を解除','unfreeze','☷')}</Group><Group label="ブック">{button('新しいシート','addSheet','＋▤')}</Group></>}
  </div>
 </div>;
}

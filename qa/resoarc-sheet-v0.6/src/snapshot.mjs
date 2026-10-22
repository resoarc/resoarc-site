// Restore getAllSheets() snapshots to the input layout expected by FortuneSheet.
// The engine exports a 2D "data" grid but initializes from sparse "celldata".
export function snapshotToInitialSheets(sheets) {
 if(!Array.isArray(sheets)||!sheets.length)throw new Error('シートデータがありません。');
 return sheets.map(sheet=>{
  if(!sheet||typeof sheet!=='object')throw new Error('無効なシートデータです。');
  if(!Array.isArray(sheet.data))return {...sheet};
  const celldata=[];
  let cols=0;
  sheet.data.forEach((row,r)=>{
   if(!Array.isArray(row))return;
   cols=Math.max(cols,row.length);
   row.forEach((cell,c)=>{if(cell!==null&&cell!==undefined)celldata.push({r,c,v:cell});});
  });
  const {data,...other}=sheet;
  return {...other,celldata,row:Math.max(20,sheet.data.length),column:Math.max(10,cols)};
 });
}
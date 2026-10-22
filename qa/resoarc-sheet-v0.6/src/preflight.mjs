import JSZip from 'jszip';

/** Non-destructive risk scan before importing an OOXML workbook. These flags are advisory, not comprehensive. */
export async function scanWorkbook(file) {
  const lower = file.name.toLowerCase();
  if (lower.endsWith('.xls') || lower.endsWith('.xlsm') || lower.endsWith('.xlsb'))
    throw new Error('この形式は安全に保存できません。.xlsx または .csv を使ってください（マクロ付き・旧形式は非対応）。');
  if (!lower.endsWith('.xlsx') && !lower.endsWith('.csv'))
    throw new Error('読み込める形式は .xlsx と .csv です。');
  if (file.size > 20 * 1024 * 1024)
    throw new Error('現在の検証版では20MBを超えるファイルは読み込めません。');
  if (lower.endsWith('.csv')) return [];
  let zip;
  try {zip = await JSZip.loadAsync(file);} catch {throw new Error('Excelファイルを読み取れません。破損またはパスワード保護の可能性があります。');}
  const paths = Object.keys(zip.files).filter(p=>!zip.files[p].dir);
  if (!paths.includes('xl/workbook.xml'))
    throw new Error('正しい .xlsx ワークブックではありません。暗号化ファイルには対応していません。');
  const rules = [
    [/xl\/vbaProject/i,'マクロやVBAを含みます'],
    [/xl\/pivotTables\//i,'ピボットテーブルを含みます'],
    [/xl\/charts\//i,'グラフを含みます'],
    [/xl\/drawings\//i,'図形・画像を含みます'],
    [/xl\/externalLinks\//i,'外部リンクを含みます'],
    [/xl\/embeddings\//i,'埋め込みオブジェクトを含みます'],
    [/xl\/connections\.xml/i,'外部データ接続を含みます'],
    [/xl\/slicers\//i,'スライサーを含みます'],
    [/xl\/queryTables\//i,'クエリテーブルを含みます'],
    [/xl\/comments\d*\.xml/i,'従来形式のコメントを含みます'],
  ];
  return rules.filter(([regex])=>paths.some(path=>regex.test(path))).map(([,name])=>name);
}
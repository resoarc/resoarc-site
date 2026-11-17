import ExcelJS from 'exceljs';

/**
 * Re-serialize the normal FortuneExcel export through ExcelJS to produce
 * OOXML readable by desktop Microsoft Excel. Do not touch safe-preserve files.
 */
export async function normalizeXlsxForExcel(inputBlob) {
  if (!(inputBlob instanceof Blob) || inputBlob.size < 4) throw Error('XLSX出力データがありません。');
  if (inputBlob.size > 50 * 1024 * 1024) throw Error('XLSXの正規化は50MBまでです。');
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.load(await inputBlob.arrayBuffer());
  if (!workbook.worksheets.length) throw Error('XLSXにシートがありません。');
  const result = await workbook.xlsx.writeBuffer();
  return new Blob([result], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
}

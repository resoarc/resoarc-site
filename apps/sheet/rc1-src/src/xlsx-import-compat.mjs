import JSZip from 'jszip';

const spreadsheetNamespace = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main';
const mainNamespaceDeclaration = 'xmlns:x="' + spreadsheetNamespace + '"';
const supportedXmlPart = /^xl\/(?:workbook\.xml|styles\.xml|sharedStrings\.xml|worksheets\/sheet\d+\.xml|tables\/table\d+\.xml)$/;

/**
 * FortuneExcel's regular-expression OOXML parser expects unprefixed SpreadsheetML
 * elements and empty elements without a space before "/>" (e.g. <border/>).
 * Both <x:worksheet> and <border /> are valid XML, but the upstream parser
 * silently skips sheets or throws when it encounters these spellings.
 *
 * Produce an import-only copy. Never change the original source File:
 * safe-preserve XLSX exports must continue to use the untouched original ZIP.
 */
export async function normalizeXlsxForImport(file) {
  if (!file?.name?.toLowerCase().endsWith('.xlsx')) return file;

  const archive = await JSZip.loadAsync(await file.arrayBuffer());
  let modified = false;

  for (const [path,entry] of Object.entries(archive.files)) {
    if (entry.dir || !supportedXmlPart.test(path)) continue;
    const original = await entry.async('string');
    let xml = original;

    if (xml.includes(mainNamespaceDeclaration)) {
      if (xml.includes('xmlns="' + spreadsheetNamespace + '"')) {
        // Do not create duplicate default namespace declarations.
        xml = xml.replace(mainNamespaceDeclaration,'');
      } else {
        xml = xml.replace(mainNamespaceDeclaration,'xmlns="' + spreadsheetNamespace + '"');
      }
      xml = xml.replace(/<(\/?)x:/g,'<$1');
    }

    // Compact otherwise valid self-closing XML to the spelling FortuneExcel
    // accepts. This is a lexical change, not a change to cell contents.
    if (path === 'xl/styles.xml' || xml !== original) {
      xml = xml.replace(/(<[A-Za-z_][A-Za-z0-9_:\-]*(?:\s+[^<>]*?)?)\s+\/>/g,'$1/>');
    }

    if (xml !== original) {
      archive.file(path,xml);
      modified = true;
    }
  }

  if (!modified) return file;
  const bytes = await archive.generateAsync({type:'uint8array',compression:'DEFLATE',compressionOptions:{level:6}});
  return new File([bytes],file.name,{type:file.type||'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',lastModified:file.lastModified||Date.now()});
}

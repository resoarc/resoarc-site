// Bounded, cleanup-safe kintone cursor reader for backups.
export async function fetchAllRecords(app, api, {maxRecords=20000}={}) {
  if (typeof api !== 'function') throw Error('kintone API関数が必要です');
  if (!Number.isSafeInteger(maxRecords) || maxRecords < 1) throw Error('取得件数の上限が不正です');
  const created = await api('/k/v1/records/cursor.json', 'POST', {app, size:500});
  if (typeof created?.id !== 'string' || !created.id) throw Error('バックアップ用Cursorの作成に失敗しました');
  const records = [];
  let finished = false;
  try {
    while (!finished) {
      const page = await api('/k/v1/records/cursor.json', 'GET', {id:created.id});
      if (!Array.isArray(page?.records) || typeof page.next !== 'boolean' || page.records.length > 500)
        throw Error('バックアップ用Cursorの取得結果が不正です');
      if (page.next && page.records.length === 0)
        throw Error('バックアップ用Cursorが進行しません。処理を中止します');
      if (records.length + page.records.length > maxRecords)
        throw Error('一度に処理できるレコードは' + maxRecords.toLocaleString('en-US') + '件までです');
      records.push(...page.records);
      finished = !page.next;
    }
  } finally {
    if (!finished) {
      try { await api('/k/v1/records/cursor.json', 'DELETE', {id:created.id}); }
      catch (error) { console.warn('Backup cursor cleanup failed', error); }
    }
  }
  return records;
}

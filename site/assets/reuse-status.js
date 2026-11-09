/* SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 * SPDX-License-Identifier: MIT
 * Show the actual checked commit. Historical badges never imply current compliance. */
(() => {
  const host = document.getElementById('reuse-live-check');
  if (!host) return;
  const status = host.querySelector('[data-reuse-state]');
  const details = host.querySelector('[data-reuse-detail]');
  const log = host.querySelector('[data-reuse-log]');
  const url = 'https://codeberg.org/api/v1/repos/ResoArc/resoarc-site/actions/runs?limit=5';
  const fallback = () => {
    status.textContent = 'ローカルREUSE検査は合格、Codeberg CIは稼働確認待ち';
    status.dataset.result = 'pending';
    fetch('/recognition/reuse-status.json').then(r=>r.json()).then(d=>{
      const check=d.latest_local_review;
      if(!check) return;
      details.textContent='ローカル検査: '+new Date(check.checked_at_utc).toLocaleString('ja-JP')+
        ' / 対象ベースコミット '+check.based_on_code_commit.slice(0,12)+
        ' / '+check.files_with_license_info+'件合格。現行mainのCI合格とは別の記録です。';
    }).catch(()=>{details.textContent='現行mainのCI合格確認待ち。ローカル503件合格の履歴は状態JSONを参照してください。';});
    log.hidden = false;
    log.textContent = 'Codeberg Actionsの設定・実行状況を見る ↗';
    log.href = 'https://codeberg.org/ResoArc/resoarc-site/actions';
  };
  fallback();
  fetch(url, {headers:{Accept:'application/json'}})
    .then(r => {if(!r.ok) throw new Error('CI_HTTP_'+r.status);return r.json();})
    .then(x => {
      const runs=x.workflow_runs || [];
      const run=runs.find(v=>String(v.path||v.name||'').includes('reuse-compliance')) || runs[0];
      if(!run) return fallback();
      const sha=run.head_sha || run.commit?.id || '';
      const date=run.updated_at || run.created_at;
      const stamp=date ? new Date(date).toLocaleString('ja-JP') : '日時不明';
      const success=run.status==='completed' && run.conclusion==='success';
      status.textContent = success ? 'Codeberg CI合格（対象コミット）' :
        run.status==='completed' ? 'Codeberg CI不合格（修正が必要）' : 'Codeberg CI検証中';
      status.dataset.result=success?'pass':run.status==='completed'?'fail':'pending';
      details.textContent='検査対象: '+(sha.slice(0,12)||'不明')+' / 実行: '+stamp+
        '。公開中のmainと同じコミットか照合してください。';
      log.hidden=false;
      log.href=run.html_url || ('https://codeberg.org/ResoArc/resoarc-site/actions/runs/'+run.id);
      log.textContent=success?'CI合格記録を見る ↗':'検査失敗の原因・ログを見る ↗';
    })
    .catch(fallback);
})();

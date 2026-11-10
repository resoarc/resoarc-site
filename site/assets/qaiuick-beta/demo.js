/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { quickApp } from '/assets/qaiuick/quick.js';

// Just data and a key. Forms, saving, redraw, add/remove/reset are automatic.
quickApp({
  key: 'resoarc-qaiuick-public-beta',
  sample: [
    { id: 'memo-1', title: 'qAIUIckのコードを読んでみる' },
    { id: 'memo-2', title: 'HTML・CSS・JSを切り替えて確認する' },
    { id: 'memo-3', title: 'メモを追加して保存を試す' },
  ],
  data: { draft: '' },
});

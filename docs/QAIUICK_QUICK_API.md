# qAIUIck Quick API (v0.3 beta)

**Goal:** write application behavior, not storage and rendering plumbing.

## Minimal local Todo

HTML in `index.html`:

```html
<div id="app">
  <form q-submit="add">
    <input q-model="draft" placeholder="メモ" required>
    <button>追加</button>
  </form>
  <template q-each="items" q-as="item">
    <p><span q-text="item.title"></span>
       <button q-action="remove" q-arg="item.id">削除</button></p>
  </template>
  <p q-show="empty">まだありません</p>
</div>
<script type="module" src="./main.js"></script>
```

JavaScript in `main.js`:

```javascript
import { quickApp } from '../../src/quick.js';

quickApp({
  key: 'my-todo',
  data: { draft: '' },
});
```

The core supplies `items`, `count`, `empty`, and `error`; the default `add`, `remove`, and `reset` actions; redraw; and localStorage persistence. Supply `sample: [{ id: 'one', title: 'Example' }]` to seed once. A saved empty array is **never** re-seeded unless the user explicitly calls reset.

The app author may override default actions. An action is `function(arg, event) { ... }` bound to the app state as `this`.

## Common operations

| Small operation | Purpose |
| --- | --- |
| `this.$add({title:'Hello'})` | Append a new record with an automatically generated ID |
| `this.$remove(id)` | Remove a record by ID |
| `this.$update(id, {done:true})` | Change matching record |
| `this.$update(id, row => { row.done = true; })` | Update using a callback |
| `this.$clear('draft')` | Restore the configured default for a form field |
| `this.$error('message')` | Show a message via `q-text="error"` |
| `this.$reset()` | Restore initial sample rows (explicit operation) |

Automatic persistence is performed **after** each action, followed by a redraw. The default `add` accepts a trimmed string `draft` as `{title:...}` or a `draft` record object; customize the action for nontrivial schema validation. Browser `required`/min/max attributes remain useful, but they are not a substitute for server-side validation.

Use `computed: { total: state => ... }` for derived values; do not persist these values manually.

## Storage and compatibility

- `persist: 'local'` (default): saves *only the records array* under `qaiuick:<key>:items`. This preserves the storage keys used by earlier qAIUIck demos.
- `persist: 'memory'`: keeps records only until page reload.
- For multiuser applications, SQL, authentication, permissions, or remote APIs, use the advanced `createApp()` / `createStore()` APIs and a real server. Quick API is intentionally not a substitute for an authenticated backend.
- Input text is rendered through textContent, not `innerHTML` or `eval`.
- The browser's localStorage is not a backup. Don't enter secrets or real personal records into demo pages.
- The Quick API does **not** automatically migrate schemas or reconcile concurrent edits across tabs; use explicit versioned migrations for production data.

## Design choice

`quickApp()` is a small facade over `createApp()`. Existing advanced APIs remain supported; no migration is required. All sample pages offer the actual HTML/CSS/JavaScript files and display the small application script by default.

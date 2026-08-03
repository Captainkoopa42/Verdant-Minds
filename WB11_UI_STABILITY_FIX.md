# WB-11 UI Stability Fix

This patch removes background full-root DOM replacement from the checked-in dependency-free Workbench UI.

Background WebSocket/status/queue traffic now updates dedicated live regions in place:
- engine/socket status
- Cultivate metrics
- execution state
- queue rows
- event rows
- Explorer canvas redraw

`render()` remains available for explicit navigation and user actions, but is not called by `backgroundRender()`.
This preserves focus, text selection, cursor position, and IME/composition state while Verdant is running.

Verification performed in the patched tree:
- `node --check workbench/frontend/dist/app.js`
- WB-11 tests: 3 passed
- WB-03 + WB-04 + WB-10 + WB-11 targeted regression set: 21 passed

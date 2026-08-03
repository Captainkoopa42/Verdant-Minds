# Workbench background refresh focus fix

The dependency-free browser build replaces the rendered DOM when `render()` runs.
Live websocket status and queue polling previously called `render()` repeatedly, which could
remove and recreate a focused input/textarea while an operator was typing.

The canonical `dist/app.js` now distinguishes explicit renders from background renders:

- live websocket repainting is limited to live-monitoring pages (`Organism`, `Cultivate`, `Explorer`);
- queue polling only repaints `Cultivate`, where queue state is actually visible;
- page-specific background refreshes defer repaint while an input, textarea, select, or contenteditable
  control has focus;
- deferred background repaint preserves scroll position.

Engine state and queue polling continue in the background even when repaint is deferred.
This is a UI focus-stability change only; it does not change engine or curriculum behavior.

## Why
- Roadmap tier-1 priorities call for "設定保存功能" right after drag/drop + preview so users stop reconfiguring grids, folders, and themes each session (see ROADMAP.md section 第一階段).
- Current app already has an in-memory ConfigManager but the main UI only restores a subset (window size/theme) and never exposes save/reset controls, so edits are forgotten.
- Persisting UI preferences improves day-to-day UX, especially for power users who rely on consistent grids, output folders, and recent paths.

## What Changes
- Auto-load the saved config at startup and hydrate every relevant field (theme, grid rows/cols, resize strategy, GIF duration, default output folders, file dialogs last-used paths).
- Save preferences whenever the user changes them (or clicks an explicit "保存" button) so next launch reflects their choices; include a "恢復預設" action.
- Surface a lightweight settings panel in the UI (or integrate into existing parameter cards) to make persistence discoverable, including confirmation toasts/status updates.
- Track recent media paths per feature so dialogs start in the last used directory.

## Impact
- Eliminates repetitive setup time per session, aligning with the productivity goals outlined in ROADMAP.
- Creates a foundation for future personalization (themes, presets) because the persistence API becomes reliable.
- Introduces small UI additions but no breaking external APIs; risk limited to config migrations handled by merge logic.
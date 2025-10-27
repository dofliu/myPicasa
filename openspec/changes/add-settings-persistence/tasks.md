## 1. Implementation
- [x] 1.1 Audit existing ConfigManager usage across tabs to list every field that must hydrate/save.
- [x] 1.2 Wire startup loaders so grid inputs, theme toggle, output folders, and dialog paths reflect persisted values.
- [x] 1.3 Add save triggers (auto + explicit) plus a reset-to-default control, including status bar/toast feedback.
- [x] 1.4 Keep ConfigManager in sync when preferences change (value validation, throttled disk writes) and extend it with recent-folder helpers where missing.
- [x] 1.5 Update docs/screenshots to explain the new persistence flow and capture regression notes for QA.

## 2. Validation
- [ ] 2.1 Manual test matrix: change each supported preference, restart app to verify persistence, then reset to defaults; include negative cases (bad paths) and multi-tab interactions.

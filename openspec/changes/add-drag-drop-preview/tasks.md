## 1. Implementation
- [x] 1.1 Review existing image/video intake flow in picasa*.py to identify hook points for event filters and data models.
- [x] 1.2 Implement drag-and-drop handlers (enter/move/leave/drop) with hover highlighting plus validation + error messaging for unsupported types.
- [x] 1.3 Add folder-walk logic that collects supported media recursively while keeping the UI responsive (threading or batched updates).
- [x] 1.4 Build thumbnail preview grid bound to the selected queue, showing metadata and allowing removal/re-order hooks.
- [x] 1.5 Wire previews to downstream processing (collage, GIF, merge) so they stay in sync and run targeted smoke tests across major flows.
- [x] 1.6 Update documentation (README/ROADMAP if needed) and capture screenshots or gifs for release notes.

## 2. Validation
- [ ] 2.1 Run manual drag/drop regression on Windows and at least one other OS target (if available) plus automated test suite.

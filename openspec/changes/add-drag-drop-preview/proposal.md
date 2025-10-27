## Why
- Roadmap prioritizes drag-and-drop import plus thumbnail preview as the highest ROI upgrade to unblock smoother workflows (see ROADMAP.md:383-400).
- Current UI requires manual file dialogs and offers no visual confirmation before processing, leading to slow setup and user errors.
- Delivering this change establishes the baseline UX foundation other enhancements (sorting, presets, etc.) will rely on.

## What Changes
- Add drag-and-drop ingestion for images, videos, and folders with clear visual feedback when files hover over valid drop zones.
- Auto-scan dropped folders to enqueue supported media while ignoring unsupported types and surfacing an error toast/log entry.
- Introduce a thumbnail preview grid that displays selected/dropped media, including filename, type, and size metadata with basic selection state.
- Keep previews in sync with downstream operations (ordering, removal) and ensure large batches remain responsive via pagination or lazy loading.

## Impact
- Cuts import friction to a single gesture and immediately shows users what will be processed.
- Reduces mistakes (wrong files/order) thanks to visual confirmation before invoking heavy jobs.
- Sets pattern library for future enhancements like drag-to-reorder and inline editing.
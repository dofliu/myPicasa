## ADDED Requirements

### Requirement: Drag-and-drop Media Intake
The workspace MUST accept drag-and-drop events for supported image/video files and folders with clear feedback and validation.

#### Scenario: Drop supported files
- **GIVEN** the user is on the main workspace with no modal dialogs open
- **WHEN** they drag one or more supported media files over the drop zone
- **THEN** the drop zone becomes visually highlighted to confirm it will accept the files
- **AND** releasing the mouse enqueues every supported file exactly once in the processing queue and surfaces a success toast summarizing counts
- **AND** any unsupported items are skipped with an inline error message that lists the skipped filenames without cancelling the rest.

#### Scenario: Drop folder of media
- **GIVEN** the user drags a folder containing mixed file types over the drop zone
- **WHEN** they release the folder
- **THEN** the system recursively scans the folder, enqueues only supported images/videos, and reports how many were added and skipped
- **AND** the UI remains responsive by chunking progress updates so the window does not freeze while large folders are processed.

### Requirement: Thumbnail Preview Grid
Users MUST see a live-updating thumbnail grid of every item queued for processing, including metadata and basic selection controls.

#### Scenario: Preview grid stays in sync
- **GIVEN** media items have been added via drag/drop or the legacy file picker
- **WHEN** the queue changes (add, remove, reorder)
- **THEN** the thumbnail grid refreshes to mirror the queue state, showing each thumbnail with filename, file type, and size
- **AND** selecting or removing an item inside the grid updates the underlying queue and downstream operations (collage, GIF, merge) without requiring a restart.
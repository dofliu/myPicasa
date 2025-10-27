## ADDED Requirements

### Requirement: Workspace Preferences Persistence
The application MUST load and save user-facing workspace preferences (theme, grid/gif parameters, output folders, resize strategy) so sessions start with the last known values.

#### Scenario: Preferences restored on launch
- **GIVEN** the user previously changed theme, grid columns/rows, GIF duration, and default output folders
- **WHEN** they relaunch the app
- **THEN** every associated control (theme toggle, QLineEdits, combo boxes) reflects the saved values without extra clicks
- **AND** invalid or missing config keys fall back to defaults without crashing
- **AND** a "重設" control restores defaults and persists them when used.

#### Scenario: Preferences saved automatically
- **GIVEN** the user modifies any preference control (e.g., changes grid columns from 3 to 5)
- **WHEN** they leave the control or click an explicit "保存設定" button
- **THEN** the new value is written to the config file within 500?ms
- **AND** the status bar or toast confirms the save so the user knows it succeeded.

### Requirement: Recent Folder Tracking
File dialogs MUST reopen in the last directory used per feature (images, videos, convert, documents) so users can resume workflows quickly.

#### Scenario: Dialog remembers last folder
- **GIVEN** the user selects images from `D:/Photos/2025/Trip`
- **WHEN** they reopen the image picker later in the same or next session
- **THEN** the dialog starts in `D:/Photos/2025/Trip` instead of the default path
- **AND** choosing a different folder updates the stored preference without affecting other features.
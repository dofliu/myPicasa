## ADDED Requirements

### Requirement: PDF Password Prompt Workflow
Document conversion features MUST detect encrypted PDFs and interactively prompt the user for passwords before proceeding.

#### Scenario: Prompt during PDF→Word
- **GIVEN** the user selects an encrypted PDF for PDF→Word conversion
- **WHEN** the converter detects the file requires a password
- **THEN** the app displays a modal asking for the password with options to retry or cancel
- **AND** entering the correct password unlocks the file and resumes conversion
- **AND** entering wrong passwords shows a clear error without crashing, allowing retry up to a set limit before aborting.

#### Scenario: Prompt during merge
- **GIVEN** the user adds a password-protected PDF into the merge list
- **WHEN** merge is triggered
- **THEN** the system pauses processing and asks for the password for that file (while remembering successful passwords for reuse in the same session)
- **AND** if the user cancels, the file is skipped and listed as “未合併 (密碼取消)” in the final summary.

### Requirement: Auto-convert Mixed Inputs to PDF Before Merge
PDF merge workflow MUST accept Word documents and supported image formats, converting them to PDF automatically before merging.

#### Scenario: Mixed-format merge
- **GIVEN** the user selects a mix of `.pdf`, `.docx`, `.png` files for merging
- **WHEN** they start the merge operation
- **THEN** the system converts non-PDF files to temporary PDFs (using existing converters) while showing progress per file
- **AND** conversion failures are reported per file but do not stop other files from merging
- **AND** temporary files are cleaned up after the merge completes.

#### Scenario: Pre-merge validation summary
- **GIVEN** the user provides any combination of supported files
- **WHEN** preprocessing finishes
- **THEN** a summary view (status bar toast or dialog) lists each file with its outcome (converted, skipped, waiting for password)
- **AND** continuing proceeds with only the successfully converted/unlocked PDFs.
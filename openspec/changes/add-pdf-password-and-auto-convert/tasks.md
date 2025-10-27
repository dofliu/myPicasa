## 1. Implementation
- [x] 1.1 Audit doc_converter + UI flows to list all password-sensitive operations and file inputs to merge.
- [x] 1.2 Implement a reusable password prompt dialog (with retry/cancel) and wire it into PDF¡÷Word and PDF merge pipelines.
- [x] 1.3 Add a preprocessing layer for merge: detect file type (PDF/Word/Image), convert non-PDF to temp PDF, and collect diagnostics.
- [x] 1.4 Update UI to display conversion/decryption status per file and surface clear error messages/logs.
- [x] 1.5 Extend documentation (README/ROADMAP) and add tests or sample scripts verifying password + auto-convert scenarios.

## 2. Validation
- [ ] 2.1 Manual matrix: cover encrypted PDFs (correct/incorrect password), plain PDFs, Word + image mixing, temp cleanup, and cancellation behavior.

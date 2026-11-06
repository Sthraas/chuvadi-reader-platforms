# Emulator test fixtures

- `no-print.pdf` — 3 pages (from `make-test-pdf.py`), AES-256, **empty open password** (opens without
  asking), random owner password, permissions mask from `PasswordService.BuildPermissionMask` with
  `AllowPrint = false`. Made with the Reader's own Core against chuvadi-pdf 3.31.2, the same way as
  Foundation's `TestSigning.ProtectRestricted` (the library has no public setter for permissions yet).
  Checked after writing: `PrintPermission.Allows` = false. Used by `platform.py` for L-8.

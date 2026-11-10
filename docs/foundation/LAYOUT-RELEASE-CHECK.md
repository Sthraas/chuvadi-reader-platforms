# Layout release check (10 Nov 2026, for D-145)

D-145: Word and Excel page view, print and Save as PDF wait for a published Chuvadi.Layout.Pdf release **and** published checksums. Checked against `github.com/arunshivab/chuvadi`: tags with `git ls-remote --tags`, release assets by direct download. (The releases API isn't reachable from here; the HTML release pages are refused too.)

## Result: still blocked
1. **There is no Chuvadi.Layout.Pdf release.** There is no `layout-pdf-*` tag, and `Chuvadi.Layout.Pdf.0.1.0.nupkg` isn't an asset of any Layout tag (all 6 tried). The Layout tags that exist are `layout-v0.1.0`, `layout-docs-v0.1.0`, `layout-documents-v0.1.0`, `layout-fonts-v0.1.0`, `layout-markup-v0.1.0` and `layout-sheets-v0.1.0`.
2. **No published checksum for any Layout-family package.** No `SHA256SUMS.txt`, `SHA256SUMS`, `sha256sums.txt`, `checksums.txt` or `<file>.sha256` asset exists at any of those tags, nor at `markup-v1.1.0`, `docs-v2.0.0` (Docs.Conversion) or `fonts-v1.1.0`.
   - GitHub may show a sha256 digest per asset on the release page or in the API; neither can be read from this session.
   - The chuvadi-pdf releases do publish `SHA256SUMS.txt`, which is the form D-145 asked for.

## What is there (downloaded unchanged; hashes computed here, not published)
| Package | Tag → commit | Depends on | SHA-256 (computed) |
|---|---|---|---|
| Chuvadi.Layout 0.1.0 | layout-v0.1.0 → bc1bfba | Chuvadi.Fonts 1.1.0 | `60986a652e66e25911ec1b37cd1cc227c028fa54c678177cc204566ec0b38fb9` |
| Chuvadi.Layout.Docs 0.1.0 | layout-docs-v0.1.0 → bc1bfba | Docs 2.0.0, Layout 0.1.0 | `08ca2440fdc9e7250ce12aebd877c6207737eb78a15d5749c4bb185008fe3138` |
| Chuvadi.Layout.Documents 0.1.0 | layout-documents-v0.1.0 → bc1bfba | Layout.Docs, Layout.Sheets 0.1.0 | `a0a70b5c6cb87dff7453d7a1dcc7749196e035fb58bbcaf1c499760b21f5a6da` |
| Chuvadi.Layout.Fonts 0.1.0 | layout-fonts-v0.1.0 → bc1bfba | Chuvadi.Fonts 1.1.0 | `6634b45667083354a7505da3d2ade4c8bcde951ff26b1e2f530ebd015ac03cc4` |
| Chuvadi.Layout.Markup 0.1.0 | layout-markup-v0.1.0 → bc1bfba | Layout 0.1.0, Markup 1.1.0 | `374ac6c0fb8da9a717c2dba58140790fbddd7c284ca8c60477a438b23f9eccf3` |
| Chuvadi.Layout.Sheets 0.1.0 | layout-sheets-v0.1.0 → bc1bfba | Layout 0.1.0, Sheets ≥ 2.0.2 | `4f83d4e68f0c28955987de2729c5677868b176765841b0d863bbe47a3ee27497` |
| Chuvadi.Markup 1.1.0 | markup-v1.1.0 → 0307a64 | — | `b5abe40df907715d333eca216b26bd89f2e8688d6ff87390cb86df8cbe26950e` |
| Chuvadi.Docs.Conversion 2.0.0 | docs-v2.0.0 → bc1bfba | Docs 2.0.0, Markup 1.1.0 | `5a4d530af2fa67264eeb2f83cb2b376222d3948199b1de800f25873efad2f1c7` |

**Also needed, not in ci/packages yet:** Chuvadi.Fonts 1.1.0 (we have 1.0.0). It is released (`fonts-v1.1.0`), also without a checksum file.

## What would unblock it
1. A Chuvadi.Layout.Pdf release (tag and nupkg).
2. A `SHA256SUMS.txt` (or one published SHA-256 per file) for every package above, Layout.Pdf, and Chuvadi.Fonts 1.1.0.

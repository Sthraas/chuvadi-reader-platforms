# Chuvadi.Docs 2.0.0 and Chuvadi.Sheets 2.0.2 in ci/packages (D-136, 9 Nov 2026)

Arun's decision D-136: the Foundation moves the Word and Excel libraries inside PR #11. They replace Chuvadi.Docs 1.1.0 and Chuvadi.Sheets 1.1.2, which are removed from `ci/packages`.

- **Source:** Arun's own release assets, downloaded unchanged from `github.com/arunshivab/chuvadi/releases/download/<tag>/<file>`. These are what the tags were released as; nothing was re-packed.
- **Ties to the tags:** each package's nuspec names the monorepo and the tag's commit.

| Package | Tag (object → commit) | Size | SHA-256 |
|---|---|---|---|
| Chuvadi.Docs.2.0.0.nupkg | `docs-v2.0.0` (425edc7 → bc1bfba) | 362,339 B | `35e4ddb3d7bac2cd5d78ac90ab437e2a92038a97777f506870b12a4891e1d087` |
| Chuvadi.Sheets.2.0.2.nupkg | `sheets-v2.0.2` (00243e7 → f561d84) | 353,606 B | `a137b5c84c431afdc6e872768fb4d79211e0fca9b0e8ee28f35c976db5944f99` |

Both target net10.0, have no package dependencies (their shared code is compiled in), and are MIT (notices regenerated). Chuvadi.Zip 1.0.0 stays for the Web chat (`PACKAGES-ZIP-1.0.0.md`); Docs and Sheets don't reference it.

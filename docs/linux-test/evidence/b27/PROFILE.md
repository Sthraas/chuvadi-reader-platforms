# B-27 profile — large vector CAD PDF (numbers and code paths only)

File: Arun's 7.9 MB site layout (5 × A1, ~1.44 M path operators, 170 images, 38 fonts). **Not in this repo**; no text or image from it is recorded here.
Machine: 2 vCPU, no GPU. Build: `platform/linux` e242d92 (Chuvadi.Pdf 3.31.2 family, Core as shipped).
Tools (test-only): `tools/b27-profiler.cs` (calls Core/library directly, per stage), `dotnet-trace` sampled thread time, `tools/t_uifreeze.py`.

## Per stage (warm OS cache; cold in `stages-cold.txt`)
| Stage | Time | Allocated | Notes |
|---|---|---|---|
| `PdfDocument.OpenAsync` | 56 ms (cold 467) | 16 MB | open is cheap |
| Reader open (`ChuvadiPdfReader.OpenAsync`) | 11 ms | 16 MB | |
| `FlattenService.Probe` | 2 ms | — | cheap on a normal file (it's the B-24 UI-thread open on a stalled one) |
| First interpretation of page 1 (raster at **18 dpi**) | **2,251 ms** | **771 MB** | cost is interpreting operators, not pixels |
| Raster page 1 at 150 dpi (what the Reader uses for large formats) | 2,383 ms | 1,693 MB | 3508 × 4967 px RGBA = 66 MB |
| `PngEncoder.Encode` of that buffer | **1,136 ms** | 279 MB | output only 1 MB |
| base64 + SVG wrapper | 5 ms | 10 MB | 2 M-char string |
| `session.RenderPageSvgAsync`, pages 1–5 | **3.5 / 3.8 / 5.0 / 4.9 / 4.6 s** | **2.0 / 1.5 / 3.0 / 3.3 / 2.5 GB** | each page interpreted + rasterised + PNG'd |
| Retained managed memory after 5 pages | — | — | **84 MB** (SVG cache only 34 MB) |

**Memory:** what the app holds is small (84 MB managed); the 1.6 GB RSS in the app is the GC heap expanding to absorb **1.5–3.3 GB of short-lived allocations per page** and not giving it back, plus WebKit decoding the page images (~250–480 MB). Not a leak; allocation churn.

## Where the CPU goes (sampled; 2 × 18 dpi + 1 × 150 dpi + 1 PNG encode, 7.5 s)
| Inclusive | Code path |
|---|---|
| 82 % | `PageRasterizer.Rasterize` |
| 41 % | ↳ `PaintDisplayList` → `ScanlineRasterizer.Fill` (33 %) — pixel fill, mostly the 150 dpi pass |
| 40 % | ↳ `DisplayListBuilder.Build` → `ContentStreamWalker.Walk` (35 %) / `Dispatch` (26 %) |
| 25 % | ↳↳ `ContentStreamLoader.Decode` → `DeflateFilter.Decode` → `DeflateInflater.InflateHuffmanBlock(List<…>)` / `HuffmanTree.Decode` (23 %) — **content streams are re-inflated on every render**, with the library's managed inflater |
| 23 % | ↳↳ `ShowTextComposite` → `ResolveFontRenderer` (20 %) → **`ExtractFontBytes` (20 %)** — **font programs re-extracted per text run** |
| 17 % | `PngEncoder.Encode` → `CompressWithZlib` (14 %) → own `DeflateDeflater.Tokenize` |

## UI responsiveness while the CAD page opens and draws (in the app)
Dispatcher round-trip polled 6,750 times over 12 s: median ~0 ms, **11 over 100 ms, worst 831 ms** (at the start of the open). The 3–5 s render does not freeze the UI.

## Suggestions for the library team (in order of likely gain)
1. **Cache the font program per font object** (`ExtractFontBytes`/`ResolveFontRenderer`) for the life of the document — ~20 % of render CPU.
2. **Cache decoded content streams** (or the built display list) per page, so re-renders (zoom, scroll back, layer toggle) skip inflate + walk — ~25 % inflate, 35 % walk.
3. **Faster inflate/deflate**: the BCL's `ZLibStream`/`DeflateStream` (part of .NET, not a third-party dependency) for `FlateDecode` and for the PNG encoder — the managed inflater uses `List<…>` in the Huffman path; PNG encode of 66 MB takes 1.1 s.
4. **Cut allocation churn** in `DisplayListBuilder`/`ContentStreamWalker` (0.5–1 KB per operator: 771 MB for one 18 dpi pass) — pooled operand buffers / structs for path segments; this is also what inflates the app's RSS.
5. App side (Reader, shared): for large formats consider tiled/progressive rendering at the visible zoom instead of a full 150 dpi page, and drop the base64 PNG round-trip (5–7 MB strings per page into the WebView).

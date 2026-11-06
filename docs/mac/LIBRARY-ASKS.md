# Library asks from the Mac chat

Sent to the coordinator for the library coordinator. Nothing here is worked around in the app.

## L-1 — Print-ready PDF: embed fonts the file does not embed (chuvadi-pdf)

**Context.** Printing must be vector (D-06). On macOS, Android and the Web, the OS print system receives
a PDF and renders it itself; Chuvadi first prepares that PDF (`Core/Reader/PrintDocumentBuilder.cs`:
chosen pages, decrypted, form fields and annotations flattened).

**Gap.** When a PDF uses a font it does not embed, Chuvadi's renderer substitutes (LiPi faces for Indic
scripts), but the prepared PDF still names the missing font, so the OS substitutes its own — or drops
glyphs. Printed output can then differ from the screen. Risk is highest for Tamil, Malayalam, Hindi and
other Indic text in PDFs from older generators.

**Ask.** An operation that writes a PDF where every font used is embedded, using exactly the substitute
Chuvadi's renderer would draw with (LiPi for Indic scripts; the standard-14 metrics-compatible faces for
the base fonts), subset to the glyphs used, with correct widths and ToUnicode so text stays selectable.
For example `FontEmbedder.EmbedMissing(Stream output, PdfDocument doc, FontEmbedOptions? options)`.
Vector, page content otherwise byte-for-byte.

**Who benefits.** Mac, Android and Web printing; also "Save as PDF/A-style" output and sharing PDFs to
machines without the fonts.

## L-2 — Flatten with print rules (chuvadi-pdf, `AnnotationFlattener`)

**Context.** The print PDF is flattened with `AnnotationFlattener` so the OS doesn't draw annotations its
own way. The flattener follows on-screen rules (`SkipHiddenAndNoView`).

**Gap.** Printing follows the annotation Print flag (ISO 32000-1 §12.5.3), which the library already
implements for its renderers as `AnnotationMode.Print` — but the flattener can't use it. So on Mac /
Android / Web prints: annotations without the Print flag are printed (they shouldn't be), and print-only
annotations (NoView + Print, e.g. a "COPY" stamp) are left out (they should print).
Today's Windows print path shares the same behaviour (it renders with the default on-screen mode).

**Ask.** `AnnotationFlattenOptions.Mode` (an `AnnotationMode`, default `View`), so
`Mode = AnnotationMode.Print` bakes exactly what prints — the same rule the renderers use.

**Who benefits.** Every platform's print path, Windows included when it moves to vector printing (D-22).

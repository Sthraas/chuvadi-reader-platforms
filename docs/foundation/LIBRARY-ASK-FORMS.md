# Ask for the chuvadi-pdf list: what a Fill form tool needs from Chuvadi.Pdf.Forms

**From:** the Reader's Foundation, 16 Nov 2026. **Read against:** Chuvadi.Pdf.Forms 3.32.0 (the version the Reader ships).
**Why:** Arun wants PDF form filling in the Reader before Phase 2. Today the Fill form button says "Coming soon".
The Reader will put an input over each field on the page, let the person fill it, and save. This note says what the
library gives today, what happened when it was tried, and exactly what is missing.

## 1. What 3.32.0 offers

| API | What it gives |
|---|---|
| `FormReader.GetFields(doc)` / `GetLeafFields(doc)` | The field tree, or a flat list of leaves. A `FormField` has `FullyQualifiedName`, `Type` (`Text`, `Button`, `Choice`, `Signature`, `Unknown`), `Value` (a string), `ObjectId`, `Children`, `IsLeaf` |
| `FormFiller.Fill(output, doc, IReadOnlyDictionary<string, string>)` | Sets `/V` for each named field, sets `/AcroForm /NeedAppearances true`, writes a new PDF |
| `FieldAppearanceGenerator.Generate(widget, objects, acroForm, onWarning, pageNumber)` | A normal appearance stream for one widget from its value, `/DA`, `/Q`, `/MK` and flags: text (single line, multiline, comb, password), check boxes, radio buttons, combo and list boxes, push-button captions. Null for signatures |

Nothing else about forms is public. XFA has its own packages (`XfaPackets`, `Chuvadi.Pdf.Xfa` layout); none of them fills.

## 2. What happened when it was tried

A small test form: a text field (required, `/MaxLen 20`), a check box whose on-state is `/On`, a radio group with two
buttons (`/M`, `/F`), a combo box with three options (one with an export value), a signature field, a read-only text
field. One `Fill` call per row.

| Tried | Result | Should be |
|---|---|---|
| Text = `Arun அருண்` | **Saved as `Arun ?????`.** The value is written as a single-byte string | The value kept exactly: a UTF-16BE text string (with its byte-order mark) whenever it isn't PDFDocEncoding |
| Check box = `On` | `/V` written as the string `<4F6E>`, `/AS /On` set | `/V /On` (a name) and `/AS /On` |
| Check box = `Yes` (its on-state is `On`) | `/V (Yes)` stored; no such state exists, so nothing shows as checked | Rejected, or mapped: the caller says "checked" and the library uses the field's own on-state |
| Radio group = `F` | Parent `/V` written as a string. **Neither button's `/AS` changed** (both still `/Off`) | Parent `/V /F`; the chosen button `/AS /F`, every other button in the group `/AS /Off` |
| Choice = `TVM` (an export value) | Stored | Right |
| Choice = `Mars` (not an option, not an editable combo) | Stored | Rejected and reported |
| Signature field = `x` | **A string written into `/V` of the signature field** | Refused: a signature field is never set by `Fill` |
| Read-only field | Overwritten | Refused and reported, unless the caller asks to override |
| 40 characters into `/MaxLen 20` | All 40 stored | Refused or reported |
| A name that is no field | Ignored, nothing said | Reported |
| Any fill | The whole file is rewritten (not an incremental update) | An incremental save as an option, so a signed form's signature survives |
| Any fill | No appearance streams written; only `/NeedAppearances true` | Appearances written (section 3.3) |

On screen the Reader does show the filled values (the renderer draws fields from their values). Other viewers that go
by `/AS` and `/AP` show the radio group unset and, without `/NeedAppearances` support, the text fields empty.

## 3. The ask

### 3.1 Field detail (reading)
For each field, in addition to what `FormField` has today:

| Needed | Detail |
|---|---|
| **Kind** | Text; check box; radio group; push button; combo box; list box; signature. Today a check box, a radio group and a push button are all `Button`, and combo and list are both `Choice` |
| **Widgets** | Each widget of the field: page index, rectangle (`/Rect`), and for a button its own on-state name. A field with several widgets (a radio group; a text field repeated on two pages) lists them all. Without page and rectangle the Reader cannot put an input over the field |
| **Check box on-name** | The on-state name of each check box widget (from `/AP /N`), so "checked" can be asked for without knowing it |
| **Radio buttons** | The group's buttons in order, each with its on-state name; whether the group may be all off (`NoToggleToOff`); whether same-named buttons turn on together (`RadiosInUnison`) |
| **Choice options** | The `/Opt` list in order, each with its export value and display text; multi-select; editable combo; the selected indexes (`/I`) as well as `/V` |
| **Flags** | Read-only, required, no-export; for text: multiline, password, comb, file-select, do-not-spell-check, do-not-scroll, rich text |
| **Limits and looks** | `/MaxLen`; alignment (`/Q`); the default appearance (`/DA`: font, size, colour); default value (`/DV`); tooltip (`/TU`); mapping name (`/TM`) |
| **Scripts** | Whether the field has format, keystroke, validate or calculate actions (`/AA`), and the document's calculation order (`/CO`): enough for the Reader to say "this field is calculated and is not recalculated here" |
| **Value, typed** | For a button: the state name. For a choice: the selected option or options. For text: the string, Unicode intact |

### 3.2 Setting values (writing)
1. **Unicode text kept** (Tamil, Devanagari and every other script): the value is written as a PDF text string, UTF-16BE when needed. Reading it back gives the same string.
2. **Button values are names**, not strings.
3. **A check box is set by meaning** ("on" / "off") or by its own state name; a state the widget doesn't have is refused.
4. **A radio group** sets the parent `/V` and switches `/AS` on every button of the group.
5. **A choice** is checked against its options (unless it is an editable combo), sets `/V` and `/I`, and takes several values for a multi-select list.
6. **Signature fields are refused.**
7. **Read-only, required and `/MaxLen`** are respected, with a way for the caller to override read-only on purpose.
8. **A result for every value asked for:** set; no such field; refused, and why. No silent ignores.
9. **Incremental save as an option**, so filling a signed form doesn't invalidate the signature already on it.
10. **Encrypted and permission-restricted files:** filling follows the file's "fill forms" permission, and says so when it is refused.

### 3.3 Appearances written by `Fill`
`Fill` should write each changed widget's appearance itself (it has `FieldAppearanceGenerator`), so the file looks the
same in every viewer, and then leave `/NeedAppearances` as it found it.
- **Indic and other complex-script text** is shaped and drawn with a font that has it, and that font is embedded in
  the file (the generator already reports `FontSubstituted`; the Reader would show that to the person).
- Comb, multiline, password, alignment and auto font size (`/DA` size 0) as the generator already handles for drawing.
- Check boxes and radio buttons that have no `/AP` at all get one.

### 3.4 Afterwards
- **Flatten the form**: turn the filled fields into plain page content and remove the fields (for "save a copy nobody
  can change"). `AnnotationFlattener` exists in `Chuvadi.Pdf.Operations`; the Foundation has not checked whether it
  covers form widgets. Please say.
- **Clear / reset** a field or the whole form to its default values (`/DV`).

### 3.5 XFA: please state in or out
The Reader shows a notice page for an XFA form today. Please state plainly which of these the library will support:
- **Hybrid forms** (AcroForm fields plus an XFA packet): either `Fill` keeps the XFA data in step with the fields, or
  it removes the XFA packet when it fills (as other tools do), and says which.
- **Pure XFA (dynamic) forms:** filling in or out of scope. If out, the Reader keeps its notice page and says the form
  cannot be filled here.

## 4. What the Reader will do with it
- Draw an input over each widget (text box, check box, radio button, drop-down, list) from 3.1, on the page as shown
  (the Reader already places things on turned and cropped pages).
- Keep the person's entries with the tab, show required and read-only fields as such, and refuse what the file refuses.
- Save through `Fill` (3.2, 3.3), as an incremental update when the file is signed.
- Say what was not done: calculated fields not recalculated, a font substituted, a value refused.

## 5. How to reproduce section 2
The test form is built in a few lines of raw PDF (six fields on one page). The Foundation can hand over the file and
the probe on request; they are not in the repo.

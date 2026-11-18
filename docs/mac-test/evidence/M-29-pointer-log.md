# M-29 — what the Excel sheet receives when a column edge is dragged (Mac Test, 18 Nov)

For Foundation (owner of M-29) and the Mac chat. Testing only: the app was built with
`tests/mac/patches/m29-pointer-log.patch`, which logs every pointer/mouse event reaching the sheet
into a small box the test reads through Accessibility. Nothing of this is in the product.

Runs: P29 with the log, run 44274053905 (app 0383c44d); the m29 evidence suite, run 44267686533.
Log files: `M-29-p29-log-macos-15-intel.txt`, `-macos-15.txt`, `-macos-26.txt` (P29's drag).

## Finding

**On the 15-Intel runner the mouse drag reaches the page as a touch pointer, not a mouse.**
The same drag (macOS mouse-down, 20 mouse-dragged events over 400 ms, mouse-up, posted at the HID
level like a real mouse) arrives on the Apple Silicon runners as `pointerType "mouse"` and resizes.

| Runner | pointerdown | mousedown | result |
|---|---|---|---|
| macOS 26 | `pt=mouse` | — | `finish commit=true moved=true`, column +60 px |
| macOS 15 | `pt=mouse` | — | `finish commit=true moved=true`, column +60 px |
| macOS 15-Intel | **`pt=touch`** | **none** (only a `mouseup` at the end) | no resize; pointer moves are `pt=touch` |

The press itself is right everywhere: target `.xv-colhdr` column 1, 1 px inside its right edge
(`dFar=-1.0`), `unz=true` on macOS 15 (older WebKit, rects corrected), screen edge at x 718.
So the aim is good and `edgeAt` finds the edge; what differs is the pointer type.

Intel, P29's drag (from `M-29-p29-log-macos-15-intel.txt`):

```
M29 4 doc pointerdown pt=touch b=0 bs=1 x=307.0 y=49.0 ... t=xv-colhdr trusted=true hdr=1 sr=244.0..308.0 dFar=-1.0 ...
M29 5 el pointerdown pt=touch ...
M29 6 finish commit=false moved=false col=true idx=1
M29 7 doc pointermove pt=touch b=-1 bs=1 x=310.0 ...
...
M29 11 doc pointermove pt=touch b=-1 bs=1 x=343.0 ...
M29 12 doc mouseup pt=- b=0 bs=0 x=367.0 ...
M29 13 doc pointerup pt=touch b=0 bs=0 x=367.0 ...
```

macOS 26, same drag:

```
M29 2 doc pointerdown pt=mouse b=0 bs=1 x=307.0 y=49.0 ... dFar=-1.0 dNear=63.0 unz=false ...
M29 7 doc pointerup pt=mouse ... t=xv-gridwrap xv-resizing
M29 9 finish commit=true moved=true col=true idx=1
```

Since patch 33 (D-193) a touch pointer must rest 350 ms on the edge before it takes it, and a touch
that moves more than 8 px first is treated as scrolling. A mouse drag that arrives as touch therefore
never resizes unless the user holds still first. (M-29 also failed before patch 33, when touch took
the edge at once, so the hold may not be the whole story; this is the first failure we have logged, and in it
the pointer type is touch.)
`finish commit=false` at line 6 is a stale drag being dropped by the "second finger" branch.

Also seen on every runner: an Accessibility press (`press "File's own sizes"`) arrives as
`pointerdown pt=touch` followed by `mousedown`/`mouseup`.

## Why it is intermittent

In the m29 suite (same app, same drag, but several seconds later and after more Accessibility reads)
all 45 drags on all three runners resized, Intel included. So whether Mac Catalyst hands WebKit the
mouse as a mouse or as a touch is not fixed per machine. We have not found what decides it.

## Likely cause (to confirm, not proven)

Mac Catalyst delivers mouse clicks to UIKit as touches unless the app opts in to indirect input
events. The Mac Info.plist has no `UIApplicationSupportsIndirectInputEvents` key. With it set to
YES, UIKit reports mouse and trackpad clicks as `UITouch.TouchType.indirectPointer`, and WKWebView is
expected to report them as `pointerType "mouse"`. This would be a one-line Mac change; it must be
checked for side effects (other UIKit gesture recognisers, M-08/M-23 key handling, the M-27 marks).

## Options

1. **Mac: add `UIApplicationSupportsIndirectInputEvents = YES`**, then re-run P29 with the log.
   Pro: fixes the cause if confirmed; also makes every other mouse path in the page (marks, text
   selection, drag) behave as a mouse. Con: needs a regression pass on all mouse work.
2. **Foundation: in `gridResize`, treat a touch pointer on a Mac (no touch screen) as a mouse.**
   Pro: small, contained. Con: works around the symptom only for this one control.
3. Both. **Recommendation: 1 first** (one line, root cause); 2 only if 1 does not change the type.

Whoever takes it, I re-verify with P29 and the m29 suite on all three runners.

## Addendum, 18 Nov evening — fix 5a500ec2 (patch 34) is not enough; the real mechanism

Run 44341567745: P29 with logging patch v2 on platform/mac 57400e56 (patch 34). Resize passes on macOS 15 and 26,
**still fails on 15-Intel**. Log: `M-29-p29-log-57400e56-macos-15-intel.txt`.

On 15-Intel **one mouse press produces two pointers**: first a `mouse` pointer goes down, then, at the same spot,
a `touch` pointer goes down too. All the moves then come on the **touch** pointer; the button release comes on both.

```
M29 2 doc pointerdown pt=mouse  x=307 t=xv-colhdr hdr=1 dFar=-1.0 ... edge=c1     ← mouse pointer takes the edge (st.drag, id = mouse)
M29 4 doc pointerdown pt=touch  x=307 t=xv-colhdr hdr=1 dFar=-1.0 ...             ← same press, second pointer: ignored (st.drag set)
M29 6 doc pointermove pt=touch  x=322 …                                            ← moves arrive on the touch pointer
M29 7 doc pointermove pt=touch  x=355 …                                               gridResize: e.pointerId !== d.id → ignored
M29 9 doc pointerup   pt=touch  x=367 …
M29 12 doc pointerup  pt=mouse  x=367 t=xv-gridwrap xv-resizing
M29 14 finish commit=true moved=false col=true idx=1                               ← drag ends with no movement seen
```

So `touchCapable=false` (5a500ec2) makes the touch pointer count as a mouse, but the drag belongs to the mouse
pointer's id and every move comes from the touch pointer's id, which `pointermove` discards. Before patch 34 the same
pair explains the earlier log: the touch pointerdown hit the "second finger = pinch" branch and dropped the drag
(`finish commit=false`).

### Options for Foundation
1. **Where `touchCapable` is false, follow moves and the release from any pointer while a drag is held** (a Mac has
   one pointing device; skip the `pointerId` check, or adopt the touch pointer's id when it goes down on the same
   spot within a few ms). Pro: small, inside `gridResize`, matches what the log shows. Con: none seen for a
   no-touch host.
2. Ignore pointers of type `touch` entirely where `touchCapable` is false. Con: on 15-Intel the moves come *only*
   as touch, so the drag would still see no movement — does not work.
3. Mac: `UIApplicationSupportsIndirectInputEvents = YES` so Catalyst stops sending the touch twin. Pro: root cause
   for every control in the page. Con: unproven; needs a regression pass.

**Recommendation: 1 now** (it is what the log asks for), and 3 as a separate Mac trial, since every other
drag in the page (marks, selection) could meet the same twin pointer on Intel.

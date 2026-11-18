# Parse-process prototype — Ubuntu 24.04.5 LTS, X64, 2 cores, .NET 10.0.14
engine: heap cap 512 MB (DOTNET_GCHeapHardLimit), time limit 10 s per request

## Stack sizes
app process: main 8160 KB, thread pool 8192 KB, new Thread() 8192 KB
engine process: main 8152 KB, thread pool 8192 KB, new Thread() 8192 KB

## 1. Starting the engine (process start to first answer)
first 53.8 ms; then median 40.3 ms (min 32.5, max 44.4); engine memory idle 27 MB
first document, open and page 1 (doc-12p.pdf): today, in a running app 127.4 ms; with an engine started for it (start included) 151.1 ms; with an engine already running, see table 2
wire, a payload sent and returned (twice the one-way cost): 1 KB 0.1 ms, 100 KB 0.5 ms, 1000 KB 3.1 ms, 6000 KB 23.2 ms

## 2. PDF pages (open, then the first 8 pages), warm: one file drawn first on both sides
| file | pages | SVG KB/page | open in-process | open engine | page in-process (median) | page engine (median) | overhead/page |
|---|---|---|---|---|---|---|---|
| doc-12p.pdf | 12 | 34 | 0.8 ms | 1.8 ms | 9.2 ms | 8.0 ms | -1.2 ms |
| lm-info.pdf | 26 | 333 | 1.5 ms | 1.8 ms | 136.3 ms | 113.0 ms | -23.4 ms |
| qhv-test.pdf | 1 | 250 | 0.5 ms | 0.7 ms | 79.5 ms | 83.4 ms | 3.9 ms |
| qpl-info.pdf | 40 | 738 | 9.8 ms | 20.9 ms | 467.4 ms | 462.1 ms | -5.2 ms |
| qtm-info.pdf | 33 | 661 | 1.6 ms | 1.8 ms | 270.0 ms | 263.7 ms | -6.2 ms |
engine memory after drawing: 140 MB

## 3. Word and Excel (load in-process, against load in the engine plus the model sent back as JSON)
| file | in-process | engine | JSON KB |
|---|---|---|---|
| discharge.docx | 30.6 ms | 83.5 ms | 9 |
| long-2000p.docx | 87.8 ms | 90.1 ms | 1056 |
| layout.xlsx | 1.0 ms | 3.0 ms | 20 |
| rows-20000.xlsx | failed: EngineFailed: OutOfMemoryException: Exception of type 'System.OutOfMemoryException' was thrown. | | |

## 4. Failure: the engine dies or runs away; the app carries on
- stack overflow (uncatchable): engine ended (exit code 134), noticed after 14.6 ms; new engine, file reopened and page 1 drawn again in 192.1 ms (35 KB). App still running: yes.
- endless loop: engine passed its time limit (10 s) and was ended, noticed after 10021.6 ms; new engine, file reopened and page 1 drawn again in 155.8 ms (35 KB). App still running: yes.
- allocates without end: engine refused and stayed up: OutOfMemoryException: Exception of type 'System.OutOfMemoryException' was thrown., noticed after 321.1 ms; new engine, file reopened and page 1 drawn again in 156.0 ms (35 KB). App still running: yes.

## 5. Probe files (each in its own engine; the app must stay up)
- deep-page-tree.pdf: refused: PdfCorruptionException: Page tree depth exceeds maximum (1024); document may contain a cyclic /Kids reference. after 211.8 ms. App still running: yes.
- form-draws-itself.pdf: drew all 1 pages after 118.2 ms. App still running: yes.
- function-cycle.pdf: drew all 1 pages after 147.9 ms. App still running: yes.
- nested-array-in-catalog.pdf: refused: PdfParseException: Object 1 0: A value is nested 200001 levels deep; the limit is 512 levels. Every array, dictionary and value counts as a level, the object's own value included (offset 562). after 208.2 ms. App still running: yes.
- bomb-flate-560MB.pdf: refused: OutOfMemoryException: Exception of type 'System.OutOfMemoryException' was thrown. after 1093.9 ms. App still running: yes.

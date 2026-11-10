#!/usr/bin/env python3
"""Test-only trace markers for the cold Open-with timeline (never shipped). Inserts
`Console.WriteLine("ATT …")` lines (→ logcat tag DOTNET, timestamped by logcat -v epoch) into the
composed source tree, at: Android activity create, MAUI builder, intent delivery, the open request,
the library open (start/end) and each page render (start/end).

    trace-patch.py <reader-checkout>
"""
import os
import sys

ROOT = sys.argv[1]
W = 'System.Console.WriteLine("ATT {0} " + System.Diagnostics.Stopwatch.GetTimestamp());'


def patch(rel, anchor, insert, before=True, count=1):
    p = os.path.join(ROOT, rel)
    s = open(p, encoding="utf-8").read()
    n = s.count(anchor)
    if n < 1:
        print(f"MISSING  {rel}: {anchor[:60]!r}")
        return False
    if before:
        s = s.replace(anchor, insert + anchor, count)
    else:
        s = s.replace(anchor, anchor + insert, count)
    open(p, "w", encoding="utf-8").write(s)
    print(f"patched  {rel}: {insert.strip()[:70]}")
    return True


A = "src/ChuvadiReader.Android"
patch(f"{A}/Platforms/Android/MainActivity.cs", "        base.OnCreate(savedInstanceState);",
      "        " + W.format("activity-oncreate") + "\n")
patch(f"{A}/Platforms/Android/MainActivity.cs", "        base.OnCreate(savedInstanceState);",
      "\n        " + W.format("activity-base-oncreate-done"), before=False)
patch(f"{A}/Platforms/Android/MainActivity.cs", "    private static void Deliver(Intent? intent)\n    {",
      "\n        " + W.format("deliver-intent"), before=False)
patch(f"{A}/MauiProgram.cs", "        var builder = MauiApp.CreateBuilder();", "        " + W.format("maui-createbuilder") + "\n")
patch(f"{A}/MauiProgram.cs", "        return builder.Build();", "        " + W.format("maui-build") + "\n")
C = "src/ChuvadiReader.Core/Reader/ChuvadiPdfReader.cs"
patch(C, "        var document = string.IsNullOrEmpty(password)", "        " + W.format("pdf-open-start") + "\n")
patch(C, "        var vm = new PdfDocumentVm", "        " + W.format("pdf-open-end") + "\n")
patch(C, "        var svg = RenderPage(document, renderer, overrides, pageNumber, cancellationToken, png => token = KeepImage(png));",
      "        System.Console.WriteLine(\"ATT render-start-p\" + pageNumber + \" \" + System.Diagnostics.Stopwatch.GetTimestamp());\n")
patch(C, "        var svg = RenderPage(document, renderer, overrides, pageNumber, cancellationToken, png => token = KeepImage(png));",
      "\n        System.Console.WriteLine(\"ATT render-end-p\" + pageNumber + \" len=\" + svg.Length + \" \" + System.Diagnostics.Stopwatch.GetTimestamp());",
      before=False)
T = "src/ChuvadiReader.Core/Reader/TabsService.cs"
patch(T, "    public async Task<ReaderTab> OpenAsync(string path, string fileName, DocumentFormat format, CancellationToken ct = default)\n    {",
      "\n        " + W.format("tabs-open"), before=False)

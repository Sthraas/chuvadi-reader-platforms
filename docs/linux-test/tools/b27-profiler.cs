// Test-only profiler for B-27. Prints numbers only — never any content of the file.
using System.Diagnostics;
using Chuvadi.Pdf.Documents; using Chuvadi.Pdf.Graphics; using Chuvadi.Pdf.Images; using Chuvadi.Pdf.Rendering;
using ChuvadiReader.Core.Reader; using ChuvadiReader.Core.Documents;
var path = args[0];
if (args.Length > 1 && args[1] == "raster-only") { var d = PdfDocument.OpenAsync(path).GetAwaiter().GetResult(); var r = new PageRasterizer(d.Objects, new RenderOptions { Dpi = 18 }); for (int k = 0; k < 2; k++) r.Rasterize(d.Pages[0]); var buf2 = new PageRasterizer(d.Objects, new RenderOptions { Dpi = 150, Background = ColorF.White, AntiAlias = true }).Rasterize(d.Pages[0]); using var ms2 = new MemoryStream(); PngEncoder.Encode(new ImageFrame(buf2, ImageColorFormat.Rgba32), ms2, false); return; }
long MB(long b) => b / (1024 * 1024);
long Retained() { GC.Collect(); GC.WaitForPendingFinalizers(); GC.Collect(); return GC.GetTotalMemory(true); }
void Stage(string name, Action a) {
    var a0 = GC.GetTotalAllocatedBytes(true); var sw = Stopwatch.StartNew(); a(); sw.Stop();
    var alloc = GC.GetTotalAllocatedBytes(true) - a0;
    Console.WriteLine($"{name,-44} {sw.ElapsedMilliseconds,7} ms  alloc {MB(alloc),6} MB  retained {MB(Retained()),6} MB  WS {MB(Environment.WorkingSet),6} MB");
}
Console.WriteLine($"file {new FileInfo(path).Length} bytes; baseline retained {MB(Retained())} MB");
PdfDocument? raw = null;
Stage("1 library open (PdfDocument.OpenAsync)", () => raw = PdfDocument.OpenAsync(path).GetAwaiter().GetResult());
Console.WriteLine($"   pages {raw!.Pages.Count}, page1 {raw.Pages[0].Width}x{raw.Pages[0].Height} pt");
Stage("1b first touch of page 1 content (Rasterize 18 dpi)", () => new PageRasterizer(raw.Objects, new RenderOptions { Dpi = 18 }).Rasterize(raw.Pages[0]));
PixelBuffer? buf = null; byte[]? png = null; string? b64 = null;
Stage("2a rasterize page 1 @150 dpi", () => buf = new PageRasterizer(raw.Objects, new RenderOptions { Dpi = 150, Background = ColorF.White, AntiAlias = true }).Rasterize(raw.Pages[0]));
Stage("2b PNG encode page 1", () => { using var ms = new MemoryStream(); PngEncoder.Encode(new ImageFrame(buf!, ImageColorFormat.Rgba32), ms, false); png = ms.ToArray(); });
Stage("2c base64 + SVG wrapper string", () => b64 = "data:image/png;base64," + Convert.ToBase64String(png!));
Console.WriteLine($"   raster {buf!.Width}x{buf.Height} px = {MB((long)buf.Width*buf.Height*4)} MB RGBA; PNG {MB(png!.Length)} MB; data-URI string {b64!.Length/1048576} M chars = {MB((long)b64.Length*2)} MB as .NET string");
buf = null; png = null; b64 = null;
raw = null;
Stage("3 FlattenService.Probe (the extra open, B-24)", () => new FlattenService().Probe(path));
IPdfSession? s = null;
Stage("4 Reader open (ChuvadiPdfReader.OpenAsync)", () => s = new ChuvadiPdfReader().OpenAsync(path, "x.pdf").GetAwaiter().GetResult());
long cacheChars = 0;
for (int i = 0; i < 5; i++) {
    string svg = "";
    Stage($"5.{i+1} session.RenderPageSvgAsync page {i+1} (cached)", () => svg = s!.RenderPageSvgAsync(i).GetAwaiter().GetResult());
    cacheChars += svg.Length;
    Console.WriteLine($"   page {i+1}: svg {svg.Length/1048576.0:F1} M chars; cache now ~{MB(cacheChars*2)} MB of strings");
}
Stage("6 DropRenderCache", () => ((ChuvadiPdfSession)s!).DropRenderCache());

using System.Collections.Concurrent;
using System.Globalization;
using Chuvadi.Pdf.Documents;
using Chuvadi.Print;
using Chuvadi.Print.Ipp;
using ChuvadiReader.Core.Reader;
using CorePrintResult = ChuvadiReader.Core.Reader.PrintResult;

namespace ChuvadiReader.Linux.Platform;

/// <summary>
/// Printing on Linux (coordinator D-06, Arun's vector rule): the PDF itself goes to a CUPS queue,
/// whose own filters lay it out for the printer. Nothing is rendered to images here.
///
/// Flow, as on Windows: the app's Print card (pages, copies, fit) → the desktop's print dialog
/// (printer, copies, pages, two-sided, paper, printer options), preset from the card → the job is
/// sent over IPP with Chuvadi.Print.Ipp (<see cref="IppDocumentTarget"/>: the PDF as-is, settings as
/// IPP job attributes).
///
/// Not here yet (library): the raster fallback needs Chuvadi.Print.Pdf.Raster, which isn't released;
/// CUPS queues accept PDF and convert it themselves, so every local queue prints without it.
/// </summary>
public sealed class CupsPrintService : IPrintService
{
    private static readonly ConcurrentDictionary<int, TaskCompletionSource<Dictionary<string, string>?>> Pending = new();
    private static int _nextToken;

    static CupsPrintService()
    {
        GtkHost.PrintResult += (token, lines) =>
        {
            if (Pending.TryRemove(token, out var tcs))
            {
                tcs.TrySetResult(lines.Length == 0 ? null : Parse(lines));
            }
        };
    }

    private static readonly CorePrintResult Cancelled = new(PrintOutcome.Cancelled, 0, "Printing cancelled");

    /// <summary>True when a CUPS server runs on this machine (its socket exists). No network call.</summary>
    public bool IsAvailable =>
        File.Exists("/run/cups/cups.sock") || File.Exists("/var/run/cups/cups.sock") ||
        Directory.Exists("/etc/cups");

    public async Task<CorePrintResult> PrintAsync(string pdfPath, PrintRequest request, CancellationToken ct = default)
    {
        byte[] pdf;
        int pageCount;
        bool allowPrint;
        try
        {
            (pdf, pageCount, allowPrint) = await Task.Run(() => Load(pdfPath, request.Password), ct);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or InvalidOperationException or FormatException)
        {
            return new CorePrintResult(PrintOutcome.Failed, 0, "Couldn't read the document: " + ex.Message);
        }

        // The file's own permissions say "no printing" (D-66, L-8): refuse before any dialog opens.
        if (!allowPrint)
        {
            return new CorePrintResult(PrintOutcome.Failed, 0, NotAllowedMessage);
        }

        if (!PageRangeParser.TryParse(request.PageRange, pageCount, request.CurrentPage, out var pages, out var rangeError))
        {
            return new CorePrintResult(PrintOutcome.Failed, 0, rangeError);
        }

        var title = request.JobName ?? Path.GetFileName(pdfPath);
        var answer = await ShowDialog(title, pageCount, request, pages, ct);
        if (answer is null)
        {
            return Cancelled;
        }

        return await Task.Run(() => Submit(pdf, pageCount, title, request, answer, ct), ct);
    }

    /// <summary>Shown when a file's permissions forbid printing.</summary>
    internal const string NotAllowedMessage = "This file's permissions don't allow printing.";

    /// <summary>The PDF bytes to send, the page count, and whether the file's permissions allow
    /// printing (a file without encryption always does). A file with an open password is sent
    /// decrypted (CUPS can't open it), made in memory with the same library calls Core uses; nothing
    /// is decrypted when printing isn't allowed.</summary>
    private static (byte[] Pdf, int PageCount, bool AllowPrint) Load(string path, string? password)
    {
        if (string.IsNullOrEmpty(password))
        {
            using var doc = PdfDocument.Open(path);
            if (doc.Encryption is { AllowPrint: false })
            {
                return ([], doc.PageCount, false);
            }

            return (File.ReadAllBytes(path), doc.PageCount, true);
        }

        using var protectedDoc = PdfDocument.Open(path, password);
        if (protectedDoc.Encryption is { AllowPrint: false })
        {
            return ([], protectedDoc.PageCount, false);
        }

        using var ms = new MemoryStream();
        protectedDoc.Save(ms, null);
        return (ms.ToArray(), protectedDoc.PageCount, true);
    }

    private static Task<Dictionary<string, string>?> ShowDialog(
        string title, int pageCount, PrintRequest request, IReadOnlyList<int> pages, CancellationToken ct)
    {
        var token = Interlocked.Increment(ref _nextToken);
        var tcs = new TaskCompletionSource<Dictionary<string, string>?>(TaskCreationOptions.RunContinuationsAsynchronously);
        Pending[token] = tcs;
        if (ct.CanBeCanceled)
        {
            ct.Register(() =>
            {
                if (Pending.TryRemove(token, out var t))
                {
                    t.TrySetCanceled(ct);
                }
            });
        }

        var preset = IsAll(request.PageRange) ? string.Empty
            : string.Equals(request.PageRange?.Trim(), "current", StringComparison.OrdinalIgnoreCase) ? "current"
            : ZeroBasedRanges(pages);
        var copies = request.Copies ?? 1;
        var current = Math.Clamp(request.CurrentPage, 0, Math.Max(0, pageCount - 1));
        GtkHost.Post(() => Native.PrintDialog(token, "Print " + title, pageCount, current, preset, copies));
        return tcs.Task;
    }

    private static CorePrintResult Submit(byte[] pdf, int pageCount, string title, PrintRequest request,
        Dictionary<string, string> answer, CancellationToken ct)
    {
        var printer = answer.GetValueOrDefault("printer") ?? string.Empty;
        string? uri;
        try
        {
            uri = CupsQueues.List(cancellationToken: ct)
                .FirstOrDefault(q => string.Equals(q.Name, printer, StringComparison.Ordinal))?.Uri;
        }
        catch (Exception ex) when (ex is IppException or IOException or System.Net.Http.HttpRequestException or TimeoutException)
        {
            return new CorePrintResult(PrintOutcome.Failed, 0, "Couldn't reach the print service (CUPS): " + ex.Message);
        }

        if (uri is null)
        {
            return new CorePrintResult(PrintOutcome.Failed, 0,
                $"\"{printer}\" isn't set up as a printer on this computer yet. Add it in Settings › Printers, then print again.");
        }

        var selection = Selection(answer.GetValueOrDefault("pages"), pageCount, out var pagesSent);
        var job = new PrintJob(pdf)
            .WithTitle(title)
            .WithPages(selection)
            .WithCopies(Int(answer, "copies", 1), Int(answer, "collate", 1) == 1)
            .WithDuplex(answer.GetValueOrDefault("duplex") switch
            {
                // GTK's names follow the binding edge in portrait: horizontal = flip on the long edge.
                "horizontal" => Duplex.Vertical,
                "vertical" => Duplex.Horizontal,
                _ => Duplex.Simplex,
            })
            .WithOrientation(answer.GetValueOrDefault("orientation") switch
            {
                "landscape" => PageOrientation.Landscape,
                "reverse-landscape" => PageOrientation.ReverseLandscape,
                "reverse-portrait" => PageOrientation.ReversePortrait,
                _ => PageOrientation.Portrait,
            })
            .WithScale(request.FitToPage ? ScaleMode.FitToPage : ScaleMode.ActualSize);

        if (Paper(answer.GetValueOrDefault("paper")) is { } paper)
        {
            job.WithPaper(paper);
        }

        // The job ticket: the library maps the settings (Chuvadi.Print.Ipp's IppJobTicket, as IppDocumentTarget
        // does), the dialog's CUPS options follow.
        var extra = new List<IppAttribute>();
        // Settings GTK's own CUPS printing passes as CUPS job attributes.
        if (answer.GetValueOrDefault("page-set") is "even" or "odd")
        {
            extra.Add(new IppAttribute("page-set", IppValue.Keyword(answer["page-set"])));
        }

        if (Int(answer, "reverse", 0) == 1)
        {
            extra.Add(new IppAttribute("outputorder", IppValue.Keyword("reverse")));
        }

        var up = Int(answer, "number-up", 1);
        if (up > 1)
        {
            extra.Add(new IppAttribute("number-up", IppValue.Integer(up)));
        }

        // The queue's options and the Job tab, as CUPS takes them (option name = attribute name).
        foreach (var (key, value) in answer)
        {
            if (key.StartsWith("opt:", StringComparison.Ordinal) && QueueOption(key[4..], value) is { } attribute)
            {
                extra.Add(attribute);
            }
        }

        try
        {
            using var client = new IppClient(uri);
            var capabilities = new IppPrinterCapabilities(
                client.GetPrinterAttributes(null, ct).Group(IppTag.PrinterAttributes) ?? new IppAttributeGroup(IppTag.PrinterAttributes));
            var ticket = IppJobTicket.Build(job.Settings, capabilities, new IppJobOptions(), documentMode: true,
                printerMakesCopies: true, pageCount, null, new List<string>());
            if (!OrientationChosen(answer))
            {
                // B-14: orientation left at the dialog's default. Without orientation-requested CUPS turns each
                // page to fit the sheet (a landscape page fills a portrait sheet); with "portrait" it shrinks
                // landscape pages to half size. The library always sends it, so the host removes it here.
                ticket.Remove("orientation-requested");
            }

            foreach (var attribute in extra)
            {
                ticket.Add(attribute);
            }

            using var document = new MemoryStream(pdf, writable: false);
            client.PrintJob(document, "application/pdf", ticket, title, ct);
        }
        catch (OperationCanceledException)
        {
            return Cancelled;
        }
        catch (Exception ex) when (ex is IppException or IOException or NotSupportedException or InvalidOperationException
                                       or System.Net.Http.HttpRequestException or TimeoutException)
        {
            return new CorePrintResult(PrintOutcome.Failed, 0, "The printer didn't take the job: " + ex.Message);
        }

        // Same wording as the Windows host.
        return new CorePrintResult(PrintOutcome.Printed, pagesSent,
            pagesSent == 1 ? "Sent 1 page to the printer" : $"Sent {pagesSent} pages to the printer");
    }

    /// <summary>True when the dialog's orientation is a choice (landscape or a reverse); portrait is GTK's
    /// default, so it means "as the document is".</summary>
    internal static bool OrientationChosen(IReadOnlyDictionary<string, string> answer) =>
        answer.GetValueOrDefault("orientation") is "landscape" or "reverse-landscape" or "reverse-portrait";

    private static readonly HashSet<string> HoldKeywords = new(StringComparer.Ordinal)
    {
        "no-hold", "indefinite", "day-time", "evening", "night", "second-shift", "third-shift", "weekend",
    };

    /// <summary>
    /// One option from the dialog as an IPP job attribute. Upper-case names are the printer's own (PPD)
    /// options; CUPS applies them by name. Lower-case names are IPP job attributes from the Job tab.
    /// Options already sent another way (pages, paper, two-sided, pages per sheet) are skipped.
    /// </summary>
    private static IppAttribute? QueueOption(string name, string value)
    {
        if (char.IsUpper(name[0]))
        {
            return name is "PageSize" or "PageRegion" or "Duplex"
                ? null
                : new IppAttribute(name, IppValue.Keyword(value));
        }

        switch (name)
        {
            case "job-priority" when int.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out var priority)
                                     && priority is >= 1 and <= 100:
                return new IppAttribute(name, IppValue.Integer(priority));
            case "job-sheets":
                // "start,end" banner pages, e.g. "standard,none".
                return new IppAttribute(name, value.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                    .Select(IppValue.Name));
            case "job-hold-until":
                // A keyword (indefinite, night…) or a time "HH:MM:SS" in UTC, which CUPS takes as a name.
                return new IppAttribute(name, HoldKeywords.Contains(value) ? IppValue.Keyword(value) : IppValue.Name(value));
            case "job-billing":
                return new IppAttribute(name, IppValue.Name(value));
            case "number-up-layout":
                return new IppAttribute(name, IppValue.Keyword(value));
            default:
                return null; // pages, copies, paper, sides, page-set, order and number-up are already mapped
        }
    }

    /// <summary>The dialog's page choice. GTK ranges are 0-based and inclusive.</summary>
    private static PageSelection Selection(string? pages, int pageCount, out int count)
    {
        if (pages is not null && pages.StartsWith("current:", StringComparison.Ordinal)
            && int.TryParse(pages.AsSpan(8), NumberStyles.None, CultureInfo.InvariantCulture, out var current))
        {
            count = 1;
            return PageSelection.Current(Math.Clamp(current, 0, pageCount - 1) + 1);
        }

        if (pages is not null && pages.StartsWith("ranges:", StringComparison.Ordinal))
        {
            var list = new SortedSet<int>();
            foreach (var part in pages[7..].Split(',', StringSplitOptions.RemoveEmptyEntries))
            {
                var ab = part.Split('-');
                if (ab.Length == 2
                    && int.TryParse(ab[0], NumberStyles.None, CultureInfo.InvariantCulture, out var a)
                    && int.TryParse(ab[1], NumberStyles.None, CultureInfo.InvariantCulture, out var b))
                {
                    for (var p = Math.Max(0, a); p <= Math.Min(b, pageCount - 1); p++)
                    {
                        list.Add(p + 1);
                    }
                }
            }

            if (list.Count > 0)
            {
                count = list.Count;
                return PageSelection.Explicit(list.ToArray());
            }
        }

        count = pageCount;
        return PageSelection.All;
    }

    /// <summary>"iso_a4;595.276;841.890" → the dialog's paper size, in points.</summary>
    private static PaperSize? Paper(string? text)
    {
        var parts = text?.Split(';');
        if (parts is not { Length: 3 }
            || !double.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out var w)
            || !double.TryParse(parts[2], NumberStyles.Float, CultureInfo.InvariantCulture, out var h)
            || w <= 0 || h <= 0)
        {
            return null;
        }

        return new PaperSize(w, h, parts[0]);
    }

    private static bool IsAll(string? range)
    {
        var t = range?.Trim() ?? string.Empty;
        return t.Length == 0 || t.Equals("all", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>Zero-based pages → "0-2,4" for the dialog (IPP and GTK take ascending ranges).</summary>
    private static string ZeroBasedRanges(IReadOnlyList<int> pages)
    {
        var sorted = pages.Distinct().Order().ToArray();
        var parts = new List<string>();
        for (var i = 0; i < sorted.Length;)
        {
            var j = i;
            while (j + 1 < sorted.Length && sorted[j + 1] == sorted[j] + 1)
            {
                j++;
            }

            parts.Add(string.Create(CultureInfo.InvariantCulture, $"{sorted[i]}-{sorted[j]}"));
            i = j + 1;
        }

        return string.Join(',', parts);
    }

    private static int Int(Dictionary<string, string> d, string key, int fallback) =>
        d.TryGetValue(key, out var v) && int.TryParse(v, NumberStyles.Integer, CultureInfo.InvariantCulture, out var n) ? n : fallback;

    private static Dictionary<string, string> Parse(string[] lines)
    {
        var d = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var line in lines)
        {
            var eq = line.IndexOf('=');
            if (eq > 0)
            {
                d[line[..eq]] = line[(eq + 1)..];
            }
        }

        return d;
    }
}

using Chuvadi.Pdf.Documents;
using Chuvadi.Pdf.Operations;
using Chuvadi.Pdf.Primitives;
using ChuvadiReader.Core.Reader;
using ChuvadiReader.Platform;
using global::Android.Content;
using global::Android.OS;
using global::Android.Print;
using JavaFile = Java.IO.FileOutputStream;

namespace ChuvadiReader.Android.Platform;

/// <summary>
/// Printing through Android's print framework (decision A-04 / Foundation F-4): the system print
/// dialog, every printer the device knows (Mopria, vendor print services, Save as PDF), and the PDF
/// handed over as-is — vector, no rasteriser, no network permission for the app.
///
/// The PDF goes unchanged when the whole document is printed. When the Print card asks for a page
/// range, or the file needs a password, chuvadi-pdf assembles just those pages into a new, unlocked
/// PDF (<see cref="PageOperations.Assemble"/>) in the app's working folder, and that is printed;
/// it is deleted when the print job is handed off. Copies, paper and scaling are chosen in the system
/// dialog (Android has no way to preselect them).
/// </summary>
public sealed class AndroidPrintService : IPrintService
{
    private readonly IAppPaths _paths;

    public AndroidPrintService(IAppPaths paths) => _paths = paths;

    public bool IsAvailable => true;

    public async Task<PrintResult> PrintAsync(string pdfPath, PrintRequest request, CancellationToken ct = default)
    {
        string? temp = null;
        try
        {
            var jobName = string.IsNullOrWhiteSpace(request.JobName) ? Path.GetFileName(pdfPath) : request.JobName!;
            var (printPath, pageCount, isTemp) = await PreparePdfAsync(pdfPath, request, ct).ConfigureAwait(false);
            temp = isTemp ? printPath : null;

            var finished = await MainThread.InvokeOnMainThreadAsync(() => StartJob(jobName, printPath, pageCount)).ConfigureAwait(false);
            return finished switch
            {
                PrintOutcome.Printed => new PrintResult(PrintOutcome.Printed, pageCount, $"Sent {pageCount} page{(pageCount == 1 ? "" : "s")} to the printer."),
                PrintOutcome.Cancelled => new PrintResult(PrintOutcome.Cancelled, 0),
                _ => new PrintResult(PrintOutcome.Failed, 0, "The print job failed."),
            };
        }
        catch (PdfPasswordRequiredException)
        {
            return new PrintResult(PrintOutcome.Failed, 0, "This file needs its password to print.");
        }
        catch (FormatException ex)
        {
            return new PrintResult(PrintOutcome.Failed, 0, ex.Message);
        }
        catch (System.OperationCanceledException)
        {
            return new PrintResult(PrintOutcome.Cancelled, 0);
        }
        finally
        {
            if (temp is not null)
            {
                TryDelete(Path.GetDirectoryName(temp)!);
            }
        }
    }

    /// <summary>Returns the PDF to print: the original, or the selected/unlocked pages as a new file.</summary>
    private async Task<(string Path, int PageCount, bool IsTemp)> PreparePdfAsync(string pdfPath, PrintRequest request, CancellationToken ct)
    {
        using var doc = string.IsNullOrEmpty(request.Password)
            ? await PdfDocument.OpenAsync(pdfPath, ct).ConfigureAwait(false)
            : await PdfDocument.OpenAsync(pdfPath, request.Password!, ct).ConfigureAwait(false);

        if (!PageRangeParser.TryParse(request.PageRange, doc.PageCount, request.CurrentPage, out var pages, out var error))
        {
            throw new FormatException(error ?? "Those pages can't be printed.");
        }

        var whole = pages.Count == doc.PageCount && pages.Select((p, i) => p == i).All(same => same);
        if (whole && string.IsNullOrEmpty(request.Password))
        {
            return (pdfPath, doc.PageCount, false);
        }

        var folder = Path.Combine(_paths.WorkingFolder, "print", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        var target = Path.Combine(folder, Path.GetFileName(pdfPath));
        await Task.Run(() =>
        {
            using var output = File.Create(target);
            PageOperations.Assemble(output, pages.Select(p => new PageSelector(doc, p)).ToList());
        }, ct).ConfigureAwait(false);
        return (target, pages.Count, true);
    }

    private static Task<PrintOutcome> StartJob(string jobName, string printPath, int pageCount)
    {
        var activity = Microsoft.Maui.ApplicationModel.Platform.CurrentActivity
            ?? throw new InvalidOperationException("The app isn't on screen.");
        var manager = (PrintManager?)activity.GetSystemService(Context.PrintService)
            ?? throw new InvalidOperationException("This device has no print service.");

        var adapter = new PdfFileAdapter(jobName, printPath, pageCount);
        var job = manager.Print(jobName, adapter, new PrintAttributes.Builder().Build());
        adapter.Job = job;
        return adapter.Finished;
    }

    private static void TryDelete(string folder)
    {
        try
        {
            Directory.Delete(folder, recursive: true);
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }

    /// <summary>Feeds one finished PDF file to the print framework.</summary>
    private sealed class PdfFileAdapter(string jobName, string path, int pageCount) : PrintDocumentAdapter
    {
        private readonly TaskCompletionSource<PrintOutcome> _finished = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private bool _wrote;

        public PrintJob? Job { get; set; }

        public Task<PrintOutcome> Finished => _finished.Task;

        public override void OnLayout(PrintAttributes? oldAttributes, PrintAttributes? newAttributes, CancellationSignal? cancellationSignal, LayoutResultCallback? callback, Bundle? extras)
        {
            if (cancellationSignal?.IsCanceled == true)
            {
                callback?.OnLayoutCancelled();
                return;
            }

            var info = new PrintDocumentInfo.Builder(jobName)
                .SetContentType(PrintContentType.Document)!
                .SetPageCount(pageCount)!
                .Build();
            callback?.OnLayoutFinished(info, !Equals(oldAttributes, newAttributes));
        }

        public override void OnWrite(PageRange[]? pages, ParcelFileDescriptor? destination, CancellationSignal? cancellationSignal, WriteResultCallback? callback)
        {
            try
            {
                if (destination?.FileDescriptor is null)
                {
                    callback?.OnWriteFailed("No destination.");
                    return;
                }

                // The whole PDF; the framework applies the pages chosen in its own dialog.
                using (var output = new JavaFile(destination.FileDescriptor))
                using (var input = File.OpenRead(path))
                {
                    var buffer = new byte[81920];
                    int read;
                    while ((read = input.Read(buffer, 0, buffer.Length)) > 0)
                    {
                        if (cancellationSignal?.IsCanceled == true)
                        {
                            callback?.OnWriteCancelled();
                            return;
                        }

                        output.Write(buffer, 0, read);
                    }
                }

                _wrote = true;
                callback?.OnWriteFinished(new[] { PageRange.AllPages! });
            }
            catch (Exception ex) when (ex is IOException or Java.IO.IOException)
            {
                callback?.OnWriteFailed(ex.Message);
            }
        }

        public override void OnFinish()
        {
            base.OnFinish();
            var outcome = Job switch
            {
                { IsCancelled: true } => PrintOutcome.Cancelled,
                { IsFailed: true } => PrintOutcome.Failed,
                _ when _wrote => PrintOutcome.Printed,
                _ => PrintOutcome.Cancelled,
            };
            _finished.TrySetResult(outcome);
        }
    }
}

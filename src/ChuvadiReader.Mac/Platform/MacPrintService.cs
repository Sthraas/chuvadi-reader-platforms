using ChuvadiReader.Core.Reader;
using Foundation;
using UIKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Prints through the native macOS print panel, keeping every page vector (never rasterised).
/// chuvadi-pdf prepares the print PDF — the chosen pages in order, decrypted with the file's
/// password — via <see cref="PrintDocumentBuilder"/>; <see cref="MacPdfPageRenderer"/> then draws each page onto
/// the sheet, placed by <see cref="PrintFit"/>. Copies, paper and the printer are chosen in the panel, as in any
/// Mac app.
/// The original file is never changed. A file whose own permissions forbid printing is refused
/// before the panel opens (<see cref="PrintPermission"/>, as the Windows print service does).
/// </summary>
public sealed class MacPrintService : IPrintService
{
    public bool IsAvailable => UIPrintInteractionController.PrintingAvailable;

    public async Task<PrintResult> PrintAsync(string pdfPath, PrintRequest request, CancellationToken ct = default)
    {
        PrintDocument doc;
        try
        {
            doc = await PrintDocumentBuilder.BuildAsync(pdfPath, request, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            return new PrintResult(PrintOutcome.Cancelled, 0);
        }
        catch (PrintRefusedException ex)
        {
            // The file's permissions forbid printing: refused before the panel, as on Windows.
            return new PrintResult(PrintOutcome.Failed, 0, ex.Message);
        }
        catch (ArgumentException ex)
        {
            return new PrintResult(PrintOutcome.Failed, 0, ex.Message);
        }
        catch (Exception ex)
        {
            return new PrintResult(PrintOutcome.Failed, 0, "Couldn't prepare the file for printing: " + ex.Message);
        }

        var tcs = new TaskCompletionSource<PrintResult>(TaskCreationOptions.RunContinuationsAsynchronously);
        UIApplication.SharedApplication.BeginInvokeOnMainThread(() =>
        {
            try
            {
                var info = UIPrintInfo.PrintInfo;
                info.JobName = doc.JobName;
                info.OutputType = UIPrintInfoOutputType.General;
                // M-26: a page shown landscape (a wide page, or an upright one with /Rotate 90) was fitted to the sheet's
                // long side but left on an upright sheet, so its right-hand third was cut off. UIKit does not turn the
                // sheet for a PDF item by itself; ask for the sheet the first page needs.
                info.Orientation = doc.Landscape ? UIPrintInfoOrientation.Landscape : UIPrintInfoOrientation.Portrait;

                var controller = UIPrintInteractionController.SharedPrintController;
                controller.PrintInfo = info;
                controller.ShowsPaperSelectionForLoadedPapers = true;
                // M-26, second part: even on a landscape sheet UIKit drew a PDF printing item into the upright sheet's
                // area and cut the page off. The pages are drawn onto the sheet here instead (still vector).
                controller.PrintPageRenderer = new MacPdfPageRenderer(doc.Pdf, request.FitToPage);

                controller.Present(true, (_, completed, error) =>
                {
                    if (error is not null)
                    {
                        tcs.TrySetResult(new PrintResult(PrintOutcome.Failed, 0, error.LocalizedDescription));
                    }
                    else if (completed)
                    {
                        tcs.TrySetResult(new PrintResult(PrintOutcome.Printed, doc.PageCount));
                    }
                    else
                    {
                        tcs.TrySetResult(new PrintResult(PrintOutcome.Cancelled, 0));
                    }
                });
            }
            catch (Exception ex)
            {
                tcs.TrySetResult(new PrintResult(PrintOutcome.Failed, 0, ex.Message));
            }
        });

        using (ct.Register(() => UIApplication.SharedApplication.BeginInvokeOnMainThread(
                   () => UIPrintInteractionController.SharedPrintController.Dismiss(true))))
        {
            return await tcs.Task.ConfigureAwait(false);
        }
    }
}

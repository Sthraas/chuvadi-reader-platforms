using ChuvadiReader.Core.Reader;
using Foundation;
using UIKit;

namespace ChuvadiReader.Mac.Platform;

/// <summary>
/// Prints through the native macOS print panel, keeping every page vector (never rasterised).
/// chuvadi-pdf prepares the print PDF — the chosen pages in order, decrypted with the file's
/// password — via <see cref="PrintDocumentBuilder"/>; the panel (an OS component) then prints that
/// PDF. Copies, paper, scaling and the printer itself are chosen in the panel, as in any Mac app.
/// The original file is never changed.
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

                var controller = UIPrintInteractionController.SharedPrintController;
                controller.PrintInfo = info;
                controller.ShowsPaperSelectionForLoadedPapers = true;
                controller.PrintingItem = NSData.FromArray(doc.Pdf);

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

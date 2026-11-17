namespace ChuvadiReader.Core.Documents;

/// <summary>D-198: what the Reader holds back or changes until it is on the patched libraries (Pdf 3.35.1,
/// Sheets 2.2.1, Docs 2.4.1; library advisory D-405/D-406). Phase 2 takes those libraries in one move and turns
/// these off; each use names this class, so the list of what to undo is a search away.</summary>
public static class LibraryHolds
{
    /// <summary>Redaction is hidden: on Pdf 3.32.0 a redacted copy can still hold the text it should remove, and
    /// the library's own check reports it clean (RED-16/17/18). Protect's other tools stay.</summary>
    public static bool RedactionHeld => true;

    /// <summary>Said where redaction was.</summary>
    public const string RedactionBack = "Redaction comes back with the next update.";

    /// <summary>Why, in one line.</summary>
    public const string RedactionWhy =
        "Until then a redacted copy could still hold the text it should remove, so it is switched off. Stamp, watermark, flatten, password and signing are in Protect as before.";

    /// <summary>Whether Excel's conditional colours are left out. On Sheets 2.0.4 evaluating them can end the
    /// process (sec08), run past a minute uncancellably (SEC-10) or take over a gigabyte (SEC-01). Arun decides
    /// between leaving them out for every file until Sheets 2.2.1 and keeping them; until he does, they stay on,
    /// as before. Changing this one value is the whole switch.</summary>
    public static bool ConditionalFormatsHeld => false;
}

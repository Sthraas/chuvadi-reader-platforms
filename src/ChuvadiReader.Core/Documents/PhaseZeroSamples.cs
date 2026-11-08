using ChuvadiReader.Platform;

namespace ChuvadiReader.Core.Documents;

/// <summary>
/// Where the Phase 0 sample recents, pins and watched folder appear: only on the Windows app, where
/// they have always been (desktop unchanged). Every other platform starts empty (Web H8; H-12, widened
/// by the coordinator's "fresh platform install", 7 Nov): the sample files don't exist there, and an
/// empty start shows the first-run box and D-89's wording. Remove with the rest of Phase 0.
/// </summary>
public static class PhaseZeroSamples
{
    /// <summary>True when this host shows the samples. No platform given (tests, older hosts): as before.</summary>
    public static bool Shown(IPlatformInfo? platform) => platform is null || platform.Kind == PlatformKind.Windows;
}

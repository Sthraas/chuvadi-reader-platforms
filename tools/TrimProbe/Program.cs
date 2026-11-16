// TESTING ONLY (AT-03). Exit code 0 when every service AddChuvadiReader registers can be built in a trimmed app.
using ChuvadiReader.Core.Storage;
using ChuvadiReader.Hosting;
using ChuvadiReader.Hosting.Desktop;
using ChuvadiReader.Platform;
using Microsoft.Extensions.DependencyInjection;

var services = new ServiceCollection();
services.AddChuvadiReader(AppStateLifetime.Process);
// What every host adds itself: who it is, and where settings live.
services.AddSingleton<IPlatformInfo>(new FixedPlatformInfo(PlatformKind.Linux, InputKinds.Mouse | InputKinds.Keyboard,
    new ShellChrome(WindowButtons.Right, false, false, true, 0), FixedPlatformInfo.DesktopCapabilities, new CtrlKeyLabels()));
services.AddSingleton<IAppStorage>(new FileAppStorage(Path.Combine(Path.GetTempPath(), "chvd-trimprobe-" + Environment.ProcessId)));

using var provider = services.BuildServiceProvider(new ServiceProviderOptions { ValidateOnBuild = false });
var failed = 0;
foreach (var type in services.Select(d => d.ServiceType).Distinct())
{
    try
    {
        _ = provider.GetRequiredService(type);
    }
    catch (Exception e)
    {
        failed++;
        Console.WriteLine($"FAIL {type.FullName}: {e.GetType().Name}: {e.Message}");
    }
}

Console.WriteLine($"{services.Count} registrations, {services.Select(d => d.ServiceType).Distinct().Count()} services, {failed} could not be built");

// The older code pages must not be switched on by startup, and must all still be there in a trimmed build.
bool onAtStartup = ChuvadiReader.Core.Documents.TextEncodings.CodePagesOn;
var missing = 0;
foreach (var choice in ChuvadiReader.Core.Documents.TextEncodings.All)
{
    try
    {
        _ = ChuvadiReader.Core.Documents.TextEncodings.Decode("plain"u8, choice.CodePage, out _);
    }
    catch (Exception e)
    {
        missing++;
        Console.WriteLine($"FAIL encoding {choice.Name}: {e.GetType().Name}: {e.Message}");
    }
}
Console.WriteLine($"{ChuvadiReader.Core.Documents.TextEncodings.All.Count} encodings, {missing} missing, code pages on at startup: {onAtStartup}");
return failed == 0 && missing == 0 && !onAtStartup ? 0 : 1;

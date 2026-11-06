namespace ChuvadiReader.Ui.Components.Platform.Portal;

/// <summary>
/// Addresses the web portal's chrome links to. Registered by the Web host only (desktop builds never
/// render portal components). Values come from the Web host's configuration and its Sangam client.
/// </summary>
/// <param name="DesktopAppUrl">"Download the desktop app" (12a) and "Get the desktop app" (12b account menu).</param>
/// <param name="AccountSettingsUrl">"Account settings" in the account menu (12b). Null hides the item.</param>
/// <param name="ForgotPasswordUrl">"Forgot?" beside the password field (12a). Null hides the link.</param>
public sealed record PortalLinks(string DesktopAppUrl, string? AccountSettingsUrl, string? ForgotPasswordUrl);

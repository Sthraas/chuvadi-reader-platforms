namespace ChuvadiReader.Ui.Components.Platform.Portal;

/// <summary>
/// What the person typed on the portal sign-in form (12a), handed to the Web host's Sangam client as typed.
/// <see cref="ToString"/> never includes the password, so the value is safe to log by accident.
/// </summary>
public sealed record PortalCredentials(string SangamId, string Password)
{
    public override string ToString() => $"PortalCredentials {{ SangamId = {SangamId}, Password = *** }}";
}

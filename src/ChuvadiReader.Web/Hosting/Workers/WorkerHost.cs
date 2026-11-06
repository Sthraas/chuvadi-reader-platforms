using System.Net;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using ChuvadiReader.Web.Auth;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Hosting.Workers;

/// <summary>
/// What the gateway tells a worker about each request. Identity values are base64url (UTF-8) so any
/// name fits in a header. The gateway removes every <c>X-Chvd-</c> header a browser sends.
/// </summary>
public static class GatewayHeaders
{
    public const string Prefix = "X-Chvd-";
    public const string Secret = "X-Chvd-Worker";
    public const string Sub = "X-Chvd-Sub";
    public const string Sid = "X-Chvd-Sid";
    public const string Name = "X-Chvd-Name";
    public const string Email = "X-Chvd-Email";
    public const string Unit = "X-Chvd-Unit";
    public const string Proto = "X-Chvd-Proto";
    public const string ClientIp = "X-Chvd-Client";

    /// <summary>Claims carried to the worker, and their headers.</summary>
    public static readonly (string Claim, string Header)[] Identity =
    [
        ("sub", Sub), ("sid", Sid), ("name", Name), ("email", Email), (SangamSignIn.UnitClaim, Unit),
    ];

    public static string Encode(string value) => Acme.AcmeJws.Base64Url(Encoding.UTF8.GetBytes(value));

    public static string? Decode(string? value)
    {
        if (string.IsNullOrEmpty(value) || value.Length > 2048)
        {
            return null;
        }

        try
        {
            return Encoding.UTF8.GetString(Acme.AcmeJws.FromBase64Url(value));
        }
        catch (FormatException)
        {
            return null;
        }
    }
}

/// <summary>The secret this worker shares with its gateway (first line of standard input). Singleton.</summary>
public sealed class WorkerSecret
{
    private readonly byte[] _secret;

    public WorkerSecret(string secret)
    {
        if (secret.Length < 32)
        {
            throw new InvalidOperationException("The worker secret is missing or too short.");
        }

        _secret = Encoding.ASCII.GetBytes(secret);
    }

    public bool Matches(string? presented)
        => presented is not null && CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(presented), _secret);
}

/// <summary>
/// Worker sign-in: a request counts only when it carries the gateway's secret, and only for the one
/// person this worker serves. The gateway did the real sign-in (Sangam) and checks the cookie.
/// </summary>
public sealed class GatewayIdentityHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    public const string SchemeName = "Gateway";

    private readonly WorkerSecret _secret;
    private readonly PortalOptions _portal;

    public GatewayIdentityHandler(IOptionsMonitor<AuthenticationSchemeOptions> options, ILoggerFactory logger, UrlEncoder encoder,
        WorkerSecret secret, IOptions<PortalOptions> portal)
        : base(options, logger, encoder)
    {
        _secret = secret;
        _portal = portal.Value;
    }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        if (!_secret.Matches(Request.Headers[GatewayHeaders.Secret]))
        {
            return Task.FromResult(AuthenticateResult.Fail("Not from the gateway."));
        }

        var claims = new List<Claim>();
        foreach (var (claim, header) in GatewayHeaders.Identity)
        {
            if (GatewayHeaders.Decode(Request.Headers[header]) is { Length: > 0 } value)
            {
                claims.Add(new Claim(claim, value));
            }
        }

        var principal = new ClaimsPrincipal(new ClaimsIdentity(claims, SchemeName, "name", "role"));
        if (Files.UserKey.From(principal) is not { } key || key != _portal.WorkerOwner)
        {
            return Task.FromResult(AuthenticateResult.Fail("This worker serves someone else."));
        }

        return Task.FromResult(AuthenticateResult.Success(new AuthenticationTicket(principal, SchemeName)));
    }
}

public static class WorkerHost
{
    public const string ControlPrefix = "/_worker";

    /// <summary>Reads the gateway's secret: the first line of standard input.</summary>
    public static WorkerSecret ReadSecret() => new(Console.In.ReadLine() ?? string.Empty);

    /// <summary>For gateway requests: the browser's scheme and address, so cookies, links and logs are right.</summary>
    public static IApplicationBuilder UseGatewayForwarding(this IApplicationBuilder app)
        => app.Use((http, next) =>
        {
            if (http.RequestServices.GetRequiredService<WorkerSecret>().Matches(http.Request.Headers[GatewayHeaders.Secret]))
            {
                if (http.Request.Headers[GatewayHeaders.Proto] is { Count: 1 } proto && (proto == "https" || proto == "http"))
                {
                    http.Request.Scheme = proto!;
                }

                if (IPAddress.TryParse(http.Request.Headers[GatewayHeaders.ClientIp], out var ip))
                {
                    http.Connection.RemoteIpAddress = ip;
                }
            }

            return next(http);
        });

    public sealed record EndRequest(string? Sub, string? Sid);

    public sealed record NoticeRequest(string Sub, string? Sid, DateTimeOffset? EndsAt, ExpiryReason Reason);

    /// <summary>The gateway's control calls. Only the gateway can authenticate here.</summary>
    public static IEndpointRouteBuilder MapWorkerControl(this IEndpointRouteBuilder app)
    {
        var g = app.MapGroup(ControlPrefix).RequireAuthorization().DisableAntiforgery();
        g.MapGet("/health", (OpenTabs tabs, CircuitCounter circuits) => Results.Json(new { tabs = tabs.Count, circuits = circuits.Count }));
        g.MapPost("/end", async (EndRequest r, OpenTabs tabs) => Results.Json(new { ended = await tabs.EndAsync(r.Sub, r.Sid).ConfigureAwait(false) }));
        g.MapPost("/notice", async (NoticeRequest r, OpenTabs tabs) =>
        {
            await tabs.NoticeAsync(r.Sub, r.Sid, r.EndsAt is { } at ? new ExpiryNotice(at, r.Reason) : null).ConfigureAwait(false);
            return Results.NoContent();
        });
        return app;
    }
}

/// <summary>Circuits alive in this process (connected or waiting to reconnect). Singleton.</summary>
public sealed class CircuitCounter
{
    private int _count;

    public int Count => Volatile.Read(ref _count);

    public void Opened() => Interlocked.Increment(ref _count);

    public void Closed() => Interlocked.Decrement(ref _count);
}

/// <summary>A worker ends when its gateway does: the gateway holds our standard input, so end of input
/// means it is gone (stopped, crashed or killed) and nobody can reach this person's files any more.</summary>
public sealed class GatewayLifeline : BackgroundService
{
    private readonly IHostApplicationLifetime _life;
    private readonly ILogger<GatewayLifeline> _log;

    public GatewayLifeline(IHostApplicationLifetime life, ILogger<GatewayLifeline> log)
    {
        _life = life;
        _log = log;
    }

    protected override Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // A background thread blocked on standard input (nothing else reads it in a worker); it never
        // holds up shutdown.
        var reader = new Thread(() =>
        {
            try
            {
                while (Console.In.ReadLine() is not null)
                {
                }
            }
            catch (IOException)
            {
            }

            if (!stoppingToken.IsCancellationRequested)
            {
                _log.LogInformation("Gateway is gone; stopping");
                _life.StopApplication();
            }
        })
        {
            IsBackground = true,
            Name = "gateway-lifeline",
        };
        reader.Start();
        return Task.CompletedTask;
    }
}

using System.Collections.Concurrent;

namespace ChuvadiReader.Web.Hosting.Acme;

/// <summary>Key authorizations for the http-01 challenges in flight (RFC 8555 §8.3). Singleton.</summary>
public sealed class Http01ChallengeStore
{
    public const string PathPrefix = "/.well-known/acme-challenge/";

    private readonly ConcurrentDictionary<string, string> _tokens = new(StringComparer.Ordinal);

    public void Publish(string token, string keyAuthorization) => _tokens[token] = keyAuthorization;

    public void Remove(string token) => _tokens.TryRemove(token, out _);

    public bool TryGet(string token, out string keyAuthorization) => _tokens.TryGetValue(token, out keyAuthorization!);

    public int Count => _tokens.Count;
}

public static class Http01ChallengeMiddleware
{
    /// <summary>
    /// Answers <c>GET /.well-known/acme-challenge/{token}</c> before HTTPS redirection and sign-in, on
    /// plain HTTP as the ACME server requires. Only tokens we published are answered; anything else
    /// under the prefix is 404. Nothing else is served this way.
    /// </summary>
    public static IApplicationBuilder UseHttp01Challenges(this IApplicationBuilder app)
        => app.Use(async (context, next) =>
        {
            var path = context.Request.Path.Value ?? string.Empty;
            if (!path.StartsWith(Http01ChallengeStore.PathPrefix, StringComparison.Ordinal))
            {
                await next(context).ConfigureAwait(false);
                return;
            }

            var store = context.RequestServices.GetRequiredService<Http01ChallengeStore>();
            var token = path[Http01ChallengeStore.PathPrefix.Length..];
            if (!HttpMethods.IsGet(context.Request.Method) || !store.TryGet(token, out var keyAuthorization))
            {
                context.Response.StatusCode = StatusCodes.Status404NotFound;
                return;
            }

            context.Response.ContentType = "application/octet-stream";
            context.Response.Headers.CacheControl = "no-store";
            await context.Response.WriteAsync(keyAuthorization, context.RequestAborted).ConfigureAwait(false);
        });
}

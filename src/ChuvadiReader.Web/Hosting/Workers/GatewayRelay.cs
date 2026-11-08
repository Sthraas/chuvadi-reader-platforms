using System.Buffers;
using System.Net.WebSockets;
using ChuvadiReader.Web.Files;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.Extensions.Options;

namespace ChuvadiReader.Web.Hosting.Workers;

/// <summary>
/// The gateway's relay (D-24, our own code): every signed-in request the gateway doesn't answer itself
/// goes to the person's own worker over its Unix socket — HTTP as a stream both ways, and the Blazor
/// circuit's WebSocket frame by frame. The browser's <c>X-Chvd-</c> headers and the gateway's own
/// cookies are dropped; the worker learns who is asking from the gateway's signed headers only.
/// </summary>
public static class GatewayRelay
{
    private static readonly HashSet<string> HopByHop = new(StringComparer.OrdinalIgnoreCase)
    {
        "Connection", "Keep-Alive", "Proxy-Connection", "Proxy-Authenticate", "Proxy-Authorization", "TE", "Trailer",
        "Transfer-Encoding", "Upgrade", "Host", "Cookie", "X-Dev-User",
        "Sec-WebSocket-Key", "Sec-WebSocket-Version", "Sec-WebSocket-Extensions", "Sec-WebSocket-Accept", "Sec-WebSocket-Protocol",
    };

    /// <summary>Maps the relay for every path not answered by the gateway itself.</summary>
    public static IEndpointRouteBuilder MapGatewayRelay(this IEndpointRouteBuilder app)
    {
        app.Map("/{**path}", RelayAsync).RequireAuthorization().DisableAntiforgery();
        return app;
    }

    private static async Task RelayAsync(HttpContext http, WorkerPool pool, IOptions<PortalOptions> options, ILoggerFactory logs)
    {
        if (http.Request.Path.StartsWithSegments(WorkerHost.ControlPrefix))
        {
            http.Response.StatusCode = StatusCodes.Status404NotFound;
            return;
        }

        WorkerProcess worker;
        try
        {
            worker = await pool.GetAsync(http.User, http.RequestAborted).ConfigureAwait(false);
        }
        catch (WorkerPoolFullException)
        {
            await Page(http, StatusCodes.Status503ServiceUnavailable, "The portal is busy",
                "It is serving as many people as it can right now. Please try again in a few minutes.").ConfigureAwait(false);
            return;
        }
        catch (Exception ex) when (ex is TimeoutException or InvalidOperationException or System.ComponentModel.Win32Exception)
        {
            logs.CreateLogger("ChuvadiReader.Web.Gateway").LogError(ex, "Couldn't start a worker");
            await Page(http, StatusCodes.Status503ServiceUnavailable, "The portal couldn't start your session",
                "Please try again in a moment.").ConfigureAwait(false);
            return;
        }

        if (http.WebSockets.IsWebSocketRequest)
        {
            await RelayWebSocketAsync(http, worker, logs).ConfigureAwait(false);
            return;
        }

        // Upload chunks may be larger than the gateway's small default body limit; the worker checks the exact size.
        if (http.Request.Path.StartsWithSegments("/portal/upload") && http.Features.Get<IHttpMaxRequestBodySizeFeature>() is { IsReadOnly: false } limit)
        {
            limit.MaxRequestBodySize = options.Value.UploadChunkBytes + 64 * 1024;
        }

        using var request = new HttpRequestMessage(new HttpMethod(http.Request.Method), http.Request.Path.ToUriComponent() + http.Request.QueryString.ToUriComponent());
        if (http.Request.ContentLength > 0 || http.Request.Headers.TransferEncoding.Count > 0)
        {
            request.Content = new StreamContent(http.Request.Body);
        }

        foreach (var (name, values) in http.Request.Headers)
        {
            if (HopByHop.Contains(name) || name.StartsWith(GatewayHeaders.Prefix, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            if (!request.Headers.TryAddWithoutValidation(name, (IEnumerable<string?>)values) && request.Content is not null)
            {
                request.Content.Headers.TryAddWithoutValidation(name, (IEnumerable<string?>)values);
            }
        }

        if (WorkerCookies(http) is { Length: > 0 } cookies)
        {
            request.Headers.TryAddWithoutValidation("Cookie", cookies);
        }

        request.Headers.Host = http.Request.Host.Value;
        Forward(request.Headers.TryAddWithoutValidation, http);
        worker.Sign(request, http.User);

        HttpResponseMessage response;
        try
        {
            response = await worker.Client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, http.RequestAborted).ConfigureAwait(false);
        }
        catch (HttpRequestException ex)
        {
            logs.CreateLogger("ChuvadiReader.Web.Gateway").LogWarning("Worker {Key} didn't answer: {Message}", worker.Key[..8], ex.Message);
            await Page(http, StatusCodes.Status502BadGateway, "Your session stopped", "Please reload the page to start again.").ConfigureAwait(false);
            return;
        }

        using (response)
        {
            http.Response.StatusCode = (int)response.StatusCode;
            foreach (var (name, values) in response.Headers.Concat(response.Content.Headers))
            {
                if (HopByHop.Contains(name))
                {
                    continue;
                }

                if (string.Equals(name, "Content-Security-Policy", StringComparison.OrdinalIgnoreCase))
                {
                    // WT-01: the gateway's own policy is already set; a worker's (Blazor adds
                    // "frame-ancestors 'self'" to interactive pages) must add to it, never replace it.
                    // The browser enforces every policy it gets, so the result is the stricter of the two.
                    http.Response.Headers.Append(name, values.ToArray());
                }
                else
                {
                    http.Response.Headers[name] = values.ToArray();
                }
            }

            http.Response.Headers.Remove("Transfer-Encoding");
            await using var body = await response.Content.ReadAsStreamAsync(http.RequestAborted).ConfigureAwait(false);
            try
            {
                await body.CopyToAsync(http.Response.Body, http.RequestAborted).ConfigureAwait(false);
            }
            catch (Exception ex) when (ex is OperationCanceledException or IOException or HttpRequestException)
            {
                http.Abort(); // the browser or the worker went away mid-response
            }
        }
    }

    private static async Task RelayWebSocketAsync(HttpContext http, WorkerProcess worker, ILoggerFactory logs)
    {
        using var upstream = new ClientWebSocket();
        upstream.Options.KeepAliveInterval = TimeSpan.Zero; // the circuit has its own pings
        upstream.Options.SetRequestHeader(GatewayHeaders.Secret, worker.Secret);
        foreach (var (claim, header) in GatewayHeaders.Identity)
        {
            if (http.User.FindFirst(claim)?.Value is { Length: > 0 } value)
            {
                upstream.Options.SetRequestHeader(header, GatewayHeaders.Encode(value));
            }
        }

        Forward((name, value) => { upstream.Options.SetRequestHeader(name, value); return true; }, http);
        foreach (var name in new[] { "Origin", "User-Agent", "Accept-Language" })
        {
            if (http.Request.Headers[name] is { Count: > 0 } v)
            {
                upstream.Options.SetRequestHeader(name, v.ToString());
            }
        }

        if (WorkerCookies(http) is { Length: > 0 } cookies)
        {
            upstream.Options.SetRequestHeader("Cookie", cookies);
        }

        foreach (var p in http.WebSockets.WebSocketRequestedProtocols)
        {
            upstream.Options.AddSubProtocol(p);
        }

        var target = new Uri("ws://worker" + http.Request.Path.ToUriComponent() + http.Request.QueryString.ToUriComponent());
        try
        {
            using var invoker = new HttpMessageInvoker(new UnixSocketHandler(worker.Socket));
            await upstream.ConnectAsync(target, invoker, http.RequestAborted).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is WebSocketException or HttpRequestException)
        {
            logs.CreateLogger("ChuvadiReader.Web.Gateway").LogWarning("Worker {Key} refused the circuit: {Message}", worker.Key[..8], ex.Message);
            http.Response.StatusCode = StatusCodes.Status502BadGateway;
            return;
        }

        using var downstream = await http.WebSockets.AcceptWebSocketAsync(upstream.SubProtocol).ConfigureAwait(false);
        using var stop = CancellationTokenSource.CreateLinkedTokenSource(http.RequestAborted);
        var up = PumpAsync(downstream, upstream, worker, stop.Token);
        var down = PumpAsync(upstream, downstream, worker, stop.Token);
        await Task.WhenAny(up, down).ConfigureAwait(false);
        await stop.CancelAsync().ConfigureAwait(false);
        downstream.Abort();
        upstream.Abort();
        await Task.WhenAll(up, down).ConfigureAwait(false);
    }

    /// <summary>Copies messages one way until a close or an error; passes the close on.</summary>
    private static async Task PumpAsync(WebSocket from, WebSocket to, WorkerProcess worker, CancellationToken ct)
    {
        var buffer = ArrayPool<byte>.Shared.Rent(16 * 1024);
        try
        {
            while (true)
            {
                var r = await from.ReceiveAsync(buffer.AsMemory(), ct).ConfigureAwait(false);
                if (r.MessageType == WebSocketMessageType.Close)
                {
                    if (to.State is WebSocketState.Open or WebSocketState.CloseReceived)
                    {
                        await to.CloseOutputAsync(from.CloseStatus ?? WebSocketCloseStatus.NormalClosure, from.CloseStatusDescription, ct).ConfigureAwait(false);
                    }

                    return;
                }

                await to.SendAsync(buffer.AsMemory(0, r.Count), r.MessageType, r.EndOfMessage, ct).ConfigureAwait(false);
                worker.Touch();
            }
        }
        catch (Exception ex) when (ex is WebSocketException or OperationCanceledException or IOException or ObjectDisposedException)
        {
        }
        finally
        {
            ArrayPool<byte>.Shared.Return(buffer);
        }
    }

    /// <summary>The browser's address and scheme for the worker.</summary>
    private static void Forward(Func<string, string, bool> add, HttpContext http)
    {
        add(GatewayHeaders.Proto, http.Request.Scheme);
        if (http.Connection.RemoteIpAddress is { } ip)
        {
            add(GatewayHeaders.ClientIp, ip.ToString());
        }
    }

    /// <summary>The browser's cookies minus the gateway's own (the sign-in cookie never reaches a worker).</summary>
    private static string WorkerCookies(HttpContext http)
        => string.Join("; ", http.Request.Cookies
            .Where(c => !c.Key.StartsWith("__Host-chvd", StringComparison.Ordinal) && !c.Key.StartsWith("chvd.", StringComparison.Ordinal))
            .Select(c => c.Key + "=" + c.Value));

    private static Task Page(HttpContext http, int status, string title, string message)
    {
        if (http.Response.HasStarted)
        {
            return Task.CompletedTask;
        }

        http.Response.StatusCode = status;
        http.Response.ContentType = "text/html; charset=utf-8";
        http.Response.Headers.CacheControl = "no-store";
        return http.Response.WriteAsync(Auth.SangamSignIn.Page(title, System.Net.WebUtility.HtmlEncode(message), "/", "Try again"));
    }

    /// <summary>Connects to a worker's Unix socket (for the circuit's WebSocket).</summary>
    private sealed class UnixSocketHandler(string socket) : DelegatingHandler(new SocketsHttpHandler
    {
        ConnectCallback = async (_, token) =>
        {
            var s = new System.Net.Sockets.Socket(System.Net.Sockets.AddressFamily.Unix, System.Net.Sockets.SocketType.Stream, System.Net.Sockets.ProtocolType.Unspecified);
            try
            {
                await s.ConnectAsync(new System.Net.Sockets.UnixDomainSocketEndPoint(socket), token).ConfigureAwait(false);
                return new System.Net.Sockets.NetworkStream(s, ownsSocket: true);
            }
            catch
            {
                s.Dispose();
                throw;
            }
        },
        UseProxy = false,
        UseCookies = false,
    });
}

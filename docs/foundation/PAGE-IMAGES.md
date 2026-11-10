# Page images by address (D-158 part 2, twenty-first combined patch)

Drawn raster pages (large-format sheets, and pages whose vector drawing is too heavy) are no longer carried inline as a ~77 MB base64 string. The PNG stays in memory in `PageImages` (Core, one per process). The page's SVG is the same, character for character, except that its `<image href>` is `_chvd/pages/<token>.png`.

- **Token:** 128 random bits, 32 lower-case hex characters.
- **Owner:** each image has one (`IPageImageOwner.Current`) and is served only to it.
- **Freed** when its page leaves the cache (a background tab, a layer change) or its document closes. A page drawn for a document that closed meanwhile is never kept.
- **Unknown, freed or someone else's token:** "not found", the same as a file that doesn't exist.
- **Vector pages** (ordinary documents) are unchanged.

## Hooks (one line per host)
| Host | Hook | Owner |
|---|---|---|
| **Windows (WPF)**, Foundation, done | `ChuvadiWebView : BlazorWebView`, `CreateFileProvider(dir) => new PageImageFileProvider(base.CreateFileProvider(dir), Services)`; MainWindow uses it | default (`"local"`) |
| **macOS (MAUI, Mac Catalyst)**, Mac chat | the same override in its BlazorWebView subclass (MAUI's `BlazorWebView.CreateFileProvider` is virtual) | default |
| **Android (MAUI)**, Android chat | the same override | default |
| **Linux (WebKitGTK)**, Linux chat | wrap the provider its `WebViewManager` is constructed with: `new PageImageFileProvider(yourProvider, services)` | default |
| **Web portal (SignalR)**, Web chat, then Web Test's security pass | the endpoint below, plus its own `IPageImageOwner` registered per connection | the signed-in user **and** their session |

All in process: WebView2, WKWebView, WebKitGTK and Android WebView read through their file-provider hook. **No localhost server, nothing leaves the device, nothing new ships.** `Microsoft.Extensions.FileProviders.Abstractions` is already in every BlazorWebView host and in ASP.NET Core.

### Portal endpoint (Web chat)
```csharp
// Program.cs — same origin, signed-in users only, per-session owner, nothing cached.
app.MapGet("/" + PageImages.PathPrefix + "{file}",
    (string file, HttpContext http, [FromServices] PageImages images, [FromServices] IPageImageOwner owner) =>
    {
        if (!PageImages.TryParseAddress(file, out var token) || !images.TryGet(token, owner.Current, out var png))
            return Results.NotFound();          // unknown, freed, or someone else's: all the same answer
        http.Response.Headers.CacheControl = "private, no-store";
        return Results.Bytes(png, "image/png");
    }).RequireAuthorization();
```
- **`IPageImageOwner` on the portal:**
  - scoped (per connection);
  - returns a value from the server-side session of the signed-in user (user id + session id), never anything the browser sends;
  - the circuit (drawing) and the endpoint (fetching) must compute the same value for the same person and session.
- **Things for Web Test's security pass:**
  - tokens are unguessable and compared in fixed time;
  - one owner can't read another's (another user, or the same user's other session);
  - freed and expired tokens give 404;
  - no directory paths;
  - `private, no-store`;
  - same origin only (no CORS).

## Proof
- **`PageImagesTests` (Core, 13):**
  - tokens are 128-bit and unique;
  - owner-only access, and freed means gone;
  - only a well-formed address is read;
  - the page's SVG is identical apart from the href, and the PNG behind the address is byte for byte the PNG that was inline;
  - images are freed on cache drop and on close;
  - a page drawn for a closed document is never kept.
- **`PageImageFileProviderTests` (Hosting, 4):** served from memory byte for byte; unknown, freed or other owner not found; every other path untouched; the kit wires it.
- **`tools/PixelProof/raster-identical.js`:** a 26 MB two-page raster PDF in the desktop preview, inline vs by address, first page after Fit page: **IDENTICAL at 1× and 2×, twice.**
- **Preview memory** with the same pages shown and four page loads each: **2354 MB inline vs 438 MB by address.**
- **Preview endpoint:** unknown token 404; `..` path 404; a page 200, `image/png`, `Cache-Control: private, no-store`.

using System.Runtime.CompilerServices;
using ChuvadiReader.Ui.Components;
using Microsoft.AspNetCore.Components;
using Microsoft.AspNetCore.Components.Rendering;
using Microsoft.AspNetCore.Components.RenderTree;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

#pragma warning disable BL0006 // a minimal renderer for the test, as Blazor's own tests use

namespace ChuvadiReader.WebUi.Tests;

/// <summary>
/// Nineteenth patch (Linux finding 3): a closed document's drawn pages must not stay referenced by the Ui. Blazor
/// keeps the render before last for diffing, so a page's text (≈ 77 MB per CAD sheet) stays alive until a second
/// render after the document changes. The Reader renders once more after a change and keys each PageSvg by its
/// document; these tests pin why both are needed, with the real PageSvg.
/// </summary>
public sealed class PageReleaseTests
{
    private sealed class TestRenderer() : Renderer(new ServiceCollection().BuildServiceProvider(), NullLoggerFactory.Instance)
    {
        public override Dispatcher Dispatcher { get; } = Dispatcher.CreateDefault();

        protected override void HandleException(Exception exception) => throw exception;

        protected override Task UpdateDisplayAsync(in RenderBatch renderBatch) => Task.CompletedTask;

        public int Attach(IComponent component) => AssignRootComponentId(component);

        public Task RenderRoot(int id) => RenderRootComponentAsync(id);
    }

    /// <summary>The Reader's page markup: one PageSvg per page, keyed by the document it shows.</summary>
    private sealed class Desk : ComponentBase
    {
        public object? Document { get; set; }

        public string? Svg { get; set; }

        public void Refresh() => StateHasChanged();

        protected override void BuildRenderTree(RenderTreeBuilder builder)
        {
            builder.OpenElement(0, "div");
            if (Svg is not null)
            {
                builder.OpenComponent<PageSvg>(1);
                builder.SetKey(Document);
                builder.AddComponentParameter(2, nameof(PageSvg.Svg), Svg);
                builder.CloseComponent();
            }

            builder.CloseElement();
        }
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static async Task<WeakReference> ShowThenSwitch(TestRenderer renderer, Desk desk, int id, bool renderOnceMore)
    {
        var heavyPage = "<svg>" + new string('x', 8_000_000) + "</svg>";
        var page = new WeakReference(heavyPage);
        desk.Document = new object();
        desk.Svg = heavyPage;
        await renderer.Dispatcher.InvokeAsync(() => renderer.RenderRoot(id));

        desk.Document = new object();            // the tab closed; another document is on show
        desk.Svg = "<svg>next file</svg>";
        await renderer.Dispatcher.InvokeAsync(desk.Refresh);
        if (renderOnceMore)
        {
            await renderer.Dispatcher.InvokeAsync(desk.Refresh);
        }

        return page;
    }

    private static void Collect()
    {
        for (var i = 0; i < 3; i++)
        {
            GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
            GC.WaitForPendingFinalizers();
        }
    }

    [Fact]
    public async Task One_render_after_a_document_change_still_holds_the_old_page()
    {
        using var renderer = new TestRenderer();
        var desk = new Desk();
        var page = await ShowThenSwitch(renderer, desk, renderer.Attach(desk), renderOnceMore: false);
        Collect();

        Assert.True(page.IsAlive); // why the Reader renders once more: Blazor's previous render still holds it
    }

    [Fact]
    public async Task Rendering_once_more_lets_the_old_page_go()
    {
        using var renderer = new TestRenderer();
        var desk = new Desk();
        var page = await ShowThenSwitch(renderer, desk, renderer.Attach(desk), renderOnceMore: true);
        Collect();

        Assert.False(page.IsAlive);
    }
}

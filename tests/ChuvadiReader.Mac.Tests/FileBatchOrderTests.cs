using ChuvadiReader.Mac.Platform;
using Xunit;

namespace ChuvadiReader.Mac.Tests;

/// <summary>M-24: a batch of files opens in Finder's Name order, whatever order macOS hands it over in.</summary>
public sealed class FileBatchOrderTests
{
    [Fact]
    public void A_shuffled_batch_comes_out_in_name_order()
    {
        var sorted = FileBatchOrder.Sort(new[] { "/d/sample.docx", "/d/third.pdf", "/d/five-pages.pdf", "/d/second.pdf" });
        Assert.Equal(new[] { "/d/five-pages.pdf", "/d/sample.docx", "/d/second.pdf", "/d/third.pdf" }, sorted);
    }

    [Fact]
    public void Numbers_sort_by_value_and_case_is_ignored()
    {
        var sorted = FileBatchOrder.Sort(new[] { "/d/page 10.pdf", "/d/Page 2.pdf", "/d/page 1.pdf", "/d/Annex.pdf", "/d/annex b.pdf" });
        Assert.Equal(new[] { "/d/Annex.pdf", "/d/annex b.pdf", "/d/page 1.pdf", "/d/Page 2.pdf", "/d/page 10.pdf" }, sorted);
    }

    [Fact]
    public void The_same_names_in_different_folders_keep_a_fixed_order()
    {
        var a = FileBatchOrder.Sort(new[] { "/b/x.pdf", "/a/x.pdf" });
        var b = FileBatchOrder.Sort(new[] { "/a/x.pdf", "/b/x.pdf" });
        Assert.Equal(a, b);
        Assert.Equal("/a/x.pdf", a[0]);
    }
}

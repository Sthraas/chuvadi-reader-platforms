using ChuvadiReader.Web.Hosting;
using Xunit;

namespace ChuvadiReader.Web.Tests;

/// <summary>D-28: working copies in RAM, never paged to disk in the clear.</summary>
[System.Runtime.Versioning.SupportedOSPlatform("linux")]
public class StorageCheckTests
{
    private readonly string _root = SpaceLayoutTests.NewTempDir();

    private (string Proc, string Sys) Fake(string[] mounts, string[] swaps, Dictionary<string, string>? dmUuids = null)
    {
        var proc = Path.Combine(_root, "proc");
        var sys = Path.Combine(_root, "sys");
        Directory.CreateDirectory(Path.Combine(proc, "self"));
        File.WriteAllLines(Path.Combine(proc, "self", "mountinfo"), mounts);
        File.WriteAllLines(Path.Combine(proc, "swaps"), ["Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority", .. swaps]);
        foreach (var (block, uuid) in dmUuids ?? new())
        {
            Directory.CreateDirectory(Path.Combine(sys, "block", block, "dm"));
            File.WriteAllText(Path.Combine(sys, "block", block, "dm", "uuid"), uuid + "\n");
        }

        return (proc, sys);
    }

    private static readonly string[] Mounts =
    [
        "22 1 252:1 / / rw,relatime shared:1 - ext4 /dev/vda1 rw",
        "30 22 0:26 / /srv/chuvadi rw,nosuid,nodev - tmpfs tmpfs rw,size=4194304k,mode=700",
        "31 22 252:2 / /srv/chuvadi/disk rw - ext4 /dev/mapper/data rw",
        "32 22 0:27 / /srv/with\\040space rw - tmpfs tmpfs rw,size=1024k",
    ];

    [Fact]
    public void A_data_root_on_tmpfs_passes_and_one_on_disk_is_refused()
    {
        var (proc, sys) = Fake(Mounts, []);
        Assert.Empty(StorageCheck.Problems("/srv/chuvadi/data", new StorageOptions(), proc, sys));
        Assert.Empty(StorageCheck.Problems("/srv/with space/data", new StorageOptions(), proc, sys));

        var onDisk = StorageCheck.Problems("/srv/chuvadi/disk/data", new StorageOptions(), proc, sys);
        Assert.Contains("ext4", Assert.Single(onDisk));
        Assert.Contains("ext4", Assert.Single(StorageCheck.Problems("/var/lib/chuvadi", new StorageOptions(), proc, sys)));
    }

    [Fact]
    public void Swap_must_be_off_encrypted_or_in_ram()
    {
        var plain = Fake(Mounts, ["/dev/vda3\tpartition\t1048572\t0\t-2"]);
        Assert.Contains("vda3", Assert.Single(StorageCheck.Problems("/srv/chuvadi/data", new StorageOptions(), plain.Proc, plain.Sys)));

        var file = Fake(Mounts, ["/swapfile\tfile\t1048572\t0\t-2"]);
        Assert.Single(StorageCheck.Problems("/srv/chuvadi/data", new StorageOptions(), file.Proc, file.Sys));

        var crypt = Fake(Mounts, ["/dev/dm-3\tpartition\t1048572\t0\t-2", "/dev/zram0\tpartition\t1048572\t0\t100"],
            new() { ["dm-3"] = "CRYPT-PLAIN-cryptswap" });
        Assert.Empty(StorageCheck.Problems("/srv/chuvadi/data", new StorageOptions(), crypt.Proc, crypt.Sys));

        var lvm = Fake(Mounts, ["/dev/dm-4\tpartition\t1048572\t0\t-2"], new() { ["dm-4"] = "LVM-abcdef" });
        Assert.Single(StorageCheck.Problems("/srv/chuvadi/data", new StorageOptions(), lvm.Proc, lvm.Sys));
    }

    [Fact]
    public void Checks_can_be_turned_off_one_by_one()
    {
        var (proc, sys) = Fake(Mounts, ["/dev/vda3\tpartition\t1048572\t0\t-2"]);
        Assert.Single(StorageCheck.Problems("/var/lib/chuvadi", new StorageOptions { RequireEncryptedSwap = false }, proc, sys));
        Assert.Empty(StorageCheck.Problems("/var/lib/chuvadi", new StorageOptions { RequireEncryptedSwap = false, RequireMemoryFileSystem = false }, proc, sys));
    }

    [Fact]
    public void This_machines_shared_memory_is_seen_as_tmpfs()
    {
        if (!Directory.Exists("/dev/shm"))
        {
            return;
        }

        Assert.Equal("tmpfs", StorageCheck.MountOf("/dev/shm/chuvadi", "/proc/self/mountinfo").Type);
    }

    [Fact]
    public void Production_start_is_refused_when_the_data_root_is_on_disk()
    {
        if (StorageCheck.MountOf(_root, "/proc/self/mountinfo").Type is "tmpfs" or "ramfs")
        {
            return; // this machine's temp folder is already in RAM
        }

        var ex = Assert.Throws<InvalidOperationException>(() => Program.Build(
        [
            "--environment", "Production",
            "--Portal:DataRoot", _root,
            "--Portal:PublicOrigin", "https://reader.example.in",
            "--Portal:Storage:RequireEncryptedSwap", "false",
        ]));
        Assert.Contains("D-28", ex.Message);
    }
}

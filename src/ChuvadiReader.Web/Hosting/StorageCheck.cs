namespace ChuvadiReader.Web.Hosting;

/// <summary>Where working copies may live (section <c>Portal:Storage</c>; D-28).</summary>
public sealed class StorageOptions
{
    /// <summary>Refuse to start unless <c>Portal:DataRoot</c> is on a RAM file system (tmpfs). On by
    /// default outside Development; turning it off needs the data root on an encrypted (LUKS) volume.</summary>
    public bool RequireMemoryFileSystem { get; set; } = true;

    /// <summary>Refuse to start while any swap could write RAM (and so working copies) to disk
    /// unencrypted. Swap may be off, on dm-crypt (LUKS or plain), or on zram.</summary>
    public bool RequireEncryptedSwap { get; set; } = true;
}

/// <summary>
/// D-28 at start-up: working copies live in RAM (tmpfs, size-limited) and nothing pages them to disk in
/// the clear. Linux only; the paths are parameters so tests can give their own <c>/proc</c> and <c>/sys</c>.
/// </summary>
public static class StorageCheck
{
    /// <summary>Problems found, in plain words; empty when the data root is fit for working copies.</summary>
    public static IReadOnlyList<string> Problems(string dataRoot, StorageOptions options, string proc = "/proc", string sys = "/sys")
    {
        var problems = new List<string>();
        if (!OperatingSystem.IsLinux())
        {
            problems.Add("The portal's production checks need Linux.");
            return problems;
        }

        if (options.RequireMemoryFileSystem)
        {
            var (mount, type) = MountOf(Path.GetFullPath(dataRoot), Path.Combine(proc, "self", "mountinfo"));
            if (type is not "tmpfs" and not "ramfs")
            {
                problems.Add($"Portal:DataRoot ({dataRoot}) is on {type ?? "an unknown file system"} mounted at {mount ?? "?"}; working copies must be in RAM (tmpfs) — D-28.");
            }
        }

        if (options.RequireEncryptedSwap)
        {
            foreach (var (name, kind) in Swaps(Path.Combine(proc, "swaps")))
            {
                if (!EncryptedOrRam(name, kind, sys))
                {
                    problems.Add($"Swap {name} ({kind}) isn't encrypted, so working copies in RAM could reach the disk in the clear. Turn it off, or put it on dm-crypt or zram — D-28.");
                }
            }
        }

        return problems;
    }

    /// <summary>The mount point and file-system type holding <paramref name="path"/> (the longest
    /// matching mount point in mountinfo, so later and deeper mounts win).</summary>
    internal static (string? Mount, string? Type) MountOf(string path, string mountinfo)
    {
        string? bestMount = null, bestType = null;
        if (!File.Exists(mountinfo))
        {
            return (null, null);
        }

        foreach (var line in File.ReadLines(mountinfo))
        {
            // id parent major:minor root mount-point options [optional fields] - fstype source super-options
            var dash = line.IndexOf(" - ", StringComparison.Ordinal);
            if (dash < 0)
            {
                continue;
            }

            var left = line[..dash].Split(' ');
            var right = line[(dash + 3)..].Split(' ');
            if (left.Length < 5 || right.Length < 1)
            {
                continue;
            }

            var mount = Unescape(left[4]);
            if (mount == "/" || path == mount || Files.SpaceLayout.IsInside(mount, path))
            {
                if (bestMount is null || mount.Length >= bestMount.Length)
                {
                    (bestMount, bestType) = (mount, right[0]);
                }
            }
        }

        return (bestMount, bestType);
    }

    /// <summary>Active swaps from <c>/proc/swaps</c>: name and type (partition or file).</summary>
    internal static IEnumerable<(string Name, string Kind)> Swaps(string swaps)
    {
        if (!File.Exists(swaps))
        {
            yield break;
        }

        foreach (var line in File.ReadLines(swaps).Skip(1))
        {
            var cols = line.Split((char[])[' ', '\t'], StringSplitOptions.RemoveEmptyEntries);
            if (cols.Length >= 2)
            {
                yield return (Unescape(cols[0]), cols[1]);
            }
        }
    }

    /// <summary>A swap partition on dm-crypt or zram. Swap files are refused: their blocks sit on
    /// whatever disk holds the file system.</summary>
    internal static bool EncryptedOrRam(string name, string kind, string sys)
    {
        if (kind != "partition")
        {
            return false;
        }

        var device = name;
        try
        {
            if (new FileInfo(name).LinkTarget is { } target)
            {
                device = Path.GetFullPath(target, Path.GetDirectoryName(name)!); // /dev/mapper/x -> /dev/dm-3
            }
        }
        catch (IOException)
        {
        }

        var block = Path.GetFileName(device);
        if (block.StartsWith("zram", StringComparison.Ordinal))
        {
            return true;
        }

        var uuid = Path.Combine(sys, "block", block, "dm", "uuid");
        return File.Exists(uuid) && File.ReadAllText(uuid).StartsWith("CRYPT-", StringComparison.Ordinal);
    }

    /// <summary>mountinfo and swaps write spaces and some characters as octal escapes (<c>\040</c>).</summary>
    private static string Unescape(string s)
    {
        if (!s.Contains('\\'))
        {
            return s;
        }

        var sb = new System.Text.StringBuilder(s.Length);
        for (var i = 0; i < s.Length; i++)
        {
            if (s[i] == '\\' && i + 3 < s.Length && s[(i + 1)..(i + 4)].All(c => c is >= '0' and <= '7'))
            {
                sb.Append((char)Convert.ToInt32(s[(i + 1)..(i + 4)], 8));
                i += 3;
            }
            else
            {
                sb.Append(s[i]);
            }
        }

        return sb.ToString();
    }
}

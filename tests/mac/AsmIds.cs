// Mac Test — TESTING ONLY. Prints name, version, public key token and company/copyright attributes of every
// .NET assembly in a folder tree, as tab-separated lines. Run: dotnet run tests/mac/AsmIds.cs -- <dir>
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;

var root = args.Length > 0 ? args[0] : ".";
foreach (var path in Directory.EnumerateFiles(root, "*.dll", SearchOption.AllDirectories).Order())
{
    try
    {
        using var fs = File.OpenRead(path);
        using var pe = new PEReader(fs);
        if (!pe.HasMetadata) { Console.WriteLine($"{path}\t(no metadata)"); continue; }
        var md = pe.GetMetadataReader();
        if (!md.IsAssembly) { Console.WriteLine($"{path}\t(module, not an assembly)"); continue; }
        var asm = md.GetAssemblyDefinition();
        var name = md.GetString(asm.Name);
        var key = md.GetBlobBytes(asm.PublicKey);
        string token = "null";
        if (key.Length > 0)
        {
            var hash = System.Security.Cryptography.SHA1.HashData(key);
            token = string.Concat(hash[^8..].Reverse().Select(b => b.ToString("x2")));
        }
        string Attr(string attrName)
        {
            foreach (var h in asm.GetCustomAttributes())
            {
                var ca = md.GetCustomAttribute(h);
                if (ca.Constructor.Kind != HandleKind.MemberReference) continue;
                var mr = md.GetMemberReference((MemberReferenceHandle)ca.Constructor);
                if (mr.Parent.Kind != HandleKind.TypeReference) continue;
                var tr = md.GetTypeReference((TypeReferenceHandle)mr.Parent);
                if (md.GetString(tr.Name) != attrName) continue;
                var blob = md.GetBlobReader(ca.Value);
                blob.ReadUInt16();
                return blob.ReadSerializedString() ?? "";
            }
            return "";
        }
        Console.WriteLine($"{Path.GetRelativePath(root, path)}\t{name}\t{asm.Version}\t{token}\t{Attr("AssemblyCompanyAttribute")}\t{Attr("AssemblyCopyrightAttribute")}");
    }
    catch (Exception ex)
    {
        Console.WriteLine($"{path}\t(error {ex.GetType().Name}: {ex.Message})");
    }
}

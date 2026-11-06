using System.Xml.Linq;
using Microsoft.AspNetCore.DataProtection.Repositories;

namespace ChuvadiReader.Web.Hosting;

/// <summary>Data Protection keys kept in this process's memory only (they die with it). Singleton.</summary>
public sealed class InMemoryKeyRepository : IXmlRepository
{
    private readonly List<XElement> _elements = new();
    private readonly Lock _lock = new();

    public IReadOnlyCollection<XElement> GetAllElements()
    {
        lock (_lock)
        {
            return _elements.Select(e => new XElement(e)).ToList();
        }
    }

    public void StoreElement(XElement element, string friendlyName)
    {
        lock (_lock)
        {
            _elements.Add(new XElement(element));
        }
    }
}

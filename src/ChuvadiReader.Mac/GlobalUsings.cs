global using Microsoft.Extensions.DependencyInjection;

// MAUI brings its own Microsoft.Maui.Storage.IFilePicker into scope; the host implements Core's.
global using IFilePicker = ChuvadiReader.Core.Reader.IFilePicker;

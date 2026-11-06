global using Microsoft.Extensions.DependencyInjection;

// MAUI's implicit usings bring its own Essentials interfaces with the same names as the
// Chuvadi seams this host implements; these aliases pick the Chuvadi ones.
global using IFilePicker = ChuvadiReader.Core.Reader.IFilePicker;
global using IClipboard = ChuvadiReader.Platform.IClipboard;
global using IShare = ChuvadiReader.Platform.IShare;

// MAUI's implicit usings bring Microsoft.Maui.Storage.IFilePicker and
// Microsoft.Maui.ApplicationModel.DataTransfer.IClipboard / IShare, which clash with the
// Chuvadi contracts of the same names. In this host those names always mean Chuvadi's.
global using IFilePicker = ChuvadiReader.Core.Reader.IFilePicker;
global using IClipboard = ChuvadiReader.Platform.IClipboard;
global using IShare = ChuvadiReader.Platform.IShare;

# D-198 on Android: parsing documents in a helper process

Android's note for Foundation's design (17 Nov). Nothing is built yet.

## The two ways Android allows

**A. Isolated service** (`<service android:isolatedProcess="true">`).
- The service runs in its own process under a throwaway user id. It has no permissions, no network, and no access to the app's files.
- The app has to bind to it (`bindService`); it cannot be started with `startService`. When the last binding goes, Android ends the process.
- The strongest choice: a crafted file that takes over the parser still gets nothing.
- **The catch for us:** the .NET for Android SDK starts the .NET runtime in each process through a content provider (`MonoRuntimeProvider`, one per process name, from `Xamarin.Android.Common.targets`). Android never starts content providers in an isolated process. So a C# service there finds no runtime, and the SDK has no supported way to start one. Making it work means calling the SDK's internal start-up code from Java, which a future SDK can break. I would not ship that.

**B. A second process of the app** (`<service android:process=":parser">`).
- Supported by the SDK: it adds a runtime provider for that process, so C# runs there as in the main app.
- The same user id as the app, so the helper can read the app's files. This contains crashes, hangs and memory blow-ups; it does not stop a taken-over parser from reading the app's data.

## How the app and the helper talk

- **Binder** through a bound service. There is no AIDL in .NET for Android, so the interface is hand-written in C#: a `Binder` with `OnTransact`, `Parcel` in and out. Or `Messenger` (simpler, one message at a time).
- **The document goes in as a file descriptor** (`ParcelFileDescriptor`). That's the only route for an isolated helper, which cannot open paths.
- **Results come back through `SharedMemory` (API 27 and up; our minimum is 35) or a pipe.** One Binder transaction is capped at about 1 MB, so page images and large models can't go inline.
- **Dying is visible:** the app gets `binderDied` / `DeadObjectException` when the helper crashes or is killed. The Ui then says the file couldn't be opened.

## Limits we can enforce

- **Time:** a timer in the app. When it runs out, the app unbinds and kills the helper (`Process.KillProcess` works on our own processes in B; in A, unbinding ends it).
- **Memory:** no OS cap per process is open to apps (no cgroups API). What we can do:
  - the GC heap hard limit inside the helper (`GCHeapHardLimit`): a .NET out-of-memory becomes a clean failure there, not in the app;
  - the helper reports its own use, and the app's timer acts on it.
  - `setrlimit` on address space breaks ART and .NET, which reserve large virtual ranges, so it isn't usable.
  - Reading another process's memory from outside is limited: `ActivityManager.getProcessMemoryInfo` is rate-limited for apps on Android 10 and later.
- **Android's own low-memory killer** may end the helper first. That is fine: it reads as a failed open, not an app crash.

## Cost

- **Memory:** a second ART process plus a second .NET runtime, on the order of tens of MB resident while it lives. This needs measuring on our build.
- **Cold start:** a new process from zygote plus .NET start-up. Our AT-14 timeline (run 42803390901) puts "first managed code" at 258 ms median (925 worst) on the phone and 663 / 1248 ms on the tablet emulator. Expect about that added to the first open after the helper starts.
- **Keeping it warm:** binding while the app is in front pays that once per session, not per file.

## What cannot be done on Android

- A .NET parser in an isolated process with the SDK as it is (see A).
- A hard OS memory cap per process.
- `fork()` of the running .NET process.
- Anything that needs the parser to open paths itself, if it is isolated.

## Recommendation

B (`:parser`, bound service, hand-written Binder, file descriptor in, `SharedMemory` out, GC heap limit plus a timer in the app). It contains crashes, hangs and memory blow-ups, which is what the advisory asks for, using only the SDK and the OS.

A is stronger isolation, but only if Microsoft's SDK starts .NET in isolated processes. If Arun wants A, the first step is a 1–2 day spike to prove it (or disprove it) before Foundation's design depends on it. Either way the helper API Foundation designs should take a stream or file descriptor in, not a path, so the same API fits A later.

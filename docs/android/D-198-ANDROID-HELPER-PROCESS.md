# D-198 on Android: parsing documents in a helper process

Android's note for Foundation's design (17 Nov; measurements added 18 Nov). Arun approved D-202 (Foundation's parse-process design): on Android **D1**, a service in its own process (`android:process=":engine"`), and **E2**, the engine starts when the first document opens. Foundation builds Windows and Linux first; Android is step 4. The measurements below come from a test-only probe; nothing of the engine is built yet.

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

## Cost (estimates from 17 Nov; measured below)

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

## Measured on the emulators (D-202, 18 Nov)

**How.** A test-only probe build (`-p:ChuvadiEngineProbe=true`, code in `src/ChuvadiReader.Android/Platform/EngineProbe/`, never shipped):
- A bound service in `android:process=":engine"` answering over a hand-written Binder. The SDK adds a .NET runtime start-up for that process (`mono.MonoRuntimeProvider_1`), so C# runs there unchanged.
- In the engine process, `MainApplication` sets up a bare MAUI app, not the Reader's (no Blazor, no Chuvadi services).
- The app was already running with its Ui up, as with E2. 10 engine starts each: 5 after dropping the page cache, 5 without.
- Release build, as shipped, plus a second build with `MONO_GC_PARAMS=max-heap-size=256m`.
- Script: `docs/android/ci/engine_probe.py`, CI suite `engine`. Clean run: **44257020519**; the JSON reports and logs are in its artifacts.
- `manifest-check.sh` fails any build that declares the probe, so it can't ship.

**1. Time from `bindService` to the engine's first answer** (ms, median / worst). "Cold" means the page cache was dropped first; the engine process is always new.

| Emulator | Cold, as shipped | Warm, as shipped | Cold, heap capped | Warm, heap capped |
|---|---|---|---|---|
| Phone, API 36 | 236 / 297 | 219 / 324 | 246 / 255 | 205 / 211 |
| Phone, API 35 | 494 / 892 | 332 / 350 | 395 / 432 | 364 / 396 |
| Tablet, API 36 | 626 / 1252 | 396 / 437 | 469 / 606 | 442 / 688 |
| Tablet, API 35 | 675 / 745 | 538 / 552 | 747 / 775 | 532 / 637 |

Where it goes, phone API 36 cold:
- Android starts the process: about 80 ms after the bind.
- .NET's first managed code: about 170 ms.
- `MainApplication` done (bare MAUI): about 230 ms.
- The Binder handshake and the first answer: under 10 ms more.

Half or more of the time is .NET starting; the bare MAUI app adds 60–130 ms. So with E2, **the first document opens about 0.2–0.7 s later on these emulators**. Real phones will differ, and Android Test should time one on a device. After that the engine is running, and later documents pay nothing.

The heap cap doesn't change start time. The first run (44254177944) had the capped build first, straight after boot, and its numbers were inflated; the clean run runs it second.

**2. Memory.** The engine, idle after its first answer:
- PSS 45–48 MB and RSS 118–160 MB. RSS counts pages shared with Android's zygote; PSS is the fair share.
- Managed heap 4 MB.

The app's own process, for comparison: PSS 93–100 MB on API 35 (the update-WebView screen) and 159–190 MB on API 36 (the Reader).

**3. Pages over a pipe the engine hands back through Binder.** 64 MB in 47–237 ms, **270–1360 MB/s**.
- This needs plain file descriptors on both ends: `ParcelFileDescriptor.DetachFd()`, then a `FileStream` over a `SafeFileHandle`.
- The first try went through the Java stream wrappers (`AutoCloseInputStream` / `AutoCloseOutputStream`) and managed only 1–4 MB/s, with timeouts. **Never move page data through Java streams.**
- One Binder message stays under about 1 MB, so Binder carries only the requests and the pipe handle.

**4. Runaway allocation in the engine.**
- **No heap cap:** the engine grew to about 3 GB resident (3–3.7 GB allocated). Before Android ended it, the low-memory killer ended **43–54 other processes on every emulator, including the launcher and the keyboard**. The engine was ended last, because a process bound by the app in front ranks as visible (`oom_score_adj 100`). The app itself lived. **A crafted file could empty the person's phone of other apps, so a cap is required.**
- **`MONO_GC_PARAMS=max-heap-size=256m`:** the engine got `OutOfMemoryException` at 240 MB, caught it, answered, and kept running. The cap works on Mono for Android.
- **The catch:** that setting comes from the app's environment file, so it applies to **every process of the app, the Reader's own included**. Ways to handle it, for Foundation's design:
  - **(i) One cap for both, high enough for the Reader.** The Reader's own managed heap needs measuring under a large Excel or Word file. Simple, but the engine's cap is then the Reader's.
  - **(ii) A soft cap inside the engine.** The engine watches its own heap or RSS and ends itself past a limit. Works per process, but it doesn't catch a single huge allocation.
  - **(iii) Bind the engine so Android ranks it low** (`BIND_WAIVE_PRIORITY` / `BIND_NOT_PERCEPTIBLE`), so the low-memory killer ends it before other apps. Not measured yet; it also makes the engine easier to end while the person is reading.
  - My recommendation: **(i) plus (ii)**, and I'll measure (iii) when Android's step 4 starts.

**5. Stack overflow.**
- Mono on Android does **not** turn a stack overflow into an exception; `catch` never runs. The engine dies of SIGSEGV. The log shows `Fatal signal 11 (SIGSEGV), code 2 (SEGV_ACCERR)` in the engine (`i.reader:engine`), and the tombstone says `Cause: stack pointer is not in a rw map; likely due to stack overflow.` There is no managed message.
- The same happens on a new thread and on the Binder thread.
- The app learns within 0.2–1.6 s: the Binder call throws, and `binderDied` and `onServiceDisconnected` arrive. **The app's own process lived every time, on all four emulators.**
- So the design's "the engine dies, the app keeps the work and starts a new engine" holds on Android. The app should treat a `DeadObjectException` on a call as "the reader stopped while reading it".

**For Foundation's Android step:**
- `MainApplication` runs in every process of the app, so the engine process must not set up the Reader (Blazor, Chuvadi services). It checks `Application.ProcessName` ending in `:engine` and builds a bare MAUI app, as the probe does.
- Requests go over Binder, with a hand-written Binder in C#; there's no AIDL.
- Files go in as open handles (`ParcelFileDescriptor`), pages come back over the pipe on plain file descriptors, and the app watches `binderDied`.
- The app ends the engine with `Process.KillProcess` on its pid (same user: allowed); this worked in the probe.

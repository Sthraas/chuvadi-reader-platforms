// Platform attributes on <html>, set by PlatformRoot.razor. Only sets attributes; CSS and other
// modules read them (e.g. reader.js picks ⌘ or Ctrl from data-platform).
export function apply(shell, platform, formFactor, input) {
    const root = document.documentElement;
    root.setAttribute('data-shell', shell || 'desktop');
    root.setAttribute('data-platform', platform || 'windows');
    root.setAttribute('data-form-factor', formFactor || 'desktop');
    root.setAttribute('data-input', input || '');
}

// The primary shortcut modifier for this platform: ⌘ on macOS, Ctrl everywhere else.
export function isPrimary(e) {
    return document.documentElement.getAttribute('data-platform') === 'macos'
        ? (e.metaKey === true && e.ctrlKey !== true)
        : (e.ctrlKey === true && e.metaKey !== true);
}

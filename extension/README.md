# CSS Spy Defender - Chrome Extension

A Chrome extension that defends against CSS-only fingerprinting attacks.

## Installation

### From Source (Developer Mode)

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top right)
3. Click **Load unpacked**
4. Select this `extension` folder
5. The extension icon will appear in your toolbar

## Files

| File | Description |
|------|-------------|
| `manifest.json` | Extension configuration (MV3) |
| `content.js` | Core defense logic injected into web pages |
| `background.js` | Service worker for cross-origin CSS fetching |
| `popup.html` | Options UI |
| `popup.js` | Options UI logic |

## Defense Options

### Unconditional Preloading (Core)

Forces all conditional URLs in CSS to load regardless of media queries or container queries. This flattens network request patterns, preventing attackers from inferring browser/OS information.

**How it works:**
1. Parses all CSS from `<style>`, `<link>`, and inline styles
2. Extracts URL candidates: `url()`, `image()`, `image-set()`, `@import`
3. Loads each URL via hidden `<img>` elements
4. Handles CSS escape sequences (e.g., `u\72l` → `url`)

### Math Fingerprinting Block

Disables stylesheets containing dangerous `calc()` with trigonometric functions or `env()` functions that can be exploited for fingerprinting.

**Warning:** May break some websites.

### Container Query Block

Neutralizes all `@container` query rules by forcing `container-type: normal`.

**Warning:** May break responsive layouts.

## Technical Details

- **Manifest Version:** 3 (MV3)
- **Permissions:** `storage`, `activeTab`, `scripting`, `tabs`
- **Host Permissions:** `<all_urls>`
- **Content Script Injection:** `document_start`, all frames, including `about:blank`

## Configuration

Click the extension icon to toggle defense options. Settings are stored via `chrome.storage.sync`.

Default settings:
- Unconditional Preloading: **ON**
- Math Fingerprinting Block: **OFF**
- Container Query Block: **OFF**

## Acknowledgments

This project is based on:
- **"Cascading Spy Sheets"** (NDSS 2025)
- Authors: L. Trampert, D. Weber, L. Gerlach, C. Rossow, M. Schwarz
- Original code: https://github.com/cispa/cascading-spy-sheets/tree/main/mitigation/browser

This Chrome extension adapts the Firefox mitigation for Chrome Manifest V3.

---

## About

CSS Spy Defender is a Chrome extension that protects against CSS-only fingerprinting attacks. Attackers can use CSS features like `@media`, `@container`, and `calc()` to infer browser, OS, and device information without any JavaScript.

### Key Defense: Unconditional Preloading

The extension parses all CSS and force-loads every URL candidate regardless of media queries or conditions. This flattens network request patterns, preventing attackers from distinguishing environments based on which URLs were requested.

### Features

- Unconditional preloading of all CSS URL candidates
- CSS escape sequence decoding (`u\72l` → `url`)
- Cross-origin CSS fetching via service worker
- iframe `srcdoc` / `about:blank` protection
- Optional: Math fingerprinting blocking
- Optional: Container query blocking

### Project Structure
```
CSS_Spy_Defender/
├── extension/       # Chrome extension source
├── eval-chrome/     # Performance evaluation scripts
├── pocs/            # Proof-of-concept attack demos
└── README.md
```

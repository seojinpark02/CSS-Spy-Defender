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

This extension builds upon the **Unconditional Preloading** mitigation proposed in the original paper. The core idea is to parse all CSS and force-load every URL candidate regardless of media queries or conditions, flattening network request patterns.

#### Limitations of the Original Implementation

We identified two bypass techniques not covered by the original Firefox mitigation:

1. **CSS Escape Obfuscation**: Attackers can obfuscate `url()` using CSS hex escapes (e.g., `u\72l` → `url`), evading naive regex-based detection.

2. **iframe srcdoc Bypass**: The original implementation does not inject into `srcdoc` iframes, allowing fingerprinting code to execute unprotected in these contexts.

#### Our Enhancements

| Enhancement | Description |
|-------------|-------------|
| CSS Escape Decoding | `decodeCssEscapes()` normalizes hex escapes before parsing |
| iframe Coverage | `match_about_blank: true` ensures injection into all iframe contexts |
| Cross-Origin Support | Service worker fetches external CSS bypassing CORS restrictions |
| Chrome MV3 Adaptation | Reimplemented for Chrome Manifest V3 architecture |

### Features

- Unconditional preloading of all CSS URL candidates
- CSS escape sequence decoding (`u\72l` → `url`)
- Cross-origin CSS fetching via service worker
- iframe `srcdoc` protection
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

### Disclaimer

This extension was developed for study purposes. Actual usage may cause:
- UI/UX breakage on some websites
- Increased network overhead

Use at your own discretion.

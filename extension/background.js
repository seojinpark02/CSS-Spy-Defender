/**
 * CSS Spy Defender - Background Service Worker (v1.0.0)
 * 
 * The Service Worker can fetch content from any URL without CORS restrictions
 * thanks to host_permissions declared in the manifest.
 */

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || !message.type) return;

    if (message.type === 'fetchCSS') {
        const url = message.url;
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.text();
            })
            .then(css => {
                sendResponse({ success: true, css: css });
            })
            .catch(error => {
                console.log('[CSS Spy Defender] Failed to fetch:', url, error.message);
                sendResponse({ success: false, error: error.message });
            });

        return true;
    }
});

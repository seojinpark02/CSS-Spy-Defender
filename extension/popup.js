/**
 * CSS Spy Defender - Popup Script
 */

document.addEventListener('DOMContentLoaded', () => {
    const optionKeys = ['usePreloading', 'blockContainer', 'blockMathFingerprinting'];
    
    const defaults = {
        usePreloading: true,
        blockContainer: false,
        blockMathFingerprinting: false
    };

    const checkboxes = {};
    for (const key of optionKeys) {
        checkboxes[key] = document.getElementById(key);
    }

    // Load saved settings
    chrome.storage.sync.get(optionKeys, (data) => {
        for (const key of optionKeys) {
            if (checkboxes[key]) {
                checkboxes[key].checked = data[key] ?? defaults[key];
            }
        }
    });

    // Save settings on button click
    document.getElementById('save').addEventListener('click', () => {
        const settings = {};
        for (const key of optionKeys) {
            if (checkboxes[key]) {
                settings[key] = checkboxes[key].checked;
            }
        }

        chrome.storage.sync.set(settings, () => {
            const status = document.getElementById('status');
            status.textContent = 'Settings saved. Reloading page...';

            // Reload the active tab
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                if (tabs[0]) {
                    chrome.tabs.reload(tabs[0].id);
                }
            });

            setTimeout(() => {
                status.textContent = '';
            }, 2000);
        });
    });
});

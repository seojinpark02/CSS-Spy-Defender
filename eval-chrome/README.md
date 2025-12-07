# CSS Spy Defender - Chrome/MV3 Performance Evaluation

This folder contains scripts to measure the performance overhead of CSS Spy Defender extension on Chrome/MV3.

Based on the original Firefox evaluation from "Cascading Spy Sheets" (NDSS 2025), adapted for Chrome Manifest V3 extensions.

## Overview

The evaluation measures:
- **Request Count**: Number of network requests
- **Response Body Size**: Total bytes transferred
- **Navigation Duration**: Time to complete page navigation
- **First Contentful Paint (FCP)**: Time to first content render

By comparing measurements with and without the extension, we can quantify the overhead introduced by CSS Spy Defender's unconditional preloading mechanism.

## Files

```
eval-chrome/
├── measure_overhead_chrome.py   # Main crawling script
├── stats.py                     # Statistics analysis
├── requirements.txt             # Python dependencies
├── tranco_LJ494.csv             # Tranco Top Sites list
└── README.md                    # This file
```

## Setup

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip3 install -r requirements.txt
playwright install chromium
```

### 2. Extension Location

The script expects the extension to be located at `../extension/` (parent directory).

Project structure:
```
CSS_Defender/
├── extension/           # Extension source (manifest.json here)
│   ├── manifest.json
│   ├── content.js
│   ├── background.js
│   ├── popup.html
│   └── popup.js
└── eval-chrome/         # This evaluation folder
    ├── measure_overhead_chrome.py
    └── ...
```

Or modify `EXTENSION_DIR` in `measure_overhead_chrome.py` to point to your extension.

### 3. Prepare Domain List

Ensure `tranco_LJ494.csv` is present in this directory. Format:
```
1,google.com
2,youtube.com
3,facebook.com
...
```

## Running the Evaluation

### Crawl

```bash
python3 measure_overhead_chrome.py
```

This will:
1. Launch Chrome **with** CSS Spy Defender extension
2. Crawl domains from Tranco list, collecting metrics
3. Launch Chrome **without** extension
4. Crawl the same domains again
5. Output three JSON files with results

**Note:** The script runs in headful mode (visible browser window) because Chrome extensions are not fully supported in headless mode.

### Statistics

After crawling completes:

```bash
python3 stats.py
```

This outputs:
- Per-domain differences
- Average/median request count overhead
- Average/median response size overhead
- Navigation duration and FCP differences

## Output Files

| File | Description |
|------|-------------|
| `resultsWithExtension.json` | Measurements with CSS Spy Defender enabled |
| `resultsWithoutExtension.json` | Baseline measurements without extension |
| `correlatedResults.json` | Difference (with - without) for each metric |

### JSON Schema

```json
{
    "https://example.com": {
        "requestCount": 42,
        "responseCount": 40,
        "accumulatedRequestBodySize": 1234,
        "accumulatedResposeBodySize": 567890,
        "navigationDuration": 1234.56,
        "resourceDuration": 123.45,
        "fcp": 456.78
    }
}
```

## Configuration

Edit `measure_overhead_chrome.py` to adjust:

```python
TRANCO_FILE = "tranco_LJ494.csv"  # Domain list file
PAGE_TIMEOUT = 20000              # Page load timeout (ms)
DOMAIN_AMOUNT = 50                # Number of domains to measure
EXTENSION_DIR = Path("...")       # Extension directory path
```

## Differences from Firefox Version

| Aspect | Firefox (Original) | Chrome (This Version) |
|--------|-------------------|----------------------|
| Browser | Firefox | Chromium |
| Extension Install | Manual (about:debugging) | Automatic (--load-extension) |
| Context Type | Browser | Persistent Context |
| Headless Mode | Mixed | Both headful |
| MV Version | MV2 | MV3 |

## Troubleshooting

### Extension not loading
- Ensure `EXTENSION_DIR` points to folder containing `manifest.json`
- Check that the extension has no syntax errors

### Timeout errors
- Increase `PAGE_TIMEOUT` for slow connections
- Some sites may block automated browsers

### Profile issues
- The script automatically cleans up profile directories
- If issues persist, manually delete `.chrome-profile-*` folders

## Expected Results

Based on the paper, unconditional preloading typically causes:
- **Request count increase**: ~128% (due to preloading conditional URLs)
- **Response size increase**: ~142% (depends on CSS complexity)
- **FCP increase**: ~150ms on average

The overhead is a trade-off for privacy protection against CSS-based fingerprinting.

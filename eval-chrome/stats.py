"""
CSS Spy Defender - Statistics Analysis Script

Analyzes the performance overhead by comparing measurements
with and without the extension.

Usage:
    python3 stats.py
"""

import json
import pprint
import numpy as np


def read_json_file(file_path):
    """Read and parse a JSON file."""
    with open(file_path, "r") as file:
        return json.load(file)


def main():
    file_path1 = "resultsWithExtension.json"
    file_path2 = "resultsWithoutExtension.json"

    data1 = read_json_file(file_path1)
    data2 = read_json_file(file_path2)

    diff_keys = [
        "requestCount",
        "responseCount",
        "accumulatedRequestBodySize",
        "accumulatedResposeBodySize",
        "navigationDuration",
        "resourceDuration",
        "fcp",
    ]

    diffs = {}
    urls = set(data1.keys()).intersection(set(data2.keys()))

    for url in urls:
        diffs[url] = {}
        for diff_key in diff_keys:
            if diff_key in data1[url] and diff_key in data2[url]:
                diffs[url][diff_key] = data1[url][diff_key] - data2[url][diff_key]

    print("=" * 60)
    print("Per-Domain Differences (with extension - without extension)")
    print("=" * 60)
    pprint.pprint(diffs)
    
    print(f"\n{'=' * 60}")
    print("Summary Statistics")
    print("=" * 60)
    
    print(f"\nTotal Domains Compared: {len(diffs)}")
    print(f"Skipped (only in one dataset): {len(set(data1.keys()).difference(set(data2.keys())))}")

    # Request Count
    print(f"\n--- Request Count ---")
    avg_req = np.average([data2[url]['requestCount'] for url in urls])
    avg_req_diff = np.average([diffs[url]['requestCount'] for url in urls])
    med_req = np.median([data2[url]['requestCount'] for url in urls])
    med_req_diff = np.median([diffs[url]['requestCount'] for url in urls])
    
    print(f"Average (baseline): {avg_req:.2f}")
    print(f"Average Diff: {avg_req_diff:.2f} ({avg_req_diff/avg_req*100:.2f}% overhead)")
    print(f"Median (baseline): {med_req:.2f}")
    print(f"Median Diff: {med_req_diff:.2f}")

    # Response Body Size
    print(f"\n--- Response Body Size ---")
    avg_size = np.average([data2[url]['accumulatedResposeBodySize'] for url in urls]) / 1000
    avg_size_diff = np.average([diffs[url]['accumulatedResposeBodySize'] for url in urls]) / 1000
    med_size = np.median([data2[url]['accumulatedResposeBodySize'] for url in urls]) / 1000
    med_size_diff = np.median([diffs[url]['accumulatedResposeBodySize'] for url in urls]) / 1000
    
    print(f"Average (baseline): {avg_size:.2f} KB")
    print(f"Average Diff: {avg_size_diff:.2f} KB ({avg_size_diff/avg_size*100:.2f}% overhead)")
    print(f"Median (baseline): {med_size:.2f} KB")
    print(f"Median Diff: {med_size_diff:.2f} KB")

    # Navigation Duration (if available)
    nav_urls = [url for url in urls if 'navigationDuration' in diffs[url]]
    if nav_urls:
        print(f"\n--- Navigation Duration ---")
        avg_nav = np.average([data2[url]['navigationDuration'] for url in nav_urls])
        avg_nav_diff = np.average([diffs[url]['navigationDuration'] for url in nav_urls])
        med_nav = np.median([data2[url]['navigationDuration'] for url in nav_urls])
        med_nav_diff = np.median([diffs[url]['navigationDuration'] for url in nav_urls])
        
        print(f"Average (baseline): {avg_nav:.2f} ms")
        print(f"Average Diff: {avg_nav_diff:.2f} ms")
        print(f"Median (baseline): {med_nav:.2f} ms")
        print(f"Median Diff: {med_nav_diff:.2f} ms")

    # FCP (if available)
    fcp_urls = [url for url in urls if 'fcp' in diffs[url]]
    if fcp_urls:
        print(f"\n--- First Contentful Paint (FCP) ---")
        avg_fcp = np.average([data2[url]['fcp'] for url in fcp_urls])
        avg_fcp_diff = np.average([diffs[url]['fcp'] for url in fcp_urls])
        med_fcp = np.median([data2[url]['fcp'] for url in fcp_urls])
        med_fcp_diff = np.median([diffs[url]['fcp'] for url in fcp_urls])
        
        print(f"Average (baseline): {avg_fcp:.2f} ms")
        print(f"Average Diff: {avg_fcp_diff:.2f} ms")
        print(f"Median (baseline): {med_fcp:.2f} ms")
        print(f"Median Diff: {med_fcp_diff:.2f} ms")


if __name__ == "__main__":
    main()

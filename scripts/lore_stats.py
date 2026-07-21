#!/usr/bin/env python3
"""
Print statistics about the Packy lorebook.

Usage: python scripts/lore_stats.py [path_to_lorebook.json]
Default: data/lorebook/packy_lorebook_structured.json
"""

import json
import sys
import os


def print_lore_stats(lorebook_path):
    """
    Print statistics about the lorebook.

    Args:
        lorebook_path: Path to the lorebook JSON file
    """
    with open(lorebook_path, "r", encoding="utf-8") as f:
        lorebook = json.load(f)

    # Extract data
    categories = lorebook.get("categories", {})

    # Calculate stats
    total_categories = len(categories)
    total_entries = sum(len(entries) for entries in categories.values())

    print("\n" + "=" * 60)
    print("PACKY LOREBOOK STATISTICS")
    print("=" * 60)

    # Total categories
    print(f"\nTotal Categories: {total_categories}")

    # Total entries
    print(f"Total Entries: {total_entries}")

    # Entries per category (sorted descending)
    print("\nEntries per Category (sorted by count):")
    print("-" * 60)

    category_counts = [(cat, len(entries)) for cat, entries in categories.items()]
    category_counts.sort(key=lambda x: x[1], reverse=True)

    for category, count in category_counts:
        print(f"  {category:.<45} {count:>4} entries")

    # Mood distribution (if available in entries)
    # This would require parsing the text or having mood metadata
    print("\n" + "=" * 60)


def main():
    # Determine paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    lorebook_path = os.path.join(project_root, "data/lorebook/packy_lorebook_structured.json")

    # Get lorebook path from command line if provided
    if len(sys.argv) > 1:
        lorebook_path = sys.argv[1]

    print_lore_stats(lorebook_path)


if __name__ == "__main__":
    main()

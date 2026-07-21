#!/usr/bin/env python3
"""
Merge new lore entries into the main Packy lorebook.

Usage: python scripts/merge_lore.py [path_to_new_entries.json]
Default: data/lorebook/new_lore_entries.json
"""

import json
import sys
import os
import tempfile


def merge_lore_entries(lorebook_path, new_entries_path):
    """
    Merge new lore entries into the main lorebook.

    Args:
        lorebook_path: Path to the main lorebook JSON file
        new_entries_path: Path to the new entries JSON file

    Returns:
        Tuple of (number of entries merged, number of categories affected)
    """
    # Read the main lorebook
    with open(lorebook_path, "r", encoding="utf-8") as f:
        lorebook = json.load(f)

    # Read the new entries
    with open(new_entries_path, "r", encoding="utf-8") as f:
        new_entries = json.load(f)

    # Initialize categories if they don't exist
    if "categories" not in lorebook:
        lorebook["categories"] = {}
    if "stats" not in lorebook:
        lorebook["stats"] = {}

    # Track categories affected
    categories_affected = set()
    entries_merged = 0

    # Process each new entry
    for entry in new_entries:
        category = entry.get("category")
        text = entry.get("text")

        if not category or not text:
            continue

        # Create category if it doesn't exist
        if category not in lorebook["categories"]:
            lorebook["categories"][category] = []

        # Append the text to the category
        lorebook["categories"][category].append(text)
        categories_affected.add(category)
        entries_merged += 1

    # Update stats
    total_entries = sum(len(entries) for entries in lorebook["categories"].values())
    lorebook["stats"]["total_entries"] = total_entries

    # Write back to file atomically using a temp file
    # Get the directory of the target file
    target_dir = os.path.dirname(lorebook_path)

    # Create temp file in the same directory (ensures same filesystem)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=target_dir, delete=False, suffix=".json", encoding="utf-8"
    ) as tmp_file:
        json.dump(lorebook, tmp_file, indent=2, ensure_ascii=False)
        tmp_path = tmp_file.name

    # Atomic rename
    os.replace(tmp_path, lorebook_path)

    return entries_merged, len(categories_affected)


def main():
    # Determine paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    lorebook_path = os.path.join(project_root, "data/lorebook/packy_lorebook_structured.json")

    # Get new entries path from command line or use default
    if len(sys.argv) > 1:
        new_entries_path = sys.argv[1]
    else:
        new_entries_path = os.path.join(project_root, "data/lorebook/new_lore_entries.json")

    # Merge the entries
    entries_merged, categories_affected = merge_lore_entries(lorebook_path, new_entries_path)

    # Print result
    print(f"Merged {entries_merged} entries into {categories_affected} categories.")


if __name__ == "__main__":
    main()

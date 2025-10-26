"""
Script to clean CSV file by removing newlines from field values
"""

import csv

input_file = "padel_posts_dataset_refined.csv"
output_file = "padel_posts_dataset_cleaned.csv"

with open(input_file, "r", encoding="utf-8-sig", newline="") as fin, open(
    output_file, "w", encoding="utf-8", newline=""
) as fout:

    reader = csv.DictReader(fin)
    writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)

    writer.writeheader()

    count = 0
    for row in reader:
        # Replace newlines and multiple spaces in all fields
        for key in row:
            if row[key]:
                # Replace newlines with spaces
                row[key] = row[key].replace("\n", " ").replace("\r", " ")
                # Replace multiple spaces with single space
                while "  " in row[key]:
                    row[key] = row[key].replace("  ", " ")
                # Strip leading/trailing whitespace
                row[key] = row[key].strip()

        writer.writerow(row)
        count += 1

print(f"✓ Cleaned {count} rows")
print(f"✓ Output saved to: {output_file}")
print(f"\nTo use the cleaned file, either:")
print(f"1. Rename it to replace the original")
print(f"2. Update populate_from_csv.py to use '{output_file}'")

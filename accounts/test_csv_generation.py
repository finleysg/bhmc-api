#!/usr/bin/env python
"""
Test script to generate CSV from the sample Excel file.
This script can be run from the Django project root.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('/home/stuart/code/bhmc-api')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bhmc.settings')
django.setup()

from accounts.imports import generate_skins_csv_from_excel

def test_csv_generation():
    """Test CSV generation with the sample file"""
    
    # Path to the sample file
    file_path = '/home/stuart/code/bhmc-api/files/BHMC LG_LN 2025-05-14 Leaderboard.xls'
    
    print("Testing CSV generation from sample Excel file...")
    print(f"Input file: {file_path}")
    print("=" * 60)
    
    try:
        # Generate CSV data
        csv_data, failures = generate_skins_csv_from_excel(file_path)
        
        if failures:
            print("Errors encountered during CSV generation:")
            for i, failure in enumerate(failures, 1):
                print(f"  {i}. {failure}")
            print()
        
        if csv_data:
            print(f"CSV generation successful! Generated {len(csv_data)} characters of CSV data.")
            
            # Save CSV to file
            output_file = '/home/stuart/code/bhmc-api/generated_skins.csv'
            with open(output_file, 'w', newline='') as f:
                f.write(csv_data)
            
            print(f"CSV data saved to: {output_file}")
            print()
            print("CSV content preview:")
            print("-" * 40)
            
            # Show first 20 lines for preview
            lines = csv_data.split('\n')
            for i, line in enumerate(lines[:20]):
                if line.strip():
                    print(f"{i+1:2d}: {line}")
            
            if len(lines) > 20:
                print(f"... and {len(lines) - 20} more lines")
                
            print("-" * 40)
            print(f"Total lines in CSV: {len([line for line in lines if line.strip()])}")
            
        else:
            print("No CSV data generated.")
            
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_csv_generation()

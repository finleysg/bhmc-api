"""
Test script for Wednesday skins import functionality.

This script demonstrates how to use the WednesdaySkinsImporter class to:
1. Generate CSV data from Excel files
2. Import skins data from CSV
"""

from accounts.imports import (
    WednesdaySkinsImporter, 
    generate_skins_csv_from_excel, 
    import_skins_from_csv,
    SkinImportError
)
from events.models import Event

def test_csv_generation():
    """
    Test generating CSV data from Excel file.
    
    Note: This requires an actual Excel file to run successfully.
    """
    
    # Example usage of CSV generation
    importer = WednesdaySkinsImporter()
    
    # Replace with actual file path
    csv_data, failures = importer.generate_csv_from_excel(
        file_path="/path/to/BHMC LG_LN 2025-05-14 Leaderboard.xls"
    )
    
    if not failures:
        print("CSV generation completed successfully!")
        print(f"Generated CSV data ({len(csv_data)} characters):")
        print("=" * 50)
        print(csv_data)
        print("=" * 50)
    else:
        print("CSV generation completed with errors:")
        for failure in failures:
            print(f"  - {failure}")

def test_csv_import():
    """
    Test importing skins from CSV data.
    
    Note: This requires a valid event ID and CSV data.
    """
    
    # Sample CSV data for testing
    sample_csv = """player_name,player_ghin,course,hole_number,value,details
John Smith,1234567,east,7,38.00,Birdie on 7 in Flight 1
Jane Doe,7654321,west,9,38.00,Eagle on 9 in Flight 2
Bob Johnson,,north,4,17.00,Birdie on 4 in Flight 1"""
    
    try:
        # Get an event (replace with actual event ID)
        event = Event.objects.get(id=1)
        
        # Import the CSV data
        failures = import_skins_from_csv(event, sample_csv)
        
        if not failures:
            print("CSV import completed successfully!")
        else:
            print("CSV import completed with errors:")
            for failure in failures:
                print(f"  - {failure}")
                
    except Event.DoesNotExist:
        print("Event with ID 1 does not exist. Please update the event ID.")
    except Exception as e:
        print(f"Unexpected error: {e}")

def test_full_workflow():
    """
    Test the complete workflow: Excel -> CSV -> Import
    """
    
    print("Testing full workflow...")
    print("=" * 40)
    
    # Step 1: Generate CSV from Excel
    print("Step 1: Generating CSV from Excel file...")
    csv_data, failures = generate_skins_csv_from_excel(
        "/path/to/BHMC LG_LN 2025-05-14 Leaderboard.xls"
    )
    
    if failures:
        print("CSV generation failed:")
        for failure in failures:
            print(f"  - {failure}")
        return
    
    print(f"CSV generated successfully ({len(csv_data)} characters)")
    
    # Step 2: Import CSV data
    print("\nStep 2: Importing CSV data...")
    try:
        event = Event.objects.get(id=1)  # Replace with actual event ID
        
        failures = import_skins_from_csv(event, csv_data)
        
        if not failures:
            print("Import completed successfully!")
        else:
            print("Import completed with errors:")
            for failure in failures:
                print(f"  - {failure}")
                
    except Event.DoesNotExist:
        print("Event with ID 1 does not exist. Please update the event ID.")
    except Exception as e:
        print(f"Unexpected error during import: {e}")

def test_individual_methods():
    """
    Test individual methods of the WednesdaySkinsImporter class.
    """
    
    importer = WednesdaySkinsImporter()
    
    # Test detail parsing
    print("Testing detail parsing:")
    print("-" * 25)
    
    test_details = [
        ("Birdie on 7", 1, "38.00", "Flight 1"),
        ("Birdie on 4, Par on 7", 2, "34.00", "Flight 2"),
        ("Eagle on 9", 1, "38.00", "Flight 1"),
    ]
    
    from decimal import Decimal
    
    for details, count, purse, flight in test_details:
        individual_skins = importer._parse_skin_details(
            details, count, Decimal(purse), flight
        )
        print(f"Input: '{details}' ({count} skins, ${purse})")
        print(f"Output: {individual_skins}")
        print()

if __name__ == "__main__":
    print("Wednesday Skins Import Test Script")
    print("=" * 40)
    
    # Uncomment to run tests (make sure to update file paths and IDs)
    # test_csv_generation()
    # test_csv_import()
    # test_full_workflow()
    test_individual_methods()
    
    print("\nTo use this script:")
    print("1. Update the file paths to point to your Excel files")
    print("2. Update event_id with valid database ID")
    print("3. Uncomment the test function calls above")
    print("4. Run: python manage.py shell < accounts/test_imports.py")
    print("\nExample usage in Django shell:")
    print(">>> from accounts.imports import generate_skins_csv_from_excel, import_skins_from_csv")
    print(">>> from events.models import Event")
    print(">>> csv_data, errors = generate_skins_csv_from_excel('/path/to/file.xls')")
    print(">>> event = Event.objects.get(id=1)")
    print(">>> failures = import_skins_from_csv(event, csv_data)")

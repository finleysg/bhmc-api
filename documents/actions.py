"""
Admin actions for Document model
"""
from django.http import HttpResponse
from django.contrib import messages
import os
import tempfile
from accounts.imports import WednesdaySkinsImporter


def generate_skins_csv(modeladmin, request, queryset):
    """
    Generate skins CSV from leaderboard documents
    """
    generated_files = []
    errors = []
    
    for document in queryset:
        # Only process documents with "Leaderboard" in the title
        if "leaderboard" not in document.title.lower():
            errors.append(f"Skipped '{document.title}' - not a leaderboard document")
            continue
            
        if not document.file:
            errors.append(f"Skipped '{document.title}' - no file attached")
            continue
        
        # Check if file has a valid Excel extension
        original_filename = document.file.name.lower()
        if not (original_filename.endswith('.xls') or original_filename.endswith('.xlsx')):
            errors.append(f"Skipped '{document.title}' - not an Excel file (.xls or .xlsx)")
            continue
            
        try:
            temp_file_path = None
            try:
                # Determine file extension from the original file
                if original_filename.endswith('.xls'):
                    file_suffix = '.xls'
                elif original_filename.endswith('.xlsx'):
                    file_suffix = '.xlsx'
                else:
                    file_suffix = '.xlsx'
                
                # Create a temporary file with the correct extension
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as temp_file:
                    # Download the file content
                    with document.file.open('rb') as source_file:
                        temp_file.write(source_file.read())
                    file_path = temp_file.name
                    temp_file_path = temp_file.name
            except Exception as download_error:
                errors.append(f"Could not download file for '{document.title}': {str(download_error)}")
                continue
            
            try:
                # Initialize the importer and generate CSV
                importer = WednesdaySkinsImporter()
                csv_data, import_errors = importer.generate_csv_from_excel(file_path)
                
                if import_errors:
                    errors.extend([f"{document.title}: {error}" for error in import_errors])
            finally:
                # Clean up temporary file if we created one
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            
            if csv_data:
                # Create a filename based on the document title
                safe_title = "".join(c for c in document.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                csv_filename = f"{safe_title}_skins.csv"
                
                # If only one document selected, return the CSV file directly
                if len(queryset) == 1 and not errors:
                    response = HttpResponse(csv_data, content_type='text/csv')
                    response['Content-Disposition'] = f'attachment; filename="{csv_filename}"'
                    return response
                
                generated_files.append(csv_filename)
            
        except Exception as e:
            errors.append(f"Error processing '{document.title}': {str(e)}")
    
    # Show results
    if generated_files:
        success_msg = f"Generated skins CSV for: {', '.join(generated_files)}"
        modeladmin.message_user(request, success_msg, messages.SUCCESS)
    
    if errors:
        error_msg = "Errors occurred: " + "; ".join(errors)
        modeladmin.message_user(request, error_msg, messages.ERROR)
    
    if not generated_files and not errors:
        modeladmin.message_user(request, "No leaderboard documents found to process", messages.WARNING)


generate_skins_csv.short_description = "Generate skins CSV"


def generate_and_import_skins(modeladmin, request, queryset):
    """
    Generate skins CSV from leaderboard documents and import the data into the database
    """
    imported_count = 0
    errors = []
    processed_documents = []
    
    for document in queryset:
        # Only process documents with "Leaderboard" in the title
        if "leaderboard" not in document.title.lower():
            errors.append(f"Skipped '{document.title}' - not a leaderboard document")
            continue
            
        if not document.file:
            errors.append(f"Skipped '{document.title}' - no file attached")
            continue
        
        # Check if file has a valid Excel extension
        original_filename = document.file.name.lower()
        if not (original_filename.endswith('.xls') or original_filename.endswith('.xlsx')):
            errors.append(f"Skipped '{document.title}' - not an Excel file (.xls or .xlsx)")
            continue
            
        # Check if document has an associated event (required for import)
        if not document.event:
            errors.append(f"Skipped '{document.title}' - no event associated (required for import)")
            continue
            
        try:
            temp_file_path = None
            try:
                # Determine file extension from the original file
                if original_filename.endswith('.xls'):
                    file_suffix = '.xls'
                elif original_filename.endswith('.xlsx'):
                    file_suffix = '.xlsx'
                else:
                    file_suffix = '.xlsx'
                
                # Create a temporary file with the correct extension
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as temp_file:
                    # Download the file content
                    with document.file.open('rb') as source_file:
                        temp_file.write(source_file.read())
                    file_path = temp_file.name
                    temp_file_path = temp_file.name
            except Exception as download_error:
                errors.append(f"Could not download file for '{document.title}': {str(download_error)}")
                continue
            
            try:
                # Initialize the importer and generate CSV
                importer = WednesdaySkinsImporter()
                csv_data, import_errors = importer.generate_csv_from_excel(file_path)
                
                if import_errors:
                    errors.extend([f"{document.title}: {error}" for error in import_errors])
                
                if csv_data:
                    # Import the CSV data into the database
                    import_result_errors = importer.import_csv_data(document.event, csv_data)
                    
                    if import_result_errors:
                        errors.extend([f"{document.title} import: {error}" for error in import_result_errors])
                    else:
                        imported_count += importer.processed_count
                        processed_documents.append(document.title)
                
            finally:
                # Clean up temporary file if we created one
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            
        except Exception as e:
            errors.append(f"Error processing '{document.title}': {str(e)}")
    
    # Show results
    if processed_documents:
        success_msg = f"Successfully imported skins from {len(processed_documents)} document(s): {', '.join(processed_documents)}. Total skins imported: {imported_count}"
        modeladmin.message_user(request, success_msg, messages.SUCCESS)
    
    if errors:
        error_msg = "Errors occurred: " + "; ".join(errors)
        modeladmin.message_user(request, error_msg, messages.ERROR)
    
    if not processed_documents and not errors:
        modeladmin.message_user(request, "No leaderboard documents found to process", messages.WARNING)


generate_and_import_skins.short_description = "Import skins"

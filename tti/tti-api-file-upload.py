import streamlit as st
import requests
import time
import os
import json
from datetime import datetime
import pytz # For timezone conversion
import pandas as pd # Import pandas for DataFrame operations
import io # To handle file data for Excel export

st.set_page_config(page_title="API File Manager", page_icon="📁", layout="wide")

st.markdown("""
<style>
.main-header { font-size: 2.5rem; color: #1f77b4; margin-bottom: 2rem; }
.upload-section { background: #f8f9fa; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }
.api-section { background: #e8f4fd; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }

/* Custom CSS to change the file size limit text */
[data-testid="stFileUploaderDropzoneInstructions"] > div > small {
    display: none; /* Hide the original text */
}
# [data-testid="stFileUploaderDropzoneInstructions"] > div::after {
#     content: 'Limit 10MB per file'; /* Add your custom text */
#     display: block; /* Make sure it's visible */
#     font-size: 0.9em; /* Adjust font size if needed */
#     color: #888; /* Adjust color if needed */
#     margin-top: 5px; /* Add some spacing if needed */
# }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">📁 API File Manager</h1>', unsafe_allow_html=True)

# Define your base API URL here (for both upload and results)
# IMPORTANT: Use the root of your API Gateway deployment, e.g., "https://1234.execute-api.ap-southeast-4.amazonaws.com/prod"
# The /prod/upload and /prod/results paths will be appended.
BASE_API_ROOT_URL = "https://atgk2xx0si.execute-api.ap-southeast-1.amazonaws.com/dev" # <--- UPDATE THIS TO YOUR API GATEWAY ROOT URL
S3_BUCKET_NAME = "tti-ocr-ap-southeast-1/" # Your S3 Bucket Name
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# Initialize session state variables
if 'uploaded_document_ids' not in st.session_state: # Changed to a list
    st.session_state.uploaded_document_ids = []
if 'analysis_results_list' not in st.session_state: # Changed to a list of results
    st.session_state.analysis_results_list = []
if 'fetch_retries_count' not in st.session_state:
    st.session_state.fetch_retries_count = 0

# Function to format timestamp (e.g., Classified At)
def format_timestamp(ms_timestamp):
    if ms_timestamp:
        try:
            # Convert string timestamp to float before division
            dt_utc = datetime.fromtimestamp(float(ms_timestamp) / 1000, tz=pytz.utc)
            dt_jakarta = dt_utc.astimezone(JAKARTA_TZ)
            return dt_jakarta.strftime("%d/%m/%Y %H:%M:%S")
        except (ValueError, TypeError) as e:
            return "Invalid Timestamp"
    return "N/A"

# New function to standardize delivery date format
def format_delivery_date(date_string):
    if not date_string:
        return ""
    try:
        # Attempt to parse the date string. errors='coerce' turns unparseable dates into NaT (Not a Time).
        parsed_date = pd.to_datetime(date_string, errors='coerce')
        if pd.isna(parsed_date):
            return date_string # Return original string if parsing failed
        return parsed_date.strftime("%d/%m/%Y") # Format to DD/MM/YYYY
    except Exception:
        return date_string # Fallback in case of unexpected errors

with st.container():
    st.markdown('<div class="api-section">', unsafe_allow_html=True)
    st.subheader("🔗 API Configuration")
    st.write(f"**Base API Endpoint:** `{BASE_API_ROOT_URL}`")
    st.write(f"**Target S3 Bucket:** `{S3_BUCKET_NAME}`")
    
    st.markdown("---")
    st.markdown("##### S3 Folder Configuration")
    user_folder_name = st.text_input(
        "", 
        placeholder="Enter the S3 folder name (e.g., 'invoices', 'reports')",
        label_visibility="collapsed",
        help="This will be the sub-folder within your S3 bucket (e.g., 'invoices', 'reports')."
    )
    
    # Ensure user_folder_name has a trailing slash if not empty
    if user_folder_name and not user_folder_name.endswith('/'):
        user_folder_name += '/'

    st.markdown('</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📤 File Upload")
    uploaded_files = st.file_uploader( # Changed to uploaded_files (plural)
        "", 
        label_visibility="collapsed", 
        accept_multiple_files=True # Now accepts multiple files
    )
    
    if uploaded_files: # Check if the list is not empty
        st.success(f"✅ Selected {len(uploaded_files)} file(s).") # Updated message
        
        # --- NEW VALIDATION LOGIC START ---
        if not user_folder_name: # Check if folder name is empty
            st.error("❌ Please Enter The Customer Name")
            uploaded_files = [] # Clear selected files to block further processing
        # --- NEW VALIDATION LOGIC END ---

# Main action buttons
if uploaded_files: # Check if there are files to process
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        if st.button("🚀 POST Upload", type="primary", use_container_width=True):
            st.session_state.analysis_results_list = [] # Clear previous results
            st.session_state.uploaded_document_ids = [] # Clear previous document IDs
            st.session_state.fetch_retries_count = 0 # Reset fetch retries

            if not uploaded_files: # Double check if validation cleared files
                st.error("Please select files to upload after entering the customer name.")
            elif not user_folder_name:
                st.error("Please enter the customer name before uploading files.")
            else:
                with st.spinner("Uploading files..."):
                    upload_success_count = 0
                    for uploaded_file in uploaded_files: # Loop through each file
                        filename = uploaded_file.name
                        current_document_id = f"{user_folder_name}{filename}"
                        api_upload_url = f"{BASE_API_ROOT_URL}/{S3_BUCKET_NAME}{current_document_id}"
                        
                        st.info(f"Uploading '{uploaded_file.name}' to `{api_upload_url}`...")
                        try:
                            response = requests.put(api_upload_url, data=uploaded_file.getvalue())
                            
                            if response.status_code == 200:
                                st.success(f"✅ Upload successful for '{uploaded_file.name}'! Status: {response.status_code}")
                                st.session_state.uploaded_document_ids.append(current_document_id) # Add to list
                                upload_success_count += 1
                            else:
                                st.warning(f"⚠️ Upload failed for '{uploaded_file.name}'. Status: {response.status_code}")
                            
                            with st.expander(f"📋 Response Details for '{uploaded_file.name}'"):
                                try:
                                    st.json(response.json())
                                except ValueError:
                                    st.text(response.text)
                        except Exception as e:
                            st.error(f"❌ Upload failed for '{uploaded_file.name}': {e}")
                    
                    if upload_success_count > 0:
                        st.success(f"Successfully uploaded {upload_success_count} of {len(uploaded_files)} files.")
                        # --- NEW: Wait 15 seconds after successful upload batch ---
                        st.info("Waiting 15 seconds for backend processing to initiate for all uploaded files...")
                        time.sleep(15) 
                        st.info("Wait complete. Attempting to fetch results...")
                        # --- END NEW ---
                    else:
                        st.error("No files were successfully uploaded.")

# Section to retrieve and display results
if st.session_state.uploaded_document_ids: # Check if there are any IDs to fetch results for
    st.markdown("---")
    st.subheader("📊 Document Analysis Results")
    
    # --- DISABLED AUTO-REFRESH ---
    # main_refresh_interval_seconds = 10 
    # if (time.time() - st.session_state.last_refresh_time) > main_refresh_interval_seconds:
    #     st.session_state.last_refresh_time = time.time() 
    #     st.rerun() 

    if st.button("🔄 Retrieve Analysis Results Now", use_container_width=True):
        st.session_state.analysis_results_list = [] # Clear previous
        st.session_state.fetch_retries_count = 0 # Reset fetch retries for manual fetch
        # The fetching logic below will run

    # Parameters for fetching retries within a single streamlit rerun
    max_fetch_retries = 20 # Maximum attempts to fetch results if 404
    fetch_retry_interval_seconds = 5 # Time to wait between fetch retries (if 404)
    
    # Only fetch if results are not already present (for all docs)
    if not st.session_state.analysis_results_list or len(st.session_state.analysis_results_list) < len(st.session_state.uploaded_document_ids):
        st.info(f"Attempting to fetch results for {len(st.session_state.uploaded_document_ids)} document(s).")
        fetch_placeholder = st.empty() # Create a placeholder for dynamic messages during fetch

        # This will hold newly fetched results
        newly_fetched_results = []
        # Keep track of documents that were successfully fetched in previous runs
        existing_fetched_results_map = {res.get('documentId'): res for res in st.session_state.analysis_results_list}

        documents_still_pending = []

        for doc_id_to_fetch in st.session_state.uploaded_document_ids:
            # If results for this document are already in our session state, use them
            if doc_id_to_fetch in existing_fetched_results_map:
                newly_fetched_results.append(existing_fetched_results_map[doc_id_to_fetch])
                continue # Skip fetching
            
            results_api_url = f"{BASE_API_ROOT_URL}/results/{doc_id_to_fetch}"
            
            with fetch_placeholder.container(): # Use container to clear previous messages for current file
                with st.spinner(f"Fetching '{os.path.basename(doc_id_to_fetch)}' results... (Attempt {st.session_state.fetch_retries_count + 1}/{max_fetch_retries})"):
                    current_doc_fetched = False
                    for i in range(st.session_state.fetch_retries_count, max_fetch_retries): # Continue from last retry count
                        try:
                            response = requests.get(results_api_url)
                            
                            if response.status_code == 200:
                                st.success(f"✅ Results found for '{os.path.basename(doc_id_to_fetch)}'!")
                                newly_fetched_results.append(response.json())
                                current_doc_fetched = True
                                break # Exit inner retry loop
                            elif response.status_code == 404:
                                st.info(f"Analysis for '{os.path.basename(doc_id_to_fetch)}' still in progress. Retrying in {fetch_retry_interval_seconds}s... ({i+1}/{max_fetch_retries})")
                                time.sleep(fetch_retry_interval_seconds)
                            else:
                                st.error(f"❌ Error fetching results for '{os.path.basename(doc_id_to_fetch)}': Status {response.status_code}")
                                with st.expander("Response Details"):
                                    st.text(response.text)
                                break # Exit inner retry loop on other errors
                        except Exception as e:
                            st.error(f"❌ Network or API error during fetch for '{os.path.basename(doc_id_to_fetch)}': {e}")
                            break # Exit inner retry loop on network error
                    
                    if not current_doc_fetched:
                        documents_still_pending.append(doc_id_to_fetch)
                        # Only show warning if max retries reached for this doc
                        if st.session_state.fetch_retries_count >= max_fetch_retries:
                            st.warning(f"⚠️ Max retries reached for '{os.path.basename(doc_id_to_fetch)}'. Analysis might still be in progress or failed.")
            
        st.session_state.analysis_results_list = newly_fetched_results # Update the list of fetched results
        if documents_still_pending:
            st.info(f"Still waiting for results for {len(documents_still_pending)} document(s).")
            st.session_state.fetch_retries_count += 1 # Increment only once per batch of docs
        else:
            st.session_state.fetch_retries_count = 0 # Reset if all are done
        fetch_placeholder.empty() # Clear the overall spinner/messages
                
    if st.session_state.analysis_results_list: # Loop through the list of results
        st.markdown("---")
        st.subheader("📋 Consolidated Document Data")

        all_combined_table_data = [] # This list will hold rows from ALL documents

        for doc_result in st.session_state.analysis_results_list:
            # Prepare header fields for the combined table
            doc_id = doc_result.get('documentId', 'N/A')
            classification = doc_result.get('classifiedData', 'N/A')
            timestamp_ms = doc_result.get('classificationTimestamp')
            classified_at = format_timestamp(timestamp_ms)

            structured_fields = doc_result.get('structuredFields', {})
            
            invoice_no = structured_fields.get('InvoiceNumber', 'N/A')
            po_no = structured_fields.get('PONo', 'N/A')
            tax_no = structured_fields.get('TaxNo', 'N/A')

            # Get item details (list fields)
            item_name_list = structured_fields.get('ItemName', [])
            qty_inbound_list = structured_fields.get('Quantity', [])
            qty_outbound_list = ['' for _ in range(len(qty_inbound_list))] # New empty column
            unit_price_list = structured_fields.get('UnitPrice', [])
            delivery_order_number_list = structured_fields.get('DeleveryOrderNumber', [])
            
            # Apply format_delivery_date to each item in the list
            raw_delivery_dates = structured_fields.get('DeleveryOrderDate', [])
            formatted_delivery_dates = [format_delivery_date(date_str) for date_str in raw_delivery_dates]


            # --- CREATE COMBINED DATA FOR CURRENT DOCUMENT'S DATAFRAME ---
            max_rows_doc = max(len(qty_inbound_list), len(unit_price_list), len(item_name_list))
            if max_rows_doc == 0:
                max_rows_doc = 1 # Ensures at least one row for header info even if no items

            for i in range(max_rows_doc):
                row = {
                    "Document ID": doc_id,
                    "Classification": classification,
                    "Classified At": classified_at,
                    "Invoice Number": invoice_no,
                    "PO Number": po_no,
                    "Tax Number": tax_no,
                    "ItemName": item_name_list[i] if i < len(item_name_list) else "",
                    "Qty Inbound": qty_inbound_list[i] if i < len(qty_inbound_list) else "",
                    "Qty Outbound": qty_outbound_list[i] if i < len(qty_outbound_list) else "",
                    "UnitPrice": unit_price_list[i] if i < len(unit_price_list) else "",
                    "DeleveryOrderNumber": delivery_order_number_list[i] if i < len(delivery_order_number_list) else "",
                    "Date Of Delivery": formatted_delivery_dates[i] if i < len(formatted_delivery_dates) else "" # Use formatted dates
                }
                all_combined_table_data.append(row) # Add row to the master list

        # --- DISPLAY THE SINGLE CONSOLIDATED TABLE FOR ALL DOCUMENTS ---
        if all_combined_table_data:
            df_combined = pd.DataFrame(all_combined_table_data)
            
            desired_columns_order = [
                "Document ID", "Classification", "Classified At",
                "Invoice Number", "PO Number", "Tax Number",
                "ItemName", "Qty Inbound", "Qty Outbound", "UnitPrice",
                "DeleveryOrderNumber", "Date Of Delivery"
            ]
            
            # Filter and reorder columns that actually exist in the DataFrame
            existing_ordered_columns = [col for col in desired_columns_order if col in df_combined.columns]
            df_combined = df_combined[existing_ordered_columns]

            st.dataframe(df_combined, use_container_width=True)

            # Add download button for the single combined table
            csv_data = df_combined.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="Download All Consolidated Data as CSV",
                data=csv_data,
                file_name=f"all_documents_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("No consolidated data available for display.")

        # --- DISPLAY RAW JSON AND OTHER SECTIONS PER DOCUMENT ---
        st.markdown("---")
        st.subheader("Raw JSON and Other Details (Per Document)")
        for doc_result in st.session_state.analysis_results_list:
            st.markdown(f"**Details for: `{doc_result.get('documentId', 'Unknown Document')}`**")
            
            with st.expander("View Raw JSON Data"):
                st.json(doc_result) # Display raw JSON for this specific document

            # Display Parsed Table Markdown (will show "No generic tables extracted" as expected)
            parsed_tables = doc_result.get('ParsedTablesMarkdown', [])
            if parsed_tables:
                st.markdown("---")
                st.subheader("📊 Parsed Tables (Markdown)")
                for i, table_md in enumerate(parsed_tables):
                    st.write(f"**Table {i+1}:**")
                    st.markdown(table_md) # Streamlit renders Markdown directly
                    st.markdown("---")
            else:
                st.info("No generic tables extracted or parsed for this document.")

            # Display Queries (will show "No queries found" as expected)
            queries = doc_result.get('Queries', {})
            if queries:
                st.markdown("---")
                st.subheader("🔍 Query Results")
                for alias, answer in queries.items():
                    st.write(f"- **{alias}:** {answer}")
            else:
                st.info("No queries found for this document.")
            
            st.markdown("---") # Separator between document results
    else:
        st.info("Upload documents to see analysis results here.")

if not uploaded_files: # Changed condition to uploaded_files
    st.info("💡 Please select file(s) to upload")
elif not user_folder_name:
    st.info("💡 Please enter an S3 folder name.")

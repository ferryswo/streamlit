import streamlit as st
import requests
import time
import os
import json
from datetime import datetime
import pytz # For timezone conversion
import pandas as pd # Import pandas for DataFrame operations

st.set_page_config(page_title="API File Manager", page_icon="📁", layout="wide")

st.markdown("""
<style>
.main-header { font-size: 2.5rem; color: #1f77b4; margin-bottom: 2rem; }
.upload-section { background: #f8f9fa; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }
.api-section { background: #e8f4fd; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }

/* Custom CSS to change the file size limit text */
[data-testid="stFileUploaderDropzoneInstructions"] > div > small {
    display: none;
    color: transparent;/* Hide the original text */
}
[data-testid="stFileUploaderDropzoneInstructions"] > div::after {
    content: 'Limit 10MB per file'; /* Add your custom text */
    display: block; /* Make sure it's visible */
    font-size: 0.9em; /* Adjust font size if needed */
    color: #888; /* Adjust color if needed */
    margin-top: 5px; /* Add some spacing if needed */
}
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
if 'uploaded_document_id' not in st.session_state:
    st.session_state.uploaded_document_id = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'fetch_retries_count' not in st.session_state:
    st.session_state.fetch_retries_count = 0

# Function to format timestamp
def format_timestamp(ms_timestamp):
    if ms_timestamp:
        try:
            # Convert string timestamp to float before division
            dt_utc = datetime.fromtimestamp(float(ms_timestamp) / 1000, tz=pytz.utc)
            dt_jakarta = dt_utc.astimezone(JAKARTA_TZ)
            return dt_jakarta.strftime("%d/%m/%Y %H:%M:%S")
        except (ValueError, TypeError) as e:
            # Removed st.error here to prevent repetitive messages on reruns
            return "Invalid Timestamp"
    return "N/A"

with st.container():
    # st.markdown('<div class="api-section">', unsafe_allow_html=True)
    # st.subheader("🔗 API Configuration")
    # st.write(f"**Base API Endpoint:** `{BASE_API_ROOT_URL}`")
    # st.write(f"**Target S3 Bucket:** `{S3_BUCKET_NAME}`")
    
    st.markdown("---")
    st.markdown("##### Customer Name")
    user_folder_name = st.text_input(
        "", 
        placeholder="Enter the Customer name (e.g., 'Bungasari', 'Haldin')",
        label_visibility="collapsed",
        help="This will be the sub-folder within your S3 bucket (e.g., 'Bungasari', 'Haldin')."
    )
    
    # Ensure user_folder_name has a trailing slash if not empty
    if user_folder_name and not user_folder_name.endswith('/'):
        user_folder_name += '/'
    # No else needed; if user_folder_name is empty, it remains empty

    st.markdown('</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📤 File Upload")
    uploaded_file = st.file_uploader(
        "", 
        label_visibility="collapsed", 
        accept_multiple_files=False
    )
    
    api_upload_url = None
    current_document_id = None # This will be the S3 object key

    if uploaded_file:
        st.success(f"✅ File selected: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        # --- NEW VALIDATION LOGIC START ---
        if not user_folder_name: # Check if folder name is empty (or just a "/")
            st.error("❌ Please Enter The Customer Name")
            uploaded_file = None # Set uploaded_file to None to block further processing
            api_upload_url = None # Ensure URL is not generated
            current_document_id = None # Ensure ID is not set
        # --- NEW VALIDATION LOGIC END ---
        
        if uploaded_file: # Only proceed if uploaded_file is still valid after check
            filename = uploaded_file.name
            
            # Construct the S3 object key
            current_document_id = f"{user_folder_name}{filename}"
            
            # The API Gateway URL for PUT (upload) is specific
            # It's usually BASE_API_ROOT_URL/prod/bucketname/folder/filename
            # Assuming your API Gateway base path is BASE_API_ROOT_URL/prod/
            # and it routes to an S3 proxy where the full path is bucket_name/folder/filename
            api_upload_url = f"{BASE_API_ROOT_URL}/{S3_BUCKET_NAME}{current_document_id}"
            
            # st.info(f"Generated API URL for upload: `{api_upload_url}`")

    st.markdown('</div>', unsafe_allow_html=True)

# Main action buttons
if uploaded_file and api_upload_url: # These conditions prevent buttons from showing if validation fails
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        if st.button("🚀 POST Upload", type="primary", use_container_width=True):
            st.session_state.analysis_results = None # Clear previous results
            st.session_state.uploaded_document_id = None # Clear previous document ID
            st.session_state.fetch_retries_count = 0 # Reset fetch retries
            with st.spinner("Uploading..."):
                try:
                    # For API Gateway S3 Proxy, it's often a PUT request directly to the S3 path
                    response = requests.put(api_upload_url, data=uploaded_file.getvalue())
                    
                    if response.status_code == 200:
                        st.success(f"✅ Upload successful! Status: {response.status_code}")
                        st.session_state.uploaded_document_id = current_document_id # Store the document ID

                    else:
                        st.warning(f"⚠️ Upload failed. Status: {response.status_code}")
                    
                    with st.expander("📋 Response Details"):
                        try:
                            st.json(response.json())
                        except ValueError:
                            st.text(response.text)
                except Exception as e:
                    st.error(f"❌ Upload failed: {e}")

# Section to retrieve and display results
if st.session_state.uploaded_document_id:
    st.markdown("---")
    st.subheader("📊 Document Analysis Results")
    
    # --- DISABLED AUTO-REFRESH ---
    # main_refresh_interval_seconds = 10 
    # if (time.time() - st.session_state.last_refresh_time) > main_refresh_interval_seconds:
    #     st.session_state.last_refresh_time = time.time() 
    #     st.rerun() 

    if st.button("🔄 Retrieve Analysis Results Now", use_container_width=True):
        st.session_state.analysis_results = None # Clear previous
        st.session_state.fetch_retries_count = 0 # Reset fetch retries for manual fetch
        # The fetching logic below will run

    # Parameters for fetching retries within a single streamlit rerun
    max_fetch_retries = 20 # Maximum attempts to fetch results if 404
    fetch_retry_interval_seconds = 10 # Time to wait between fetch retries (if 404)
    
    results_api_url = f"{BASE_API_ROOT_URL}/results/{st.session_state.uploaded_document_id}"
    
    # Only fetch if results are not already present
    if st.session_state.analysis_results is None:
        time.sleep(15) 
        # st.info(f"Attempting to fetch results...")
        fetch_placeholder = st.empty() # Create a placeholder for dynamic messages during fetch

        with fetch_placeholder.container(): # Use container to clear previous messages
            with st.spinner(f"Fetching and waiting for analysis results..."):
                while st.session_state.fetch_retries_count < max_fetch_retries:
                    try:
                        response = requests.get(results_api_url)
                        
                        if response.status_code == 200:
                            st.success("✅ Results found!")
                            st.session_state.analysis_results = response.json()
                            st.session_state.fetch_retries_count = 0 # Reset on success
                            break # Exit the while loop
                        elif response.status_code == 404:
                            st.info(f"Analysis still in progress or not found... (Attempt {st.session_state.fetch_retries_count + 1}/{max_fetch_retries})")
                            st.session_state.fetch_retries_count += 1
                            time.sleep(fetch_retry_interval_seconds) # Wait before retrying
                            if st.session_state.fetch_retries_count >= max_fetch_retries:
                                st.warning("⚠️ Max retries reached. Analysis might still be in progress or failed. Check Lambda/Step Functions logs or try manual refresh.")
                        else:
                            st.error(f"❌ Error fetching results: Status {response.status_code}")
                            with st.expander("Response Details"):
                                st.text(response.text)
                            st.session_state.fetch_retries_count = 0 # Reset on other error
                            break # Exit loop on other errors
                    except Exception as e:
                        st.error(f"❌ Network or API error during fetch: {e}")
                        st.session_state.fetch_retries_count = 0 # Reset on network error
                        break # Exit loop on network error
                
    if st.session_state.analysis_results:
        # Prepare header fields for the combined table
        doc_id = st.session_state.analysis_results.get('documentId', 'N/A')
        classification = st.session_state.analysis_results.get('classifiedData', 'N/A')
        timestamp_ms = st.session_state.analysis_results.get('classificationTimestamp')
        classified_at = format_timestamp(timestamp_ms)

        structured_fields = st.session_state.analysis_results.get('structuredFields', {})
        
        invoice_no = structured_fields.get('InvoiceNumber', 'N/A')
        po_no = structured_fields.get('PONo', 'N/A')
        tax_no = structured_fields.get('TaxNo', 'N/A')

        # Get item details (list fields)
        list_fields_data = {k: v for k, v in structured_fields.items() if isinstance(v, list)}

        # Determine the maximum number of rows among all lists
        max_rows = 1 # At least one row for header info if no item details
        if list_fields_data:
            max_rows = max(len(v) for v in list_fields_data.values())
            if max_rows == 0: # If lists are empty, still show one row for header
                max_rows = 1

        # Create a list of dictionaries for the combined dataframe
        combined_table_data = []
        for i in range(max_rows):
            row = {}
            # Add header fields to each row
            row["Document ID"] = doc_id
            row["Classification"] = classification
            row["Classified At"] = classified_at
            row["Invoice Number"] = invoice_no
            row["PO Number"] = po_no
            row["Tax Number"] = tax_no

            # Add item details for current row
            for key, values in list_fields_data.items():
                row[key] = values[i] if i < len(values) else ""
            combined_table_data.append(row)
        
        if combined_table_data:
            st.markdown("---")
            st.subheader("📋 Consolidated Document Data")
            
            # Create DataFrame
            df = pd.DataFrame(combined_table_data)
            
            # Reorder columns to match the desired output visually
            # Ensure all expected columns are present, even if empty
            desired_columns_order = [
                "Document ID", "Classification", "Classified At",
                "Invoice Number", "PO Number", "Tax Number",
                "ItemName", "Quantity", "UnitPrice", "DeleveryOrderNumber", "DeleveryOrderDate"
            ]
            
            # Filter and reorder columns that actually exist in the DataFrame
            existing_ordered_columns = [col for col in desired_columns_order if col in df.columns]
            df = df[existing_ordered_columns]

            st.dataframe(df, use_container_width=True)

            # Add download button
            csv_file = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Data as CSV",
                data=csv_file,
                file_name=f"{os.path.basename(doc_id).replace('.', '_')}_analysis.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("No consolidated data available for display.")

        st.subheader("Extracted Data Details (Raw JSON)")
        with st.expander("View Raw JSON Data"):
            st.json(st.session_state.analysis_results)

        # Display Parsed Table Markdown (will show "No generic tables extracted" as expected)
        # parsed_tables = st.session_state.analysis_results.get('ParsedTablesMarkdown', [])
        # if parsed_tables:
        #     st.markdown("---")
        #     st.subheader("📊 Parsed Tables (Markdown)")
        #     for i, table_md in enumerate(parsed_tables):
        #         st.write(f"**Table {i+1}:**")
        #         st.markdown(table_md) # Streamlit renders Markdown directly
        #         st.markdown("---")
        # else:
        #     st.info("No generic tables extracted or parsed for this document.")

        # Display Queries (will show "No queries found" as expected)
        # queries = st.session_state.analysis_results.get('Queries', {})
        # if queries:
        #     st.markdown("---")
        #     st.subheader("🔍 Query Results")
        #     for alias, answer in queries.items():
        #         st.write(f"- **{alias}:** {answer}")
        # else:
        #     st.info("No queries found for this document.")

if not uploaded_file:
    st.info("💡 Please select a file to upload")
elif not user_folder_name:
    st.info("💡 Please enter an S3 folder name.")

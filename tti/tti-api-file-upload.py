import streamlit as st
import requests
import time
import os
import json
from datetime import datetime
import pytz # For timezone conversion

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
BASE_API_ROOT_URL = "https://a4hsl7pj9c.execute-api.ap-southeast-1.amazonaws.com/dev" # <--- UPDATE THIS TO YOUR API GATEWAY ROOT URL
S3_BUCKET_NAME = "tti-ocr-ap-southeast-1/" # Your S3 Bucket Name
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# Initialize session state variables
if 'uploaded_document_id' not in st.session_state:
    st.session_state.uploaded_document_id = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = time.time() # Track last refresh for auto-refresh

# Function to format timestamp
def format_timestamp(ms_timestamp):
    if ms_timestamp:
        dt_utc = datetime.fromtimestamp(ms_timestamp / 1000, tz=pytz.utc)
        dt_jakarta = dt_utc.astimezone(JAKARTA_TZ)
        return dt_jakarta.strftime("%d/%m/%Y %H:%M:%S")
    return "N/A"

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
    
    if user_folder_name and not user_folder_name.endswith('/'):
        user_folder_name += '/'
    elif not user_folder_name:
        user_folder_name = ""

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
        
        filename = uploaded_file.name
        
        # Construct the S3 object key
        current_document_id = f"{user_folder_name}{filename}"
        
        # The API Gateway URL for PUT (upload) is specific
        # It's usually BASE_API_ROOT_URL/prod/bucketname/folder/filename
        # Assuming your API Gateway base path is BASE_API_ROOT_URL/prod/
        # and it routes to an S3 proxy where the full path is bucket_name/folder/filename
        # Adjust this mapping based on your API Gateway's actual configuration
        api_upload_url = f"{BASE_API_ROOT_URL}/{S3_BUCKET_NAME}{current_document_id}"
        
        st.info(f"Generated API URL for upload: `{api_upload_url}`")

    st.markdown('</div>', unsafe_allow_html=True)

# Main action buttons
if uploaded_file and api_upload_url:
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        if st.button("🚀 POST Upload", type="primary", use_container_width=True):
            st.session_state.analysis_results = None # Clear previous results
            st.session_state.uploaded_document_id = None # Clear previous document ID
            st.session_state.last_refresh_time = time.time() # Reset refresh timer on new upload
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
    
    # Auto-refresh logic
    refresh_interval_seconds = 10 # Refresh every 10 seconds
    if (time.time() - st.session_state.last_refresh_time) > refresh_interval_seconds:
        st.session_state.last_refresh_time = time.time() # Update last refresh time
        st.rerun() # Trigger a rerun to re-fetch data

    if st.button("🔄 Retrieve Analysis Results Now", use_container_width=True):
        st.session_state.analysis_results = None # Clear previous
        st.session_state.last_refresh_time = time.time() # Reset timer for manual refresh
        # The fetching logic below will run
    
    results_api_url = f"{BASE_API_ROOT_URL}/results/{st.session_state.uploaded_document_id}"
    
    # Only fetch if results are not already present or if explicitly asked to refresh
    if st.session_state.analysis_results is None:
        st.info(f"Attempting to fetch results from: `{results_api_url}`")
        with st.spinner("Fetching and waiting for analysis results... (This may take a while for large documents)"):
            try:
                response = requests.get(results_api_url)
                
                if response.status_code == 200:
                    st.success("✅ Results found!")
                    st.session_state.analysis_results = response.json()
                elif response.status_code == 404:
                    st.info("Analysis still in progress or not found. Waiting for results...")
                    # No time.sleep here, relying on auto-refresh or manual button
                else:
                    st.error(f"❌ Error fetching results: Status {response.status_code}")
                    with st.expander("Response Details"):
                        st.text(response.text)
            except Exception as e:
                st.error(f"❌ Network or API error: {e}")
    
    if st.session_state.analysis_results:
        # Display general document info
        st.markdown("---")
        st.subheader("📄 Document Information")
        doc_info_cols = st.columns(3)
        with doc_info_cols[0]:
            st.write(f"**Document ID:** {st.session_state.analysis_results.get('documentId', 'N/A')}")
        with doc_info_cols[1]:
            st.write(f"**Classification:** {st.session_state.analysis_results.get('classifiedData', 'N/A')}")
        with doc_info_cols[2]:
            timestamp_ms = st.session_state.analysis_results.get('classificationTimestamp')
            st.write(f"**Classified At (Jkt):** {format_timestamp(timestamp_ms)}")


        st.subheader("Extracted Data Details")
        with st.expander("View Raw JSON Data"):
            st.json(st.session_state.analysis_results)

        # Display Structured Fields as a table
        structured_fields = st.session_state.analysis_results.get('structuredFields', {})
        if structured_fields:
            st.markdown("---")
            st.subheader("📋 Structured Fields")
            
            # Prepare data for Streamlit table, transposing if necessary
            # The image shows "ItemName", "Quantity", "UnitPrice", "DeleveryOrderNumber", "DeleveryOrderDate"
            # as columns, with lists of values. We need to create rows from these lists.
            
            # Find all keys that are lists and determine max length
            list_keys = [k for k, v in structured_fields.items() if isinstance(v, list)]
            max_rows = 0
            if list_keys:
                max_rows = max(len(structured_fields[k]) for k in list_keys)
            
            # Create a list of dictionaries for st.dataframe
            table_data_for_dataframe = []
            for i in range(max_rows):
                row = {}
                for key in list_keys:
                    # Get value at current index, or None/empty string if index out of bounds
                    row[key] = structured_fields[key][i] if i < len(structured_fields[key]) else ""
                table_data_for_dataframe.append(row)
            
            # Display non-list fields above the table if they exist
            non_list_fields = {k: v for k, v in structured_fields.items() if not isinstance(v, list)}
            if non_list_fields:
                st.write("**Header Fields:**")
                for key, value in non_list_fields.items():
                    st.write(f"- **{key}:** {value}")
                st.markdown("---") # Separator before the main table

            if table_data_for_dataframe:
                st.write("**Item Details:**")
                st.dataframe(table_data_for_dataframe, use_container_width=True)
            else:
                st.info("No structured item details found for this document.")

        else:
            st.info("No structured fields found for this document.")

        # Display Parsed Table Markdown
        parsed_tables = st.session_state.analysis_results.get('ParsedTablesMarkdown', [])
        if parsed_tables:
            st.markdown("---")
            st.subheader("📊 Parsed Tables (Markdown)")
            for i, table_md in enumerate(parsed_tables):
                st.write(f"**Table {i+1}:**")
                st.markdown(table_md) # Streamlit renders Markdown directly
                st.markdown("---")
        else:
            st.info("No generic tables extracted or parsed for this document.")

        # Display Queries
        queries = st.session_state.analysis_results.get('Queries', {})
        if queries:
            st.markdown("---")
            st.subheader("🔍 Query Results")
            for alias, answer in queries.items():
                st.write(f"- **{alias}:** {answer}")
        else:
            st.info("No queries found for this document.")

        # Display Classified Data (already at the top, but keeping this check here too)
        # classified_data = st.session_state.analysis_results.get('classifiedData')
        # if classified_data:
        #     st.markdown("---")
        #     st.subheader("🧠 Document Classification")
        #     st.success(f"**Category:** {classified_data}")
        # else:
        #     st.info("Document not yet classified or classification data not found.")

if not uploaded_file:
    st.info("💡 Please select a file to upload")
elif not user_folder_name:
    st.info("💡 Please enter an S3 folder name.")

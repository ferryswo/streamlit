import streamlit as st
import requests
import time
import os # Import the os module for path manipulation

st.set_page_config(page_title="API File Manager", page_icon="📁", layout="wide")

st.markdown("""
<style>
.main-header { font-size: 2.5rem; color: #1f77b4; margin-bottom: 2rem; }
.upload-section { background: #f8f9fa; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }
.api-section { background: #e8f4fd; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">📁 API File Manager</h1>', unsafe_allow_html=True)

# Define your base API URL here
BASE_API_URL = "https://api-end-point.amazonaws.com/dev/ocr-ap-southeast-4/"
# Define the fixed part of your S3 path (bucket/foldername)
S3_PATH_PREFIX = "bucket/foldername/" # Adjust this if your actual path is different

with st.container():
    st.markdown('<div class="api-section">', unsafe_allow_html=True)
    st.subheader("🔗 API Configuration")
    # Display the base API URL, no longer an input field for the user to change entirely
    st.write(f"**Base API Endpoint:** `{BASE_API_URL}`")
    st.markdown('</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📤 File Upload")
    uploaded_file = st.file_uploader("", label_visibility="collapsed")
    
    # Initialize api_url for later use
    api_url_for_request = None

    if uploaded_file:
        st.success(f"✅ File selected: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        # Construct the full API URL
        # We replace "ocr-ap-southeast-4/" with the desired S3 path and filename
        # Ensure that the base URL ends with a '/' if it's meant to be a directory,
        # or adjust string manipulation accordingly.
        
        # Get just the filename (without extension if your API expects that)
        filename = uploaded_file.name
        
        # Construct the full URL for the API endpoint
        # Assuming the API expects the full S3 path appended to the base API URL
        # For example, if BASE_API_URL is https://api-end-point.amazonaws.com/dev/
        # and you want https://api-end-point.amazonaws.com/dev/bucket/foldername/filename.pdf
        
        # Let's assume your API gateway is set up such that the S3 path comes AFTER the base URL.
        # If your API endpoint `https://api-end-point.amazonaws.com/dev/ocr-ap-southeast-4/`
        # is meant to represent the base of your S3 operations,
        # then you might just append the bucket/folder/filename to it.
        
        # A more robust way to construct the final API URL:
        # We need to decide if 'ocr-ap-southeast-4' is part of the API path
        # or if it implies the region/service and the S3 path comes after 'dev/'.
        # Based on your desired output `https://APi-end-point.amazonaws.com/dev/bucket/foldername/filename.pdf`
        # it seems 'ocr-ap-southeast-4/' needs to be replaced or ignored in favor of 'bucket/foldername/'.
        
        # Let's adjust BASE_API_URL to be only up to /dev/ if that's the true base
        # And then dynamically append.
        
        # Option 1: If BASE_API_URL is the true root and the S3 path is appended directly.
        # It seems your provided BASE_API_URL already contains 'ocr-ap-southeast-4/'.
        # If your API expects the full path like this:
        # https://api-end-point.amazonaws.com/dev/bucket/foldername/filename.pdf
        # and your BASE_API_URL is https://api-end-point.amazonaws.com/dev/ocr-ap-southeast-4/
        # this means 'ocr-ap-southeast-4/' part needs to be replaced with 'bucket/foldername/'.
        
        # Let's construct it by taking the root part of your API URL:
        base_api_root = BASE_API_URL.split('/ocr-ap-southeast-4/')[0] + '/' # Gets 'https://api-end-point.amazonaws.com/dev/'
        
        # Ensure a trailing slash for consistency
        if not base_api_root.endswith('/'):
            base_api_root += '/'
            
        api_url_for_request = f"{base_api_root}{S3_PATH_PREFIX}{filename}"
        
        st.info(f"Generated API URL for request: `{api_url_for_request}`")

    st.markdown('</div>', unsafe_allow_html=True)

# Use api_url_for_request in the POST and GET buttons
if uploaded_file and api_url_for_request: # Check if api_url_for_request has been generated
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        if st.button("🚀 POST Upload", type="primary", use_container_width=True):
            with st.spinner("Uploading..."):
                files = {"file": uploaded_file}
                try:
                    # Make the POST request to the constructed URL
                    response = requests.post(api_url_for_request, files=files)
                    if response.status_code == 200:
                        st.success(f"✅ Upload successful! Status: {response.status_code}")
                    else:
                        st.warning(f"⚠️ Status: {response.status_code}")
                    
                    with st.expander("📋 Response Details"):
                        # Attempt to parse as JSON first, then fall back to text
                        try:
                            st.json(response.json())
                        except ValueError:
                            st.text(response.text) # Display as plain text if not JSON
                except Exception as e:
                    st.error(f"❌ Upload failed: {e}")
    
    with col2:
        if st.button("📥 GET Request", use_container_width=True):
            with st.spinner("Fetching..."):
                try:
                    # Make the GET request to the constructed URL
                    response = requests.get(api_url_for_request)
                    if response.status_code == 200:
                        st.success(f"✅ Request successful! Status: {response.status_code}")
                    else:
                        st.warning(f"⚠️ Status: {response.status_code}")
                    
                    with st.expander("📋 Response Details"):
                        # Attempt to parse as JSON first, then fall back to text
                        try:
                            st.json(response.json())
                        except ValueError:
                            st.text(response.text) # Display as plain text if not JSON
                except Exception as e:
                    st.error(f"❌ Request failed: {e}")

if not uploaded_file:
    st.info("💡 Please select a file to upload")

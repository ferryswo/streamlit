import streamlit as st
import requests
import time
import os

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
BASE_API_URL = "https://a4hsl7pj9c.execute-api.ap-southeast-1.amazonaws.com/dev"
# Define the fixed bucket name part of your S3 path
S3_BUCKET_NAME = "tti-ocr-ap-southeast-1/"

with st.container():
    st.markdown('<div class="api-section">', unsafe_allow_html=True)
    st.subheader("🔗 API Configuration")
    st.write(f"**Base API Endpoint:** `{BASE_API_URL}`")
    st.write(f"**Target S3 Bucket:** `{S3_BUCKET_NAME}`")
    # User input for the folder name
    st.markdown("---")
    st.markdown("##### S3 Folder Configuration")
    user_folder_name = st.text_input(
        "Enter the S3 folder name:", 
        value="default_uploads",
        help="This will be the sub-folder within your S3 bucket (e.g., 'Bungasari', 'Haldin')."
    )
    # Ensure the folder name has a trailing slash if it's meant to be a folder path
    if user_folder_name and not user_folder_name.endswith('/'):
        user_folder_name += '/'
    elif not user_folder_name: 
        user_folder_name = ""

    st.markdown('</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📤 File Upload")
    uploaded_file = st.file_uploader("", label_visibility="collapsed")
    
    api_url_for_request = None

    if uploaded_file:
        st.success(f"✅ File selected: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        filename = uploaded_file.name
        base_api_root = BASE_API_URL.split('/tti-ocr-ap-southeast-1/')[0] + '/'
        
        if not base_api_root.endswith('/'):
            base_api_root += '/'
            
        api_url_for_request = f"{base_api_root}{S3_BUCKET_NAME}{user_folder_name}{filename}"
        
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
                    response = requests.put(api_url_for_request, files=files)
                    if response.status_code == 200:
                        st.success(f"✅ Upload successful! Status: {response.status_code}")
                    else:
                        st.warning(f"⚠️ Status: {response.status_code}")
                    
                    with st.expander("📋 Response Details"):
                        try:
                            st.json(response.json())
                        except ValueError:
                            st.text(response.text)
                except Exception as e:
                    st.error(f"❌ Upload failed: {e}")

if not uploaded_file:
    st.info("💡 Please select a file to upload")
elif not user_folder_name:
    st.info("💡 Please enter an S3 folder name.")

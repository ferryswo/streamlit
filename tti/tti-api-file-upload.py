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

[data-testid="stFileUploaderDropzoneInstructions"] > div > small {
    display: none;
}
[data-testid="stFileUploaderDropzoneInstructions"] > div::after {
    content: 'Limit 10MB per file';
    display: block;
    font-size: 0.9em;
    color: #888;
    margin-top: 5px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">📁 API File Manager</h1>', unsafe_allow_html=True)
BASE_API_URL = "https://a4hsl7pj9c.execute-api.ap-southeast-1.amazonaws.com/dev"
S3_BUCKET_NAME = "tti-ocr-ap-southeast-1/"

with st.container():
    st.markdown('<div class="api-section">', unsafe_allow_html=True)
    st.subheader("🔗 API Configuration")
    st.write(f"**Base API Endpoint:** `{BASE_API_URL}`")
    st.write(f"**Target S3 Bucket:** `{S3_BUCKET_NAME}`")
    st.markdown("---")
    st.markdown("##### S3 Folder Configuration")
    user_folder_name = st.text_input(
        "",
        placeholder="Enter the S3 folder name (e.g., 'Bungasari', 'Haldin')",
        label_visibility="collapsed",
        help="This will be the sub-folder within your S3 bucket (e.g., 'Bungasari', 'Haldin')."
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
    # uploaded_file = st.file_uploader("", label_visibility="collapsed")
    
    api_url_for_request = None

    if uploaded_file:
        st.success(f"✅ File selected: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        filename = uploaded_file.name
        
        base_api_root = BASE_API_URL.split('/ocr-ap-southeast-4/')[0] + '/'
        
        if not base_api_root.endswith('/'):
            base_api_root += '/'
            
        api_url_for_request = f"{base_api_root}{S3_BUCKET_NAME}{user_folder_name}{filename}"
        
        st.info(f"Generated API URL for request: `{api_url_for_request}`")

    st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file and api_url_for_request:
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
    
    # with col2:
        # if st.button("📥 GET Request", use_container_width=True):
            # with st.spinner("Fetching..."):
                # try:
                    # response = requests.get(api_url_for_request)
                    # if response.status_code == 200:
                        # st.success(f"✅ Request successful! Status: {response.status_code}")
                    # else:
                        # st.warning(f"⚠️ Status: {response.status_code}")
                    
                    # with st.expander("📋 Response Details"):
                        # try:
                            # st.json(response.json())
                        # except ValueError:
                            # st.text(response.text)
                # except Exception as e:
                    # st.error(f"❌ Request failed: {e}")

if not uploaded_file:
    st.info("💡 Please select a file to upload")
elif not user_folder_name:
    st.info("💡 Please enter an S3 folder name.")

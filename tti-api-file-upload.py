import streamlit as st
import requests
import time

st.set_page_config(page_title="API File Manager", page_icon="📁", layout="wide")

st.markdown("""
<style>
.main-header { font-size: 2.5rem; color: #1f77b4; margin-bottom: 2rem; }
.upload-section { background: #f8f9fa; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }
.api-section { background: #e8f4fd; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">📁 API File Manager</h1>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="api-section">', unsafe_allow_html=True)
    st.subheader("🔗 API Configuration")
    api_url = st.text_input("", placeholder="Enter your API endpoint (e.g., https://api.example.com/upload)", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📤 File Upload")
    uploaded_file = st.file_uploader("", label_visibility="collapsed")
    
    if uploaded_file:
        st.success(f"✅ File selected: {uploaded_file.name} ({uploaded_file.size} bytes)")
    st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file and api_url:
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        if st.button("🚀 POST Upload", type="primary", use_container_width=True):
            with st.spinner("Uploading..."):
                files = {"file": uploaded_file}
                try:
                    response = requests.post(api_url, files=files)
                    if response.status_code == 200:
                        st.success(f"✅ Upload successful! Status: {response.status_code}")
                    else:
                        st.warning(f"⚠️ Status: {response.status_code}")
                    
                    with st.expander("📋 Response Details"):
                        st.json(response.json() if response.headers.get('content-type') == 'application/json' else response.text)
                except Exception as e:
                    st.error(f"❌ Upload failed: {e}")
    
    with col2:
        if st.button("📥 GET Request", use_container_width=True):
            with st.spinner("Fetching..."):
                try:
                    response = requests.get(api_url)
                    if response.status_code == 200:
                        st.success(f"✅ Request successful! Status: {response.status_code}")
                    else:
                        st.warning(f"⚠️ Status: {response.status_code}")
                    
                    with st.expander("📋 Response Details"):
                        st.json(response.json() if response.headers.get('content-type') == 'application/json' else response.text)
                except Exception as e:
                    st.error(f"❌ Request failed: {e}")

if not api_url:
    st.info("💡 Please enter an API endpoint to get started")
elif not uploaded_file:
    st.info("💡 Please select a file to upload")

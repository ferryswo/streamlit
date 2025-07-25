import streamlit as st
import requests
import time
import os
from datetime import datetime, timezone, timedelta
import pytz

st.set_page_config(page_title="API File Manager", page_icon="📁", layout="wide")

st.markdown("""
<style>
.main-header { font-size: 2.5rem; color: #1f77b4; margin-bottom: 2rem; }
.upload-section { background: #f8f9fa; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }
.api-section { background: #e8f4fd; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }
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
    user_folder_name = st.text_input("", placeholder="Enter the S3 folder name (e.g., 'invoices', 'reports')", label_visibility="collapsed")
    if user_folder_name and not user_folder_name.endswith('/'):
        user_folder_name += '/'
    elif not user_folder_name:
        user_folder_name = ""
    st.markdown('</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📤 File Upload")
    uploaded_file = st.file_uploader("", label_visibility="collapsed", accept_multiple_files=False)
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

# Auto-refresh every 15 seconds
st_autorefresh = st.experimental_rerun if st.experimental_get_query_params().get("refresh") else st.experimental_set_query_params(refresh="1")

# Simulate fetching DynamoDB result from backend (replace with your actual API call or DB access)
DUMMY_DYNAMO_ITEM = {
    "documentId": "Bungasari/5200656442&1900006496 BFM - AI K DEL 3 JUN (WHEAT FLOUR F05G 26,830 KG).pdf",
    "classificationTimestamp": "1753414491112",
    "classifiedData": "Invoice",
    "structuredFields": {
        "InvoiceNumber": "6000159659",
        "TaxNo": "04002500166139662",
        "PONo": "33188555",
        "ItemName": ["Terigu F05 G Curah (BT)", "Terigu F05 G Curah (BT)"],
        "UnitPrice": ["IDR 5,900.00", "IDR 5,900.00"],
        "Quantity": ["26,810.000", "20.000"],
        "DeleveryOrderNumber": ["3000233899", "3000234789"],
        "DeleveryOrderDate": ["02.06.2025", "02.06.2025"]
    }
}

item = DUMMY_DYNAMO_ITEM
if item and "structuredFields" in item:
    fields = item["structuredFields"]
    doc_id = item.get("documentId", "")
    doc_type = item.get("classifiedData", "")
    ts = item.get("classificationTimestamp")
    dt_str = ""
    if ts:
        try:
            timestamp = int(ts) / 1000
            dt = datetime.fromtimestamp(timestamp, pytz.timezone("Asia/Jakarta"))
            dt_str = dt.strftime("%d/%m/%Y %H:%M:%S")
        except:
            dt_str = "Invalid timestamp"

    st.markdown("""
    <table>
        <tr><td><b>classificationTimestamp:</b></td><td>{}</td></tr>
        <tr><td><b>documentId:</b></td><td>{}</td></tr>
        <tr><td><b>classifiedData:</b></td><td>{}</td></tr>
        <tr><td><b>InvoiceNumber:</b></td><td>{}</td></tr>
        <tr><td><b>PONo:</b></td><td>{}</td></tr>
        <tr><td><b>TaxNo:</b></td><td>{}</td></tr>
    </table>
    <br>
    """.format(
        dt_str, doc_id, doc_type,
        fields.get("InvoiceNumber", ""),
        fields.get("PONo", ""),
        fields.get("TaxNo", "")
    ), unsafe_allow_html=True)

    # Table header
    md = "| <span style='color:#3c763d'><b>ItemName</b></span> | <b>Quantity</b> | <b>UnitPrice</b> | <b>DeleveryOrderNumber</b> | <b>DeleveryOrderDate</b> |\n"
    md += "|--------------------|----------|------------|----------------------|--------------------|\n"

    item_names = fields.get("ItemName", [])
    qtys = fields.get("Quantity", [])
    prices = fields.get("UnitPrice", [])
    donos = fields.get("DeleveryOrderNumber", [])
    dodates = fields.get("DeleveryOrderDate", [])

    row_count = max(len(item_names), len(qtys), len(prices), len(donos), len(dodates))

    for i in range(row_count):
        md += f"| {item_names[i] if i < len(item_names) else ''} | {qtys[i] if i < len(qtys) else ''} | {prices[i] if i < len(prices) else ''} | {donos[i] if i < len(donos) else ''} | {dodates[i] if i < len(dodates) else ''} |\n"

    st.markdown(md, unsafe_allow_html=True)

st.markdown("<br><sub style='color:#aaa;'>🔄 Auto-refresh enabled every 15s</sub>", unsafe_allow_html=True)

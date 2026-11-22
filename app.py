import streamlit as st
import pandas as pd
from datetime import date
import os
import re
import requests

st.set_page_config(page_title="Agency Order App", page_icon="💊", layout="centered")

# --- CONFIGURATION ---
STAFF_PIN = "1234"
GOOGLE_SHEET_URL = "https://script.google.com/macros/s/AKfycbwCRwR_PjebqVXWM_ORXKd2LzyMosXJRM9zahdbSzYn3IGPAIyR7WTj-wOy9lYkcnCCkg/exec"
MEDICINE_FILE = "medicine.csv"

# --- STAFF LOGIN ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Staff Login")
    pin_input = st.text_input("Enter Staff PIN", type="password")
    if st.button("Login"):
        if pin_input == STAFF_PIN:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect PIN. Access denied.")
    st.stop()

# --- LOAD MEDICINE LIST ---
@st.cache_data
def load_medicines():
    items = []
    if not os.path.exists(MEDICINE_FILE):
        st.error(f"'{MEDICINE_FILE}' not found!")
        return pd.DataFrame(columns=["Medicine_Name", "Pack", "Stock"])

    with open(MEDICINE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            clean_line = line.strip()
            if not clean_line:
                continue
            parts = re.split(r"\t+|\s{2,}", clean_line)
            if len(parts) >= 2:
                if parts[0].isdigit():
                    med_name = parts[1].strip()
                    pack = parts[2].strip() if len(parts) > 2 else "-"
                    stock = parts[3].strip() if len(parts) > 3 else "-"
                else:
                    med_name = parts[0].strip()
                    pack = parts[1].strip() if len(parts) > 1 else "-"
                    stock = parts[2].strip() if len(parts) > 2 else "-"

                if med_name.lower() in ["item name", "medicine", "particulars", "product"]:
                    continue

                items.append({"Medicine_Name": med_name, "Pack": pack, "Stock": stock})

    return pd.DataFrame(items).drop_duplicates(subset=["Medicine_Name"])

med_df = load_medicines()

if "cart" not in st.session_state:
    st.session_state.cart = []

# --- APP SCREEN ---
st.title("💊 Wholesale Medicine Order Entry")

st.subheader("1. Shopkeeper & Order Details")
col1, col2 = st.columns(2)
with col1:
    shopkeeper_name = st.text_input("Shopkeeper / Medical Store Name *", placeholder="e.g. Gupta Medical Store")
    staff_name = st.text_input("Staff Name *", placeholder="e.g. Rahul")
with col2:
    order_date = st.date_input("Order Date", value=date.today())
    notes = st.text_input("Notes / Route (Optional)", placeholder="e.g. Urgent / Evening delivery")

st.divider()
st.subheader("2. Add Medicines to Order")

if not med_df.empty:
    medicine_list = med_df["Medicine_Name"].tolist()
    selected_med = st.selectbox("Type to Search & Select Medicine", options=medicine_list)

    med_info = med_df[med_df["Medicine_Name"] == selected_med].iloc[0]
    pack = med_info["Pack"]
    stock = med_info["Stock"]

    st.info(f"📦 **Pack:** {pack}   |   📊 **Available Stock:** {stock}")

    c1, c2 = st.columns(2)
    with c1:
        qty = st.number_input("Order Quantity *", min_value=1, value=1, step=1)
    with c2:
        free_qty = st.number_input("Free / Scheme Qty", min_value=0, value=0, step=1)

    if st.button("➕ Add Medicine to Order", type="secondary"):
        st.session_state.cart.append({
            "Medicine_Name": selected_med,
            "Pack": pack,
            "Qty": qty,
            "Free_Qty": free_qty
        })
        st.success(f"Added **{selected_med}** (Qty: {qty})")

if st.session_state.cart:
    st.divider()
    st.subheader("3. Order Summary")
    cart_df = pd.DataFrame(st.session_state.cart)
    st.dataframe(cart_df, use_container_width=True, hide_index=True)

    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("✅ Submit & Save Order", type="primary", use_container_width=True):
            if not shopkeeper_name.strip() or not staff_name.strip():
                st.warning("Please enter both Shopkeeper Name and Staff Name before saving.")
            else:
                order_id = f"ORD-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
                records = []
                for item in st.session_state.cart:
                    records.append({
                        "Order_ID": order_id,
                        "Order_Date": str(order_date),
                        "Shopkeeper_Name": shopkeeper_name.strip(),
                        "Staff_Name": staff_name.strip(),
                        "Medicine_Name": item["Medicine_Name"],
                        "Pack": item["Pack"],
                        "Qty": item["Qty"],
                        "Free_Qty": item["Free_Qty"],
                        "Notes": notes.strip()
                    })

                try:
                    res = requests.post(GOOGLE_SHEET_URL, json=records, timeout=10)
                    if res.status_code == 200:
                        st.session_state.cart = []
                        st.success(f"Order **{order_id}** saved to Google Sheets for **{shopkeeper_name}**!")
                        st.balloons()
                    else:
                        st.error("Failed to save to Google Sheets. Check your Web App URL.")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    with col_clear:
        if st.button("🗑️ Clear Current List", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
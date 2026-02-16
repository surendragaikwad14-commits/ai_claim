"""
Dashboard — List claims, filter by status, see rejection reasons, export to Excel.
"""
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Dashboard | Claim Verifier", page_icon="📊", layout="wide")

st.markdown("## 📊 Verification Dashboard")
st.caption("View all claims, filter by status, and see why claims were rejected. Export to Excel below.")

try:
    from services.db import list_claims
except Exception as e:
    st.error(f"Cannot connect to database: {e}. Check MONGODB_URI in `.env`.")
    st.stop()

status_filter = st.selectbox(
    "Filter by status",
    options=["All", "accepted", "rejected", "flagged"],
    index=0,
)
limit = st.number_input("Max rows", min_value=10, max_value=500, value=100, step=10)

q_status = None if status_filter == "All" else status_filter
rows = list_claims(status=q_status, limit=limit, exclude_large_fields=True)

if not rows:
    st.info("No claims found. Submit a claim from the **Submit Claim** page.")
    st.stop()

# Normalize for display (created_at, _id)
def row_to_dict(r):
    d = {
        "Claim ID": r.get("claim_id", ""),
        "Compared With": r.get("compared_with") or "—",
        "Duplication %": r.get("duplication_pct") if r.get("duplication_pct") is not None else "—",
        "Key Differences": r.get("key_differences") or "—",
        "Status": (r.get("status") or "").capitalize(),
        "Rejection Reason": r.get("rejection_reason") or "—",
    }
    ct = r.get("created_at")
    if ct:
        d["Created"] = ct.strftime("%Y-%m-%d %H:%M") if hasattr(ct, "strftime") else str(ct)
    else:
        d["Created"] = "—"
    return d

df = pd.DataFrame([row_to_dict(r) for r in rows])

st.dataframe(df, width="stretch", hide_index=True)

# Excel export
buffer = BytesIO()
df.to_excel(buffer, index=False, sheet_name="Claims")
buffer.seek(0)

st.download_button(
    label="📥 Download as Excel",
    data=buffer,
    file_name=f"claim_verification_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    width="content",
)

"""
Submit Claim — Upload PDF and run verification pipeline.
"""
import streamlit as st
from datetime import datetime, timezone

st.set_page_config(page_title="Submit Claim | Claim Verifier", page_icon="📤", layout="wide")

st.markdown("## 📤 Submit Claim")
st.caption("Upload a claim document (PDF). We'll check for duplicates and extract key differences.")

uploaded = st.file_uploader("Choose a PDF file", type=["pdf"], help="Supported: PDF with readable text")

if uploaded is not None:
    file_bytes = uploaded.read()
    filename = uploaded.name or "document.pdf"

    if st.button("Verify claim", type="primary", width="content"):
        with st.spinner("Extracting text, comparing with existing claims, and running verification…"):
            try:
                from services.pipeline import run_verification
                result = run_verification(file_bytes, filename)
            except ValueError as e:
                st.error(f"Configuration error: {e}. Please set MONGODB_URI and Azure OpenAI keys in `.env`.")
                st.stop()
            except Exception as e:
                st.exception(e)
                st.stop()

        if not result.get("success"):
            st.error(result.get("error", "Verification failed."))
            st.stop()

        claim_id = result.get("claim_id")
        status = result.get("status", "").lower()
        compared_with = result.get("compared_with")
        duplication_pct = result.get("duplication_pct", 0)
        key_differences = result.get("key_differences", "")
        rejection_reason = result.get("rejection_reason", "")

        st.success(f"Claim saved as **{claim_id}**.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Status", status.capitalize())
        c2.metric("Duplication %", f"{duplication_pct}%" if compared_with else "—")
        c3.metric("Compared with", compared_with or "—")

        if key_differences:
            with st.expander("Key differences", expanded=True):
                st.write(key_differences)
        if rejection_reason:
            st.info(f"**Rejection reason:** {rejection_reason}")

        st.markdown("---")
        st.caption(f"Completed at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. View all claims on the **Dashboard**.")

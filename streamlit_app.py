"""
AI-Powered Claim Document Verifier
Single app: Home, Submit Claim, Dashboard (via Streamlit multipage).
"""
import streamlit as st

st.set_page_config(
    page_title="Claim Document Verifier",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom style for a clean, professional look
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1e3a5f;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #5a6c7d;
        margin-bottom: 2rem;
    }
    .card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid #e2e8f0;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">📋 AI-Powered Claim Document Verifier</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Verify claim documents, detect duplicates, and extract key differences — all in one place.</p>',
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div class="metric-card">
        <strong>📤 Submit Claim</strong><br/>
        <span style="color:#64748b;font-size:0.9rem;">Upload a PDF claim to run duplication check and get a verdict.</span>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Go to Submit Claim →", key="nav_submit", width="stretch"):
        st.switch_page("pages/1_Submit_Claim.py")
with col2:
    st.markdown("""
    <div class="metric-card">
        <strong>📊 Dashboard</strong><br/>
        <span style="color:#64748b;font-size:0.9rem;">View all claims, filter by status, and see why claims were rejected.</span>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Go to Dashboard →", key="nav_dash", width="stretch"):
        st.switch_page("pages/2_Dashboard.py")
with col3:
    st.markdown("""
    <div class="metric-card">
        <strong>📥 Export</strong><br/>
        <span style="color:#64748b;font-size:0.9rem;">Download results as Excel from the Dashboard.</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div class="card">
    <strong>How it works</strong><br/>
    1. <b>Submit Claim</b> — Upload a claim PDF. We extract text, compare it with existing claims using AI embeddings, and run an agent to decide accept / reject / flag.<br/>
    2. <b>Dashboard</b> — See all claims with status, duplication %, compared claim, key differences, and <b>rejection reason</b> for quick review.<br/>
    3. <b>Export</b> — Download the table as Excel (Claim ID, Compared With, Duplication %, Key Differences, Status, Rejection Reason).
</div>
""", unsafe_allow_html=True)

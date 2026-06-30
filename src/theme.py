"""
HireWise AI — Theme Manager
===========================
Provides dynamic light and dark theme toggling across all Streamlit pages.
"""
from __future__ import annotations

import streamlit as st

def apply_theme() -> None:
    """Initialize theme session state, render sidebar toggle button, and inject theme CSS."""
    # 1. Initialize session state theme if not present (default to light matching original theme)
    if "theme" not in st.session_state:
        st.session_state.theme = "light"

    # 2. Render theme toggle button in the sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎨 Appearance")
    
    current_theme = st.session_state.theme
    btn_label = "🌙 Switch to Dark Mode" if current_theme == "light" else "☀️ Switch to Light Mode"
    
    # Check if button is clicked
    if st.sidebar.button(btn_label, key="theme_toggle_button", use_container_width=True):
        st.session_state.theme = "dark" if current_theme == "light" else "light"
        st.rerun()

    # 3. Inject CSS overrides based on the active theme
    common_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        /* Smooth transitions */
        * {
            transition: background-color 0.15s ease, border-color 0.15s ease;
        }

        html, body, [class*="css"], [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif !important;
        }

        /* Sidebar navigation redesign as modern button blocks */
        [data-testid="stSidebarNav"] {
            padding-top: 1.5rem !important;
        }

        [data-testid="stSidebarNav"] ul {
            list-style: none !important;
            padding: 0 12px !important;
            margin: 0 !important;
            display: flex !important;
            flex-direction: column !important;
            gap: 8px !important;
        }

        [data-testid="stSidebarNav"] li {
            padding: 0 !important;
            margin: 0 !important;
        }

        [data-testid="stSidebarNav"] a {
            display: flex !important;
            align-items: center !important;
            padding: 10px 16px !important;
            border-radius: 8px !important;
            text-decoration: none !important;
            font-weight: 500 !important;
            background-color: var(--sidebar-item-bg) !important;
            color: var(--sidebar-item-text) !important;
            border: 1px solid var(--sidebar-item-border) !important;
            transition: all 0.2s ease-in-out !important;
        }

        [data-testid="stSidebarNav"] a:hover {
            background-color: var(--sidebar-item-hover-bg) !important;
            color: var(--sidebar-item-hover-text) !important;
            border-color: var(--sidebar-item-hover-border) !important;
            transform: translateY(-1px) !important;
        }

        /* Selected active state */
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
            color: #ffffff !important;
            border-color: #2563eb !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2), 0 2px 4px -1px rgba(37, 99, 235, 0.1) !important;
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] span {
            color: #ffffff !important;
        }

        [data-testid="stSidebarNav"] a span {
            color: inherit !important;
            font-weight: inherit !important;
        }

        /* Core structure colors */
        html, body, [data-testid="stAppViewContainer"], .main {
            background-color: var(--bg-color) !important;
            color: var(--text-color) !important;
        }

        [data-testid="stHeader"] {
            background-color: transparent !important;
        }

        /* Text styling */
        .stMarkdown, .stText, [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {
            color: var(--text-color) !important;
        }

        h1, h2, h3, h4, h5, h6, 
        [data-testid="stMarkdownContainer"] h1, 
        [data-testid="stMarkdownContainer"] h2, 
        [data-testid="stMarkdownContainer"] h3, 
        [data-testid="stMarkdownContainer"] h4 {
            color: var(--heading-color) !important;
            font-weight: 700 !important;
        }

        /* Cards & Panels */
        .section-card, .info-card, .stat-card, .stage-card, .download-card, .method-card {
            background-color: var(--card-bg) !important;
            color: var(--text-color) !important;
            border: 1px solid var(--card-border) !important;
            box-shadow: var(--card-shadow) !important;
            border-radius: 10px !important;
            padding: 20px !important;
            margin: 8px 0 !important;
            transition: transform 0.2s, box-shadow 0.2s !important;
        }

        .section-card:hover, .info-card:hover, .stat-card:hover, .stage-card:hover, .download-card:hover, .method-card:hover {
            transform: translateY(-2px) !important;
            box-shadow: var(--card-hover-shadow) !important;
        }

        .section-card *, .info-card *, .stat-card *, .stage-card *, .download-card *, .method-card * {
            color: var(--text-color) !important;
        }

        .stat-number {
            color: var(--stat-number-color) !important;
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            margin: 0 !important;
        }
        
        .stat-label {
            font-size: 0.85rem !important;
            color: var(--text-color) !important;
            font-weight: 500 !important;
            margin-top: 4px !important;
        }

        .download-title, .stage-title {
            color: var(--title-highlight-color) !important;
            font-weight: 700 !important;
        }

        .timeline-entry {
            border-left: 3px solid #3b82f6 !important;
            padding: 8px 16px !important;
            margin: 8px 0 !important;
            background-color: var(--timeline-bg) !important;
            border-radius: 0 8px 8px 0 !important;
            border-top: 1px solid var(--card-border) !important;
            border-right: 1px solid var(--card-border) !important;
            border-bottom: 1px solid var(--card-border) !important;
        }
        .timeline-entry * {
            color: var(--text-color) !important;
        }
        .timeline-entry small {
            color: var(--timeline-small) !important;
        }

        /* Badges & Flags */
        .flag-item {
            background-color: var(--flag-bg) !important;
            border: 1px solid var(--flag-border) !important;
            border-radius: 6px !important;
            padding: 8px 12px !important;
            margin: 4px 0 !important;
            color: var(--flag-text) !important;
            font-size: 0.85rem !important;
        }
        .flag-item * {
            color: var(--flag-text) !important;
        }

        .skill-expert { background-color: var(--skill-expert-bg) !important; color: var(--skill-expert-text) !important; }
        .skill-advanced { background-color: var(--skill-advanced-bg) !important; color: var(--skill-advanced-text) !important; }
        .skill-intermediate { background-color: var(--skill-intermediate-bg) !important; color: var(--skill-intermediate-text) !important; }
        .skill-beginner { background-color: var(--skill-beginner-bg) !important; color: var(--skill-beginner-text) !important; }

        /* Native Streamlit UI Form Inputs */
        .stSelectbox label, .stTextInput label, .stNumberInput label, .stTextArea label, [data-testid="stFileUploader"] label {
            color: var(--label-color) !important;
            font-weight: 600 !important;
            opacity: 1 !important;
        }

        .stSelectbox div[data-baseweb="select"], .stTextInput input, .stNumberInput input, .stTextArea textarea {
            background-color: var(--input-bg) !important;
            color: var(--input-text) !important;
            border: 1px solid var(--input-border) !important;
            border-radius: 6px !important;
        }
        
        /* Expanders */
        [data-testid="stExpander"] {
            background-color: var(--card-bg) !important;
            border: 1px solid var(--card-border) !important;
            border-radius: 8px !important;
        }
        [data-testid="stExpander"] summary p, [data-testid="stExpander"] summary span {
            color: var(--heading-color) !important;
            font-weight: 600 !important;
            opacity: 1 !important;
        }

        /* Tabs */
        [data-testid="stTab"] p {
            color: var(--text-color) !important;
            font-weight: 500 !important;
            opacity: 1 !important;
        }
        [data-testid="stTab"][aria-selected="true"] p {
            color: var(--tab-selected) !important;
            font-weight: 700 !important;
        }

        /* File Uploader */
        [data-testid="stFileUploader"] {
            border: 2px dashed var(--input-border) !important;
            background-color: var(--card-bg) !important;
            padding: 12px !important;
            border-radius: 8px !important;
        }
        [data-testid="stFileUploader"] p, [data-testid="stFileUploader"] span, [data-testid="stFileUploaderDropzone"] div {
            color: var(--text-color) !important;
            opacity: 1 !important;
        }

        /* Checkbox text */
        .stCheckbox label, .stCheckbox span, .stCheckbox p {
            color: var(--text-color) !important;
            font-weight: 500 !important;
            opacity: 1 !important;
        }

        /* Metrics values */
        [data-testid="stMetricValue"] {
            color: var(--heading-color) !important;
            font-weight: 800 !important;
        }
        [data-testid="stMetricLabel"] {
            color: var(--text-color) !important;
            font-weight: 500 !important;
            opacity: 1 !important;
        }

        /* Primary Button */
        div.stButton > button {
            background: linear-gradient(135deg, #2563eb, #0ea5e9) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 10px 24px !important;
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2), 0 2px 4px -1px rgba(37, 99, 235, 0.1) !important;
            transition: all 0.2s ease !important;
            opacity: 1 !important;
        }
        div.stButton > button:hover {
            opacity: 0.95 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 12px -1px rgba(37, 99, 235, 0.3), 0 4px 6px -1px rgba(37, 99, 235, 0.15) !important;
        }
        div.stButton > button:active {
            transform: translateY(1px) !important;
        }

        /* Disabled Button styling (e.g. Validate Candidates button or others) */
        div.stButton > button:disabled, 
        div.stButton > button[disabled] {
            background: var(--disabled-btn-bg) !important;
            color: var(--disabled-btn-text) !important;
            border: 1px solid var(--disabled-btn-border) !important;
            cursor: not-allowed !important;
            opacity: 1 !important;
            box-shadow: none !important;
            transform: none !important;
        }

        /* Unified Sidebar elements styling */
        [data-testid="stSidebar"] {
            background: var(--sidebar-bg) !important;
        }
        [data-testid="stSidebar"] * {
            color: var(--sidebar-item-text);
        }

        /* Sidebar toggle appearance buttons */
        [data-testid="stSidebar"] button {
            background-color: var(--sidebar-item-bg) !important;
            color: var(--sidebar-item-text) !important;
            border: 1px solid var(--sidebar-item-border) !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 8px 16px !important;
            transition: all 0.2s ease !important;
            opacity: 1 !important;
        }
        [data-testid="stSidebar"] button:hover {
            background-color: var(--sidebar-item-hover-bg) !important;
            color: var(--sidebar-item-hover-text) !important;
            border-color: var(--sidebar-item-hover-border) !important;
            transform: translateY(-1px) !important;
        }

        /* Divider lines */
        hr {
            border-color: var(--card-border) !important;
        }

        /* Page-specific unified header component */
        .page-header {
            border-radius: 12px;
            padding: 28px 36px;
            color: white !important;
            margin-bottom: 24px;
        }
        [data-testid="stMarkdownContainer"] .page-header *,
        .page-header * {
            color: white !important;
        }
        [data-testid="stMarkdownContainer"] .page-title,
        .page-title {
            font-size: 1.8rem;
            font-weight: 800;
            margin: 0;
            color: white !important;
        }
        [data-testid="stMarkdownContainer"] .page-sub,
        .page-sub {
            margin-top: 4px;
            font-size: 0.95rem;
            color: rgba(255, 255, 255, 0.9) !important;
        }

        /* Page-specific header colors */
        .header-overview { background: linear-gradient(135deg, #0f172a 0%, #1e40af 50%, #0ea5e9 100%) !important; }
        .header-upload { background: linear-gradient(135deg, #1e3a5f, #2563eb) !important; }
        .header-ranking { background: linear-gradient(135deg, #064e3b, #065f46) !important; }
        .header-rankings { background: linear-gradient(135deg, #312e81, #4f46e5) !important; }
        .header-detail { background: linear-gradient(135deg, #1e3a5f, #0f766e) !important; }
        .header-analytics { background: linear-gradient(135deg, #701a75, #a21caf) !important; }
        .header-methodology { background: linear-gradient(135deg, #1a1a2e, #16213e) !important; }
        .header-export { background: linear-gradient(135deg, #1a3a4a, #065f46) !important; }

        /* General tables */
        .stMarkdown table {
            border-collapse: collapse !important;
            width: 100% !important;
        }
        .stMarkdown th {
            background-color: var(--table-header-bg) !important;
            color: var(--heading-color) !important;
            border: 1px solid var(--card-border) !important;
            padding: 8px 12px !important;
            font-weight: 600 !important;
        }
        .stMarkdown td {
            border: 1px solid var(--card-border) !important;
            padding: 8px 12px !important;
            color: var(--text-color) !important;
        }

        /* High-contrast status badges */
        .cat-excellent { background:#dcfce7 !important; color:#15803d !important; padding:3px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; display:inline-block; }
        .cat-strong { background:#dbeafe !important; color:#1d4ed8 !important; padding:3px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; display:inline-block; }
        .cat-moderate { background:#fef9c3 !important; color:#854d0e !important; padding:3px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; display:inline-block; }
        .cat-limited { background:#fee2e2 !important; color:#b91c1c !important; padding:3px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; display:inline-block; }
        
        .risk-high { color:#dc2626 !important; font-weight:700 !important; }
        .risk-medium { color:#d97706 !important; font-weight:700 !important; }
        .risk-low { color:#16a34a !important; font-weight:700 !important; }

        /* Overview-specific classes */
        .hero-container {
            background: linear-gradient(135deg, #0f172a 0%, #1e40af 50%, #0ea5e9 100%) !important;
            border-radius: 16px !important;
            padding: 40px 48px !important;
            margin-bottom: 32px !important;
            color: white !important;
        }
        .hero-title {
            font-size: 2.8rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.5px !important;
            margin: 0 !important;
            background: linear-gradient(90deg, #ffffff, #93c5fd) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
        }
        [data-testid="stMarkdownContainer"] .hero-subtitle,
        .hero-container .hero-subtitle {
            font-size: 1.1rem !important;
            color: #ffffff !important;
            margin-top: 8px !important;
        }
        .hero-badge {
            display: inline-block !important;
            background: rgba(255,255,255,0.15) !important;
            border: 1px solid rgba(255,255,255,0.3) !important;
            border-radius: 20px !important;
            padding: 4px 16px !important;
            font-size: 0.85rem !important;
            color: #e2e8f0 !important;
            margin-top: 12px !important;
            backdrop-filter: blur(4px) !important;
        }

        .section-header {
            font-size: 1.4rem !important;
            font-weight: 700 !important;
            color: var(--heading-color) !important;
            margin: 24px 0 12px 0 !important;
            padding-bottom: 8px !important;
            border-bottom: 2px solid #3b82f6 !important;
            display: inline-block !important;
        }

        .constraint-chip {
            display: inline-block !important;
            background-color: var(--chip-bg) !important;
            color: var(--chip-text) !important;
            border: 1px solid var(--chip-border) !important;
            border-radius: 20px !important;
            padding: 4px 14px !important;
            font-size: 0.82rem !important;
            font-weight: 500 !important;
            margin: 4px !important;
        }
    </style>
    """

    if st.session_state.theme == "dark":
        st.markdown(f"""
        <style>
            :root {{
                --bg-color: #0f172a;
                --text-color: #cbd5e1;
                --heading-color: #ffffff;
                
                --card-bg: #1e293b;
                --card-text: #e2e8f0;
                --card-border: #334155;
                --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);
                --card-hover-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.3);
                
                --sidebar-bg: #090d16;
                --sidebar-item-bg: #1e293b;
                --sidebar-item-text: #e2e8f0;
                --sidebar-item-border: #334155;
                
                --sidebar-item-hover-bg: #334155;
                --sidebar-item-hover-text: #ffffff;
                --sidebar-item-hover-border: #475569;
                
                --input-bg: #1e293b;
                --input-text: #ffffff;
                --input-border: #475569;
                --label-color: #e5e7eb;
                --tab-selected: #60a5fa;
                
                --stat-number-color: #60a5fa;
                --title-highlight-color: #3b82f6;
                --table-header-bg: #1e293b;

                --disabled-btn-bg: #334155;
                --disabled-btn-text: #94a3b8;
                --disabled-btn-border: #475569;

                --timeline-bg: #1e293b;
                --timeline-small: #94a3b8;

                --flag-bg: #450a0a;
                --flag-border: #7f1d1d;
                --flag-text: #fca5a5;

                --skill-expert-bg: #064e3b;
                --skill-expert-text: #a7f3d0;
                --skill-advanced-bg: #1e3a8a;
                --skill-advanced-text: #bfdbfe;
                --skill-intermediate-bg: #78350f;
                --skill-intermediate-text: #fde68a;
                --skill-beginner-bg: #334155;
                --skill-beginner-text: #cbd5e1;

                --chip-bg: #1e3a8a;
                --chip-text: #bfdbfe;
                --chip-border: #3b82f6;
            }}
        </style>
        {common_css}
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <style>
            :root {{
                --bg-color: #f8fafc;
                --text-color: #0f172a;
                --heading-color: #0f172a;
                
                --card-bg: #ffffff;
                --card-text: #0f172a;
                --card-border: #e2e8f0;
                --card-shadow: 0 1px 3px rgba(0,0,0,0.06);
                --card-hover-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
                
                --sidebar-bg: #f1f5f9;
                --sidebar-item-bg: #ffffff;
                --sidebar-item-text: #0f172a;
                --sidebar-item-border: #cbd5e1;
                
                --sidebar-item-hover-bg: #e2e8f0;
                --sidebar-item-hover-text: #0f172a;
                --sidebar-item-hover-border: #cbd5e1;
                
                --input-bg: #ffffff;
                --input-text: #0f172a;
                --input-border: #cbd5e1;
                --label-color: #1e293b;
                --tab-selected: #2563eb;
                
                --stat-number-color: #1e40af;
                --title-highlight-color: #1e40af;
                --table-header-bg: #f1f5f9;

                --disabled-btn-bg: #e2e8f0;
                --disabled-btn-text: #64748b;
                --disabled-btn-border: #cbd5e1;

                --timeline-bg: #f8fafc;
                --timeline-small: #64748b;

                --flag-bg: #fef2f2;
                --flag-border: #fecaca;
                --flag-text: #991b1b;

                --skill-expert-bg: #ecfdf5;
                --skill-expert-text: #065f46;
                --skill-advanced-bg: #eff6ff;
                --skill-advanced-text: #1e40af;
                --skill-intermediate-bg: #fffbeb;
                --skill-intermediate-text: #92400e;
                --skill-beginner-bg: #f9fafb;
                --skill-beginner-text: #374151;

                --chip-bg: #eff6ff;
                --chip-text: #1d4ed8;
                --chip-border: #bfdbfe;
            }}
        </style>
        {common_css}
        """, unsafe_allow_html=True)

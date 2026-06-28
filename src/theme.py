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
    if st.session_state.theme == "dark":
        st.markdown("""
        <style>
            /* Smooth transitions */
            * {
                transition: background-color 0.15s ease, border-color 0.15s ease;
            }

            /* Dark mode core overrides */
            html, body, [data-testid="stAppViewContainer"], .main {
                background-color: #0b0f19 !important;
                color: #e2e8f0 !important;
            }

            [data-testid="stHeader"] {
                background-color: transparent !important;
            }

            /* Text styling */
            .stMarkdown, .stText, [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {
                color: #cbd5e1 !important;
            }

            h1, h2, h3, h4, h5, h6, 
            [data-testid="stMarkdownContainer"] h1, 
            [data-testid="stMarkdownContainer"] h2, 
            [data-testid="stMarkdownContainer"] h3, 
            [data-testid="stMarkdownContainer"] h4 {
                color: #ffffff !important;
            }

            /* Cards & Panels */
            .section-card, .info-card, .stat-card, .stage-card, .download-card, .method-card {
                background-color: #1e293b !important;
                color: #f1f5f9 !important;
                border: 1px solid #334155 !important;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1) !important;
            }

            /* Nested elements inside custom cards */
            .section-card *, .info-card *, .stat-card *, .stage-card *, .download-card *, .method-card * {
                color: #cbd5e1 !important;
            }

            .stat-number {
                color: #60a5fa !important;
            }
            
            .download-title, .stage-title {
                color: #3b82f6 !important;
                font-weight: 700 !important;
            }

            .timeline-entry {
                border-left: 3px solid #3b82f6 !important;
                background-color: #1e293b !important;
                color: #f1f5f9 !important;
                border-top: 1px solid #334155 !important;
                border-right: 1px solid #334155 !important;
                border-bottom: 1px solid #334155 !important;
            }
            .timeline-entry * {
                color: #cbd5e1 !important;
            }
            .timeline-entry small {
                color: #94a3b8 !important;
            }

            /* Badges & Flags */
            .flag-item {
                background-color: #450a0a !important;
                border: 1px solid #7f1d1d !important;
                color: #fca5a5 !important;
            }
            .flag-item * {
                color: #fca5a5 !important;
            }

            .skill-expert { background-color: #064e3b !important; color: #a7f3d0 !important; }
            .skill-advanced { background-color: #1e3a8a !important; color: #bfdbfe !important; }
            .skill-intermediate { background-color: #78350f !important; color: #fde68a !important; }
            .skill-beginner { background-color: #334155 !important; color: #cbd5e1 !important; }

            /* Metrics values */
            [data-testid="stMetricValue"] {
                color: #ffffff !important;
            }
            [data-testid="stMetricLabel"] {
                color: #94a3b8 !important;
            }

            /* Native Streamlit UI Form Inputs */
            .stSelectbox div[data-baseweb="select"] {
                background-color: #1e293b !important;
                color: #ffffff !important;
            }
            
            /* Expanders */
            [data-testid="stExpander"] {
                background-color: #1e293b !important;
                border: 1px solid #334155 !important;
            }

            /* Divider lines */
            hr {
                border-color: #334155 !important;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            /* Smooth transitions */
            * {
                transition: background-color 0.15s ease, border-color 0.15s ease;
            }

            /* Light mode core overrides */
            html, body, [data-testid="stAppViewContainer"], .main {
                background-color: #f8fafc !important;
                color: #0f172a !important;
            }

            /* Cards & Panels */
            .section-card, .info-card, .stat-card, .stage-card, .download-card, .method-card {
                background-color: #ffffff !important;
                color: #0f172a !important;
                border: 1px solid #e2e8f0 !important;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
            }

            .section-card *, .info-card *, .stat-card *, .stage-card *, .download-card *, .method-card * {
                color: #0f172a !important;
            }

            .stat-number {
                color: #1e40af !important;
            }

            .timeline-entry {
                border-left: 3px solid #3b82f6 !important;
                background-color: #f8fafc !important;
                color: #0f172a !important;
                border-top: 1px solid #e2e8f0 !important;
                border-right: 1px solid #e2e8f0 !important;
                border-bottom: 1px solid #e2e8f0 !important;
            }
            .timeline-entry * {
                color: #0f172a !important;
            }
            .timeline-entry small {
                color: #64748b !important;
            }

            /* Badges & Flags */
            .flag-item {
                background-color: #fef2f2 !important;
                border: 1px solid #fecaca !important;
                color: #991b1b !important;
            }

            .skill-expert { background-color: #ecfdf5 !important; color: #065f46 !important; }
            .skill-advanced { background-color: #eff6ff !important; color: #1e40af !important; }
            .skill-intermediate { background-color: #fffbeb !important; color: #92400e !important; }
            .skill-beginner { background-color: #f9fafb !important; color: #374151 !important; }
        </style>
        """, unsafe_allow_html=True)

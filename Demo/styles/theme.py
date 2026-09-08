"""
CSS Styles & Aerospace Dark Theme Definitions
"""

import streamlit as st

def apply_custom_theme():
    """Injects custom Grafana/Palantir dark aerospace CSS theme into Streamlit app."""
    st.markdown("""
        <style>
        /* Base Dark Background */
        .stApp {
            background-color: #0b0e14;
            color: #e6edf3;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        /* Maximize Page Layout Container */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        
        /* Completely Hide Default Streamlit Top Header, 3-Dots Menu, Dark/Light Toggle & Footer */
        header[data-testid="stHeader"] {
            visibility: hidden !important;
            height: 0px !important;
        }
        #MainMenu {
            visibility: hidden !important;
        }
        footer {
            visibility: hidden !important;
        }
        div[data-testid="stDecoration"] {
            display: none !important;
        }
        div[data-testid="stToolbar"] {
            visibility: hidden !important;
        }
        
        /* Custom Professional Header Bar */
        .app-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px 24px;
            margin-bottom: 20px;
        }
        .app-header-title {
            color: #58a6ff;
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.3px;
        }
        .app-header-sub {
            color: #8b949e;
            font-size: 0.85rem;
            margin-top: 4px;
            margin-bottom: 0;
        }

        /* Structured Metric Cards */
        .metric-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
            min-height: 125px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .metric-label {
            font-size: 0.75rem;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 1.6rem;
            font-weight: 700;
            line-height: 1.2;
        }
        .metric-subtext {
            font-size: 0.75rem;
            margin-top: 6px;
            font-weight: 500;
        }

        /* Status Badges */
        .status-normal {
            color: #3fb950;
            background: rgba(63, 185, 80, 0.12);
            border: 1px solid rgba(63, 185, 80, 0.3);
            padding: 4px 10px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .status-warning {
            color: #d29922;
            background: rgba(210, 153, 34, 0.12);
            border: 1px solid rgba(210, 153, 34, 0.3);
            padding: 4px 10px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .status-critical {
            color: #f85149;
            background: rgba(248, 81, 73, 0.12);
            border: 1px solid rgba(248, 81, 73, 0.3);
            padding: 4px 10px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.85rem;
        }

        /* Section Container */
        .flight-path-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 18px 20px;
            margin-bottom: 20px;
        }

        /* AI Diagnostic Container */
        .ai-copilot-card {
            background: #161b22;
            border: 1px solid #1f6feb;
            border-radius: 8px;
            padding: 22px;
            margin-top: 24px;
        }

        /* Settings Section Card */
        .settings-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 24px;
            margin-top: 10px;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #0d1117;
            border-right: 1px solid #21262d;
        }

        /* Clean Styled Buttons */
        .stButton > button {
            border-radius: 6px;
            font-weight: 600;
            border: 1px solid #30363d;
            background: #21262d;
            color: #c9d1d9;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            background: #30363d;
            border-color: #58a6ff;
            color: #ffffff;
        }
        </style>
    """, unsafe_allow_html=True)

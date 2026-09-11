"""Shared visual treatment for the mission console."""
import streamlit as st


def apply_custom_theme():
    st.markdown("""
    <style>
    :root { color-scheme: dark; --cyan: #40d9e6; --muted: #91a4ba; --line: #23364b; }
    .stApp { background: #080f1a; color: #e8f0f8; }
    .stApp, .stButton button, .stDownloadButton button { font-family: 'Inter', 'Segoe UI', sans-serif; }
    .block-container { max-width: 1600px; padding: 2.8rem 2.8rem 1.4rem; }
    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu, footer { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }
    [data-testid="stSidebar"] { background: #0c1624; border-right: 1px solid #1c2c40; }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
    [data-testid="stSidebar"] .stElementContainer p { font-size: .86rem; }
    .brand { display: flex; align-items: center; gap: 12px; color: #e8f0f8; font-size: 1.55rem; font-weight: 750; letter-spacing: .19em; margin: 0 0 2.3rem; }
    .brand-symbol { color: #40d9e6; font-size: 2.6rem; line-height: 1; }
    .brand-sub { display: block; font-size: .54rem; letter-spacing: .19em; color: #91a4ba; font-weight: 500; margin-top: 3px; }
    .sidebar-label { color: #7790aa; font-size: .65rem; letter-spacing: .16em; font-weight: 650; margin: 0 0 .7rem; }
    .sidebar-system { padding-top: 1rem; font-size: .76rem; color: #c4d1df; }
    .sidebar-system small { display: block; color: #7790aa; font-size: .63rem; letter-spacing: .08em; padding-top: .6rem; }
    .system-dot, .demo-badge span { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #5ce0ae; margin-right: 5px; }
    .topline { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding-bottom: 1.35rem; border-bottom: 1px solid #1c2c40; font-size: .64rem; font-weight: 650; letter-spacing: .13em; color: #91a4ba; }
    .breadcrumb { margin: 0 .7rem; color: #456078; }
    .demo-badge { border: 1px solid #284c4b; color: #91dfcb; background: #102a2c; padding: .38rem .65rem; border-radius: 4px; white-space: nowrap; }
    .mission-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem; padding: 1.4rem 0 .5rem; }
    .mission-heading h1 { font-size: clamp(1.65rem, 2.4vw, 2.5rem); font-weight: 650; letter-spacing: -.05em; line-height: 1.2; padding: 0; margin: 0 0 .55rem; }
    .mission-heading p { color: #91a4ba; font-size: .86rem; margin: 0; }
    .mission-code { text-align: right; font-family: ui-monospace, monospace; color: #aec1d4; font-size: .72rem; line-height: 1.8; white-space: nowrap; }
    .mission-code span { display: block; color: #64829d; font-size: .6rem; letter-spacing: .1em; }
    .section-heading { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin: .3rem 0 .45rem; }
    .section-heading h3 { font-size: .95rem; font-weight: 600; margin: 0; padding: 0; }
    .section-heading span { font-family: ui-monospace, monospace; color: #91a4ba; font-size: .67rem; }
    .mission-strip { display: flex; justify-content: space-between; gap: .8rem; color: #91a4ba; font-size: .78rem; padding: .7rem 0 .1rem; }
    .mission-strip strong { color: #e8f0f8; font-weight: 600; }
    .metric-card { background: linear-gradient(120deg, #101d2e, #0e1929); border: 1px solid #23364b; border-radius: 9px; padding: 1.1rem 1.2rem; min-height: 160px; }
    .metric-label { color: #91a4ba; font-size: .64rem; font-weight: 650; letter-spacing: .12em; text-transform: uppercase; margin-bottom: .65rem; }
    .metric-value { font-size: clamp(1.6rem, 2.2vw, 2.15rem); font-weight: 620; letter-spacing: -.045em; line-height: 1.2; }
    .metric-value small { font-size: .9rem; color: #91a4ba; font-weight: 400; letter-spacing: 0; }
    .metric-subtext { font-size: .7rem; color: #91a4ba; margin-top: .6rem; line-height: 1.5; }
    .metric-bar { margin-top: .65rem; height: 3px; border-radius: 4px; background: #25364a; overflow: hidden; }
    .metric-bar span { display: block; height: 100%; border-radius: 4px; }
    .status-normal { color: #5ce0ae; } .status-warning { color: #f7bb60; } .status-critical { color: #ff6b7a; }
    .snapshot-note { border-left: 2px solid #40d9e6; padding: .4rem .8rem; font-size: .8rem; color: #b0c1d2; margin: .2rem 0 .8rem; }
    .snapshot-note strong { color: #e8f0f8; }
    .ai-copilot-card, .settings-card { background: #101d2e; border: 1px solid #23364b; border-radius: 9px; padding: 1.4rem; margin: .7rem 0; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-color: #23364b !important; border-radius: 9px !important; }
    [data-testid="stPlotlyChart"] { border: 1px solid #23364b; border-radius: 8px; overflow: hidden; }
    [data-testid="stCaptionContainer"] { color: #91a4ba; }
    [data-testid="stMarkdownContainer"] h3 { font-size: 1.05rem; letter-spacing: -.02em; }
    [data-testid="stMarkdownContainer"] a { color: #40d9e6; }
    .stButton > button, .stDownloadButton > button { background: #122237; color: #d4e1ee; border: 1px solid #294159; border-radius: 6px; font-size: .8rem; font-weight: 550; transition: border-color .15s, background .15s; }
    .stButton > button:hover, .stDownloadButton > button:hover { background: #193049; border-color: #40d9e6; color: #e8f0f8; }
    .stButton > button[kind="primary"] { background: #40d9e6; border-color: #40d9e6; color: #06151e; }
    .stButton > button:focus-visible, .stDownloadButton > button:focus-visible { outline: 2px solid #40d9e6; outline-offset: 3px; }
    [data-baseweb="input"], [data-baseweb="select"] > div { background: #101d2e; color: #e8f0f8; border-color: #294159; }
    [data-baseweb="input"] input { color: #e8f0f8; }
    [data-testid="stTabs"] [role="tablist"] { gap: 1.7rem; border-bottom: 1px solid #23364b; }
    [data-testid="stTabs"] [role="tab"] { color: #91a4ba; padding: .8rem 0; }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: #40d9e6; }
    hr { border-color: #23364b; }
    .app-footer { margin-top: 2rem; border-top: 1px solid #1c2c40; padding-top: 1rem; display: flex; justify-content: space-between; gap: 1rem; color: #66809b; font-size: .63rem; letter-spacing: .02em; }
    @media (max-width: 900px) { .block-container { padding: 2.4rem 1.1rem 1rem; } .mission-code { display: none; } .metric-card { padding: .8rem; min-height: 130px; } }
    @media (max-width: 640px) {
        .mission-strip, .app-footer { flex-wrap: wrap; }
        .topline { font-size: .54rem; }
        .section-heading span { font-size: .6rem; }
        [data-testid="stTabs"] [role="tablist"] { flex-wrap: wrap; height: auto; overflow: visible; gap: 0; }
        [data-testid="stTabs"] [role="tab"] { flex: 0 0 50%; min-height: 44px; height: auto; padding: .65rem .25rem; }
    }
    @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
    </style>
    """, unsafe_allow_html=True)

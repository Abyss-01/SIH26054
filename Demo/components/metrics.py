"""
Metric Cards UI Component
"""

import streamlit as st

def render_top_metric_cards(health: float, rul: float, status_label: str, status_class: str, status_desc: str, cluster_text: str, cluster_sub: str, cluster_color: str):
    """Renders 4 top metric cards: Engine Health, RUL, Operating Status, ML Cluster State."""
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        hc = "#3fb950" if health > 80 else ("#d29922" if health > 50 else "#f85149")
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Health Index</div>
                <div class="metric-value" style="color: {hc};">{health:.1f}%</div>
                <div class="metric-subtext" style="color: {hc};">
                    {"🟢 Optimal" if health > 80 else ("🟡 Degraded" if health > 50 else "🔴 Critical")}
                </div>
            </div>
        """, unsafe_allow_html=True)

    with m2:
        rc = "#58a6ff" if rul > 50 else ("#d29922" if rul > 15 else "#f85149")
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Estimated RUL</div>
                <div class="metric-value" style="color: {rc};">{rul:.0f} <span style="font-size:1.0rem;">hrs</span></div>
                <div class="metric-subtext" style="color: #8b949e;">Next Maintenance</div>
            </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Engine State & Status</div>
                <div style="margin-top: 4px; margin-bottom: 4px;">
                    <span class="{status_class}">{status_label}</span>
                </div>
                <div class="metric-subtext" style="color: #8b949e;">{status_desc}</div>
            </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">ML Cluster State</div>
                <div class="metric-value" style="color: {cluster_color}; font-size: 1.02rem; margin-top: 4px;">{cluster_text}</div>
                <div class="metric-subtext" style="color: {cluster_color};">{cluster_sub}</div>
            </div>
        """, unsafe_allow_html=True)

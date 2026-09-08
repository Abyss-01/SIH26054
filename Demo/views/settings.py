"""
API Settings & Key Configuration View Page
"""

import streamlit as st

try:
    from google import genai
    GENAI_SDK_AVAILABLE = True
except ImportError:
    GENAI_SDK_AVAILABLE = False

def render_settings_view():
    """Renders the Google Gemini API key configuration page."""
    st.markdown("""
        <div class="settings-card">
            <h2 style="color: #58a6ff; margin-top: 0; font-size: 1.35rem;">⚙️ Google Gemini API Key Configuration</h2>
            <p style="color: #8b949e; font-size: 0.9rem;">
                Enter your Google Gemini API key below. The key enables real-time LLM diagnostic reasoning for the <b>Autonomous AI Diagnostic Engine</b> using model <code>gemini-2.5-flash</code>.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_s1, col_s2 = st.columns([2, 1])
    
    with col_s1:
        input_key = st.text_input(
            "Google Gemini API Key",
            value=st.session_state.get("gemini_api_key", ""),
            type="password",
            placeholder="AIzaSy...",
            help="Key is preserved safely in session memory."
        )
        
        if input_key != st.session_state.get("gemini_api_key", ""):
            st.session_state["gemini_api_key"] = input_key.strip()
            st.success("✅ API Key saved in session!")

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("🧪 Test API Connection", use_container_width=True):
                key_to_test = st.session_state.get("gemini_api_key", "").strip()
                if not key_to_test:
                    st.warning("⚠️ Please enter a Gemini API Key.")
                elif not GENAI_SDK_AVAILABLE:
                    st.error("❌ `google-genai` package is missing in environment.")
                else:
                    with st.spinner("Testing API connection..."):
                        try:
                            client = genai.Client(api_key=key_to_test)
                            res = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents="Diagnostic ping"
                            )
                            st.success(f"🎉 **Connection Verified!** Response: `{res.text.strip()[:60]}...`")
                        except Exception as e:
                            st.error(f"❌ Connection failed: {e}")
        with col_b2:
            if st.button("⬅️ Return to Dashboard", use_container_width=True):
                st.session_state["active_page"] = "dashboard"
                st.rerun()

    with col_s2:
        st.markdown("### ℹ️ Key Status")
        active_k = st.session_state.get("gemini_api_key", "").strip()
        if active_k:
            st.markdown("🟢 **Status**: Active")
            st.markdown(f"**Target Model**: `gemini-2.5-flash`")
            st.markdown(f"**Fingerprint**: `...{active_k[-6:] if len(active_k) > 6 else '***'}`")
        else:
            st.markdown("🟡 **Status**: Not Configured (Using Offline Rule Engine)")
            
        st.markdown("""
        ---
        **Get your free key:**
        1. Go to [Google AI Studio](https://aistudio.google.com/)
        2. Click **Get API Key**
        3. Paste it here!
        """)

import streamlit as st
st.session_state.setdefault('my_key', 'default_val')
# NO confirmation loop
st.radio('Page', ['a','b'], key='page', label_visibility='collapsed')
if st.session_state['page'] == 'a':
    st.selectbox('choice', ['x','y','z'], key='my_key', label_visibility='collapsed')
st.write('KEY:', st.session_state['my_key'])

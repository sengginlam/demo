import streamlit as st


def user_setting():
    logout = st.button("退出登录")
    if logout:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.password = None
        st.rerun()


user_setting()
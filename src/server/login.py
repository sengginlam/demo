from streamlit.connections.sql_connection import SQLConnection
from hashlib import md5
from sqlalchemy import text
from typing import Optional
import streamlit as st
from shared import ENCODE


def get_pwd(connection:SQLConnection, username:str) -> Optional[str]:
    SQL = "SELECT `password` FROM `Users` WHERE `username`= :username;"
    with connection.session as cs:
        res = cs.execute(text(SQL), {"username":username}).all()
    if len(res)==1 and len(res[0])==1:
        return res[0][0]
    else:
        return None

def check_pwd(connection:SQLConnection) -> bool:
    username = st.session_state.username
    if username and st.session_state.password:
        if md5(st.session_state.password.encode(ENCODE)).hexdigest()==get_pwd(connection, username):
            st.session_state.logged_in = True
            return True
        else:
            st.error("账号或密码错误！！！")
    else:
        st.error("请输入账号和密码！！！")
    return False

def form_login(connection:SQLConnection) ->None:
    with st.form("Credentials", clear_on_submit=True):
        col_0, col_1, col_2 = st.columns([1, 2, 1])  
        with col_1:  
            st.markdown("<h1 style='text-align: center;'>股票数据库</h1>", unsafe_allow_html=True)
        st.text_input("账号名称", key="username", help="账号：user")  
        st.text_input("账号密码", type="password", key="password", help="密码：user")  
        useless, submit = st.columns([9, 1])
        if submit.form_submit_button("登录"):
            if check_pwd(connection):
                st.rerun()

def login():
    conn = st.connection(name="mysql", type="sql")
    form_login(conn)
    

login()
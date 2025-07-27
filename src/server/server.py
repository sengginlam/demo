import streamlit as st


def init() -> None:
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

def main():
    init()
    if st.session_state.logged_in:
        stocks = st.Page("stocks.py", title="股票数据")
        portfolio = st.Page("portfolio.py", title="投资组合")
        user_setting = st.Page("user_setting.py", title="账户管理")
        pages = st.navigation([user_setting, stocks, portfolio])
    else:
        login = st.Page("login.py", title="登录")
        pages = st.navigation([login])
    pages.run()


if __name__=="__main__":
    main()
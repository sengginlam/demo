from datetime import datetime, time
from streamlit.delta_generator import DeltaGenerator
import streamlit as st
from shared import *


def show(container:DeltaGenerator, stock_symbol:int, date_from:datetime, date_to:datetime) -> None:
    data = load_stock_data(stock_symbol)
    data = data[data["date"].between(date_from, date_to)]
    data["date"] = data["date"].apply(dateformat)
    container.dataframe(data.rename(columns=COLS_NAME_0).set_axis(range(1, len(data)+1, 1)))

def statistics(container:DeltaGenerator, stock_symbol:int, date_from:datetime, date_to:datetime) -> None:
    data_raw = load_stock_data(stock_symbol)
    detail_raw = load_stock_detail(stock_symbol)
    data, bounded, daily, monthly, total_return = analyze(data_raw, detail_raw, date_from, date_to)
    figure = draw_0(data, bounded, daily, monthly, total_return)
    container.plotly_chart(figure, use_container_width=True)

def trigger(container:DeltaGenerator, data_type:str, stock_symbol:str, date_from:datetime, date_to:datetime) -> None:
    if data_type==DATA_TYPE[0]:
        show(container, stock_symbol, date_from, date_to)
    elif data_type==DATA_TYPE[1]:
        statistics(container, stock_symbol, date_from, date_to)

def stocks():
    stock_symbols = load_stock_symbol()
    stock_symbols_labels = tuple(str(ss[0]) for ss in stock_symbols.values.tolist())
    default_data = load_stock_data(int(stock_symbols_labels[0]))
    schedule = default_data["date"].unique()
    container = st.container()
    with container.form("Filter"):
        col_0, col_1, col_2, col_3, col_4 = st.columns([1, 1, 1, 1, 1])
        with col_0:
            stock_symbol = st.selectbox("选择股票", stock_symbols_labels, index=0)
        with col_1:
            date_from = st.date_input(
                label="开始日期", 
                min_value=schedule.min(), 
                max_value=schedule.max(), 
                value=schedule.min(),
                width=100
            )
        with col_2:
            date_to = st.date_input(
                label="结束日期", 
                min_value=schedule.min(), 
                max_value=schedule.max(), 
                value=schedule.max(),
                width=100
            )
        with col_3:
            data_type = st.selectbox("数据类型", DATA_TYPE, index=0)
        with col_4:
            useless, submit = st.columns([1, 1])
            if submit.form_submit_button("筛选"):
                trigger(container, data_type, int(stock_symbol), st.session_state.date_from, st.session_state.date_to)
    st.session_state.date_from = schedule.min()
    st.session_state.date_to = schedule.max()


stocks()
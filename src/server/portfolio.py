from streamlit.delta_generator import DeltaGenerator
from pandas import DataFrame
import streamlit as st
from shared import *


def show(container:DeltaGenerator) -> None:
    stock_symbols = load_stock_symbol().values.tolist()
    data = load_stock_data(stock_symbols[0])
    for stock_symbol in stock_symbols[1:]:
        data.iloc[:, 1:] += load_stock_data(stock_symbol).iloc[:, 1:]
    data["date"] = data["date"].apply(dateformat)
    data.iloc[:, 1:] = data.iloc[:, 1:]/len(stock_symbols)
    container.dataframe(data.rename(columns=COLS_NAME_0).set_axis(range(1, len(data)+1, 1)))

def statistics(container:DeltaGenerator, date_from:datetime, date_to:datetime) -> None:
    stock_symbols = load_stock_symbol().values.tolist()
    pf = []
    for stock_symbol in stock_symbols:
        data_raw = load_stock_data(stock_symbol)
        detail_raw = load_stock_detail(stock_symbol)
        pf.append(analyze(data_raw, detail_raw, date_from, date_to))
    pf = list(map(list, zip(*pf)))
    # [data, bounded, daily, monthly, total_return]
    data = pf[0][0]
    for d in pf[0][1:]:
        data.iloc[:, 1:] += d.iloc[:, 1:]
    data.iloc[:, 1:] = data.iloc[:, 1:]/len(stock_symbols)
    daily = pf[2][0]
    for d in pf[2][1:]:
        daily["daily_avg"] += d["daily_avg"]
    daily["daily_avg"] = daily["daily_avg"]/len(stock_symbols)
    monthly = pf[3][0]
    for d in pf[3][1:]:
        monthly["monthly_avg"] += d["monthly_avg"]
    monthly["monthly_avg"] = monthly["monthly_avg"]/len(stock_symbols)
    total_return = pf[4][0]
    for d in pf[4][1:]:
        total_return[["ror_oty", "ror", "mdd_oty", "mdd"]] += d[["ror_oty", "ror", "mdd_oty", "mdd"]]
    total_return[["ror_oty", "ror", "mdd_oty", "mdd"]] = total_return[["ror_oty", "ror", "mdd_oty", "mdd"]]/len(stock_symbols)
    use = pd.concat([data[["date", "opening_price", "closing_price"]], daily["daily_avg"], monthly["monthly_avg"], total_return[["ror_oty", "ror", "mdd_oty", "mdd", "y"]]], axis=1)
    use_group = use.groupby("y")
    use["std_dev_oty"] = use_group["ror_oty"].expanding().apply(lambda cp: cp.std()).reset_index(level=0, drop=True)
    use["std_dev"] = use["ror"].expanding().std()
    count_oty = use_group["ror_oty"].apply(lambda ro: ro.expanding().count()).reset_index(drop=True)
    count = use["ror"].expanding().count()
    use["ror_avg_oty"] = (1+use["ror_oty"])**(360/count_oty)-1
    use["ror_avg"] = (1+use["ror"])**(360/count)-1
    use["sharpe_ratio_oty"] = (use["ror_avg_oty"]-RISK_FREE_RATE)/use["std_dev_oty"]
    use["sharpe_ratio"] = (use["ror_avg"]-RISK_FREE_RATE)/use["std_dev"]
    figure = draw_1(use)
    container.plotly_chart(figure, use_container_width=True)

def trigger(container:DeltaGenerator, data_type:str, date_from:datetime, date_to:datetime) -> None:
    if data_type==DATA_TYPE[0]:
        show(container)
    elif data_type==DATA_TYPE[1]:
        statistics(container, date_from, date_to)

def portfolio():
    container = st.container()
    with container.form("Filter"):
        col_0, col_1 = st.columns([1, 1])
        with col_0:
            data_type = st.selectbox("数据类型", DATA_TYPE, index=0)
        useless, submit = col_1.columns([5, 1])
        if submit.form_submit_button("筛选"):
            trigger(container, data_type, st.session_state.date_from, st.session_state.date_to)
    

portfolio()
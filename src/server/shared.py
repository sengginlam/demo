from datetime import datetime, time
from _pydatetime import date as Date
from sqlalchemy import text
from typing import List
from plotly.subplots import make_subplots
from numpy import float64
import streamlit as st
import pandas as pd
import plotly.graph_objects as go


DATA_TYPE = ("详细数据", "统计数据", )
COLS_NAME_0 = {"date":"日期", "opening_price":"开盘价", "closing_price":"收盘价", }
ENCODE = "utf-8"
RISK_FREE_RATE = 0.0138  # 1-year Chinese Government Bond Yield 


def datetimeformat(date:Date|int|str) -> datetime:
    if isinstance(date, Date):
        return datetime.combine(date, time(0, 0, 0))
    return datetime.strptime(str(date), "%Y%m%d")

def dateformat(date:datetime|int|str) -> Date:
    if isinstance(date, datetime):
        return date.date()
    return datetime.strptime(str(date), "%Y%m%d").date()

@st.cache_data
def _load_stock_symbol() -> pd.DataFrame:
    with st.connection(name="mysql", type="sql").session as cs:
        stock_symbols = cs.execute(text("SELECT `stock_symbol` FROM `Data` GROUP BY `stock_symbol`;")).all()
    return pd.DataFrame(data=stock_symbols, columns=("stock_symbols", ))

def load_stock_symbol() -> pd.DataFrame:
    return _load_stock_symbol()

@st.cache_data
def _load_stock_data(stock_symbol:int|str) -> pd.DataFrame:
    if isinstance(stock_symbol, str):
        stock_symbol = int(stock_symbol)
    with st.connection(name="mysql", type="sql").session as cs:
        data = cs.execute(text("SELECT `date`, `opening_price`, `closing_price` FROM `Data` WHERE `stock_symbol`=:stock_symbol;"), {"stock_symbol":stock_symbol}).all()
    data = pd.DataFrame(data=data, columns=("date", "opening_price", "closing_price"))
    data["date"] = data["date"].apply(datetimeformat)
    data["opening_price"] = data["opening_price"].astype(float64)
    data["closing_price"] = data["closing_price"].astype(float64)
    data = data.sort_values(by="date")
    return data

def load_stock_data(stock_symbol:int|str) -> pd.DataFrame:
    return _load_stock_data(stock_symbol)

@st.cache_data
def _load_stock_detail(stock_symbol:int, date:int=None) -> pd.DataFrame:
    if date:
        sql = "SELECT `date`, `execution_price`, `number_of_shared_traded` FROM `Detail` WHERE `stock_symbol`=:stock_symbol AND `date`=:date;"
        params = {"stock_symbol":stock_symbol, "date":date}
    else:
        sql = "SELECT `date`, `execution_price`, `number_of_shared_traded` FROM `Detail` WHERE `stock_symbol`=:stock_symbol;"
        params = {"stock_symbol":stock_symbol}
    with st.connection(name="mysql", type="sql").session as cs:
        data = cs.execute(text(sql), params).all()
    data = pd.DataFrame(data=data, columns=("date", "execution_price", "number_of_shared_traded"))
    data["date"] = data["date"].apply(datetimeformat)
    data["execution_price"] = data["execution_price"].astype(float64)
    data = data.sort_values(by="date")
    return data

def load_stock_detail(stock_symbol:int, date:int=None) -> pd.DataFrame:
    return _load_stock_detail(stock_symbol, date)

@st.cache_data
def _analyze(
        data:pd.DataFrame, 
        detail:pd.DataFrame, 
        date_from:datetime, 
        date_to:datetime
    ) -> List[pd.DataFrame]:
    data = data[data["date"].between(date_from, date_to)]
    detail = detail[detail["date"].between(date_from, date_to)]
    bounded = detail.groupby("date")["execution_price"].aggregate(["max", "min"])
    lambda_tmp = lambda df: (df["execution_price"]*df["number_of_shared_traded"]).sum()
    daily_volume = detail.groupby("date")[["execution_price", "number_of_shared_traded"]].apply(lambda_tmp).rename("daily_volume").reset_index()
    daily = daily_volume.merge(
            right=detail.groupby("date")["number_of_shared_traded"].sum().rename("daily_number").reset_index(), 
            how="outer",
            on="date",
        ).fillna(0)
    daily["daily_avg"] = daily["daily_volume"]/daily["daily_number"]
    monthly = daily.copy()
    monthly["y_m"] = monthly["date"].dt.to_period("M")
    monthly_group = monthly.groupby("y_m")
    monthly["monthly_volume"] = monthly_group["daily_volume"].apply(lambda da: da.expanding().sum()).reset_index(level=0, drop=True)
    monthly["monthly_number"] = monthly_group["daily_number"].apply(lambda da: da.expanding().sum()).reset_index(level=0, drop=True)
    monthly["monthly_avg"] = monthly_group["daily_avg"].apply(lambda da: (da.expanding().sum())/(da.expanding().count())).reset_index(level=0, drop=True)
    daily_prev = data.iloc[:-1, :].reset_index()
    daily_curr = data.iloc[1:, :].reset_index()
    daily_return = daily_curr["closing_price"]-daily_prev["closing_price"]
    total_return = pd.merge(
            daily[["date"]], 
            data[["date", "closing_price"]], 
            on="date", 
            how="left"
        )
    total_return["daily_r"] = pd.concat([pd.Series([0]), daily_return], ignore_index=True)
    total_return["y"] = total_return["date"].dt.to_period("Y")
    total_return_group = total_return.groupby("y")
    total_return["ror_oty"] = total_return_group[["closing_price", "daily_r"]].apply(lambda dr: (dr["daily_r"].expanding().sum()/(dr["closing_price"].iat[0]))).reset_index(level=0, drop=True)
    #oty means "of this year"
    cpotfd = total_return["closing_price"].iat[0]    # closing price on the first day
    total_return["ror"] = total_return["daily_r"].expanding().sum()/cpotfd
    min_oty = total_return_group["closing_price"].cummin()
    total_return["mdd_oty"] = (cpotfd-min_oty)/cpotfd
    total_return["mdd"] = (cpotfd-total_return["closing_price"].cummin())/cpotfd
    total_return["std_dev_oty"] = total_return_group["ror_oty"].expanding().apply(lambda cp: cp.std()).reset_index(level=0, drop=True)
    total_return["std_dev"] = total_return["ror"].expanding().std()
    count_oty = total_return_group["ror_oty"].apply(lambda ro: ro.expanding().count()).reset_index(drop=True)
    count = total_return["ror"].expanding().count()
    total_return["ror_avg_oty"] = (1+total_return["ror_oty"])**(360/count_oty)-1
    total_return["ror_avg"] = (1+total_return["ror"])**(360/count)-1
    total_return["sharpe_ratio_oty"] = (total_return["ror_avg_oty"]-RISK_FREE_RATE)/total_return["std_dev_oty"]
    total_return["sharpe_ratio"] = (total_return["ror_avg"]-RISK_FREE_RATE)/total_return["std_dev"]
    # monthly.drop(["daily_volume", "daily_number", "daily_avg", "y_m"], axis=1, inplace=True)
    # total_return.drop(["closing_price", "daily_r", "std_dev_oty", "std_dev", "ror_avg_oty", "ror_avg", "y"], axis=1, inplace=True)
    return [data, bounded, daily, monthly, total_return]

def analyze(
        data:pd.DataFrame, 
        detail:pd.DataFrame, 
        date_from:datetime, 
        date_to:datetime
    ) -> List[pd.DataFrame]:
    """
    # Returns
        - data:         ["date", "opening_price", "closing_price"]
        - bounded:      ["date", "max", "min"]
        - daily:        ["date", "daily_volume", "daily_number", "daily_avg"]  

            - "daily_avg": VWAP (Volume Weighted Average Price)
        
        - monthly:      ["date", "monthly_volume", "monthly_number", "monthly_avg"] 
        
            - going drop ["daily_volume", "daily_number", "daily_avg", "y_m"]

            - "monthly_avg": VWAP
        
        - total_return: ["date",  "ror_oty", "ror", "mdd_oty", "mdd", "sharpe_ratio_oty", "sharpe_ratio"]

            - going drop ["closing_price", "daily_r", "std_dev_oty", "std_dev", "ror_avg_oty", "ror_avg", "y"]
    """
    return _analyze(data, detail, date_from, date_to)

@st.cache_resource
def _draw_0(data:pd.DataFrame, bounded:pd.DataFrame, daily:pd.DataFrame, monthly:pd.DataFrame, total_return:pd.DataFrame) -> go.Figure:
    data["date"] = data["date"].apply(dateformat)
    volume = daily["daily_number"]
    figure = make_subplots(
        rows=2, 
        cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05, 
        row_heights=[0.7, 0.3],
    )
    figure.add_trace(
        go.Candlestick(
            x=data["date"], 
            open=data["opening_price"], 
            high=bounded["max"], 
            low=bounded["min"], 
            close=data["closing_price"],
            name="K线",
            increasing_line_color="red",
            decreasing_line_color="green"
        ), 
        row=1, 
        col=1
    )
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=daily["daily_avg"],
            name="日均线",
            line=dict(color="royalblue", width=2),
            opacity=0.9
        ), 
        row=1, 
        col=1
    )
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=monthly["monthly_avg"],
            name="月均线",
            line=dict(color="orange", width=2, dash="dot"),
            opacity=0.7
        ),
        row=1,
        col=1
    )
    if volume is not None:
        figure.add_trace(
            go.Bar(
                x=data["date"],
                y=volume,
                name="成交量",
                marker_color="rgba(158,202,225,0.6)"
            ),
            row=2,
            col=1
        )
    hover_text = []
    for i in range(data["date"].count()):
        hover_text.append(
            f"<b>日期:</b> {data["date"].iloc[i]}<br>"
            f"<b>开盘价:</b> {data["opening_price"].iloc[i]:.2f}<br>"
            f"<b>收盘价:</b> {data["closing_price"].iloc[i]:.2f}<br>"
            f"<b>日均价:</b> {daily["daily_avg"].iloc[i]:.2f}<br>"
            f"<b>月均价:</b> {monthly["monthly_avg"].iloc[i]:.2f}<br>"
            f"<b>今年以来收益率:</b> {total_return["ror_oty"].iloc[i]*100:.2f}%<br>"
            f"<b>历史收益率:</b> {total_return["ror"].iloc[i]*100:.2f}%<br>"
            f"<b>今年以来最大回撤:</b> {total_return["mdd_oty"].iloc[i]*100:.2f}%<br>"
            f"<b>历史最大回撤:</b> {total_return["mdd"].iloc[i]*100:.2f}%<br>"
            f"<b>今年以来夏普比率:</b> {total_return["sharpe_ratio_oty"].iloc[i]:.2f}<br>"
            f"<b>历史夏普比率:</b> {total_return["sharpe_ratio"].iloc[i]:.2f}<br>"
        )
    figure.update_traces(hovertext=hover_text, hoverinfo="text", selector={"type": "candlestick"})
    figure.update_layout(
        title="股票K线图与分析",
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1个月", step="month", stepmode="backward"),
                    dict(count=3, label="3个月", step="month", stepmode="backward"),
                    dict(count=6, label="6个月", step="month", stepmode="backward"),
                    dict(count=1, label="1年", step="year", stepmode="backward"),
                    dict(step="all", label="全部")
                ]),
                font=dict(size=10)
            ),
            rangeslider=dict(visible=False),
            type="date",
            showgrid=True,
            gridcolor="rgba(200,200,200,0.2)"
        ),
        yaxis=dict(
            title="价格",
            showgrid=True,
            gridcolor="rgba(200,200,200,0.2)"
        ),
        yaxis2=dict(
            title="成交量",
            showgrid=True,
            gridcolor="rgba(200,200,200,0.2)"
        ),
        dragmode="pan",
        height=900,
        plot_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
    )
    figure.update_xaxes(rangeslider_thickness=0.05)
    return figure

def draw_0(data:pd.DataFrame, bounded:pd.DataFrame, daily:pd.DataFrame, monthly:pd.DataFrame, total_return:pd.DataFrame) -> go.Figure:
    return _draw_0(data, bounded, daily, monthly, total_return)

@st.cache_resource
def _draw_1(use:pd.DataFrame) -> go.Figure:
    use["date"] = use["date"].apply(dateformat)
    figure = make_subplots(
        rows=1,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
    )
    figure.add_trace(
        go.Scatter(
            x=use["date"],
            y=use["daily_avg"],
            name="日均线",
            line=dict(color="royalblue", width=2),
            opacity=0.9
        ),
        row=1,
        col=1
    )
    figure.add_trace(
        go.Scatter(
            x=use["date"],
            y=use["monthly_avg"],
            name="月均线",
            line=dict(color="orange", width=2, dash="dot"),
            opacity=0.7
        ),
        row=1,
        col=1
    )
    hover_text = []
    for i in range(use["date"].count()):
        hover_text.append(
            f"<b>日期:</b> {use['date'].iloc[i]}<br>"
            f"<b>开盘价:</b> {use['opening_price'].iloc[i]:.2f}<br>"
            f"<b>收盘价:</b> {use['closing_price'].iloc[i]:.2f}<br>"
            f"<b>日均价:</b> {use['daily_avg'].iloc[i]:.2f}<br>"
            f"<b>月均价:</b> {use['monthly_avg'].iloc[i]:.2f}<br>"
            f"<b>今年以来收益率:</b> {use['ror_oty'].iloc[i]*100:.2f}%<br>"
            f"<b>历史收益率:</b> {use['ror'].iloc[i]*100:.2f}%<br>"
            f"<b>今年以来最大回撤:</b> {use['mdd_oty'].iloc[i]*100:.2f}%<br>"
            f"<b>历史最大回撤:</b> {use['mdd'].iloc[i]*100:.2f}%<br>"
            f"<b>今年以来夏普比率:</b> {use['sharpe_ratio_oty'].iloc[i]:.2f}<br>"
            f"<b>历史夏普比率:</b> {use['sharpe_ratio'].iloc[i]:.2f}<br>"
        )
    figure.update_traces(hovertext=hover_text, hoverinfo="text", selector=dict(name="日均线"))
    figure.update_layout(
        title="股票折线图与分析",
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1个月", step="month", stepmode="backward"),
                    dict(count=3, label="3个月", step="month", stepmode="backward"),
                    dict(count=6, label="6个月", step="month", stepmode="backward"),
                    dict(count=1, label="1年", step="year", stepmode="backward"),
                    dict(step="all", label="全部")
                ]),
                font=dict(size=10)
            ),
            rangeslider=dict(visible=False),
            type="date",
            showgrid=True,
            gridcolor="rgba(200,200,200,0.2)"
        ),
        yaxis=dict(
            title="价格",
            showgrid=True,
            gridcolor="rgba(200,200,200,0.2)"
        ),
        yaxis2=dict(
            title="成交量",
            showgrid=True,
            gridcolor="rgba(200,200,200,0.2)"
        ),
        dragmode="pan",
        height=900,
        plot_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
    )
    figure.update_xaxes(rangeslider_thickness=0.05)
    return figure

def draw_1(use:pd.DataFrame) -> go.Figure:
    return _draw_1(use)

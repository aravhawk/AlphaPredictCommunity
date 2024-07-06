import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import google.generativeai as genai
from exchanges import exchange_names

# Set your Google AI API key
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Define the model
model = genai.GenerativeModel('gemini-pro')

st.title('AlphaPredictCommunity')

# Input for stock symbol
stock_symbol = st.text_input("Enter a stock symbol", "AAPL")


# Fetch stock data
def get_stock_data(symbol):
    stock = yf.Ticker(symbol)
    return stock


def display_stock_info(stock):
    st.subheader("Stock Information")
    info = stock.info
    company_name = info.get("longName", "N/A")
    exchange_code = info.get("exchange", "N/A")
    index = exchange_names.get(exchange_code, exchange_code)  # Map to common name if available
    current_price = info.get("currentPrice")
    full_time_employees = info.get("fullTimeEmployees", "N/A")

    st.text(f"Name: {company_name}")
    st.text(f"Index: {index}")
    if current_price:
        st.text(f"Current Price: ${current_price:.2f}")
    else:
        st.text("Current Price: Not Available")
    st.text(f"Full-time employees: {full_time_employees}")


def display_stock_history(stock):
    hist = stock.history(period="1d", interval="1m")
    fig = go.Figure(data=[go.Candlestick(x=hist.index,
                                         open=hist['Open'], high=hist['High'],
                                         low=hist['Low'], close=hist['Close'])])
    fig.update_layout(height=300, margin={'t': 0, 'b': 0, 'l': 0, 'r': 0})
    st.plotly_chart(fig, use_container_width=True)


def get_gemini_insights(query):
    # Call the Gemini API
    response = model.generate_content(query)
    return response.text


if stock_symbol:
    if st.button('Refresh'):
        st.experimental_rerun()

    stock = get_stock_data(stock_symbol)

    col1, col2 = st.columns([3, 2])

    with col1:
        display_stock_history(stock)

    with col2:
        display_stock_info(stock)

    st.text("*Charts in Eastern Time")

    st.subheader("AI Insights")
    # Craft a query for the Gemini model based on the stock data
    query = f"Provide predictions for the stock for the next few days, based on the following current/historical data: {stock.info}"
    insights = get_gemini_insights(query)

    # Using markdown to display insights
    st.markdown(insights)


footer="""<style>
a:link , a:visited{
color: blue;
background-color: transparent;
text-decoration: underline;
}

a:hover,  a:active {
color: red;
background-color: transparent;
text-decoration: underline;
}

.footer {
position: fixed;
left: 0;
bottom: 0;
width: 100%;
background-color: transparent;
color: grey;
text-align: center;
}
</style>
<div class='footer'>
<p>AlphaPredict is powered by AI. Consider thinking before trading.</p>
</div>
"""

st.markdown(footer, unsafe_allow_html=True)

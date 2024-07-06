import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import pyrebase
from google.cloud import firestore
from openai import OpenAI
import mappings
from exchanges import exchange_names

ap_version = "1.0.0"
login_form_submitted = False

st.set_page_config(
    page_title=f"AlphaPredict ({ap_version})",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get help': 'mailto:support@neuralbytes.net?subject=Need%20Help%20with%20AlphaPredict',
        'Report a bug': 'mailto:bugs@neuralbytes.net?subject=AlphaPredict%20Bug%20Report',
        'About': '''### AlphaPredict: A professional stock market predictor and insight-provider, with charts and company details. \n
        https://alphapredict.neuralbytes.net'''
    }
)

firebaseConfig = {
    'apiKey': st.secrets.firebaseConfig['apiKey'],
    'authDomain': st.secrets.firebaseConfig['authDomain'],
    'databaseURL': st.secrets.firebaseConfig['databaseURL'],
    'projectId': st.secrets.firebaseConfig['projectId'],
    'storageBucket': st.secrets.firebaseConfig['storageBucket'],
    'messagingSenderId': st.secrets.firebaseConfig['messagingSenderId'],
    'appId': st.secrets.firebaseConfig['appId'],
    'measurementId': st.secrets.firebaseConfig['measurementId']
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firestore.Client.from_service_account_json("alphapredict-firebase-key.json")


def check_password():
    if 'password_correct' not in st.session_state:
        st.session_state['password_correct'] = None

    def login_form():
        st.header("Login Form")
        with st.form("Credentials"):
            st.session_state["email"] = st.text_input("Email")
            st.session_state["password"] = st.text_input("Password", type="password")
            st.form_submit_button("Log in", on_click=password_entered)
            st.caption("⬆️ Press it twice (not rapidly, though)")

    def password_entered():
        form_submitted = True
        try:
            login = auth.sign_in_with_email_and_password(st.session_state["email"], st.session_state["password"])
            print(login)
            st.session_state["password_correct"] = True
            doc_ref = db.collection("users").document(st.session_state["email"])
            doc = doc_ref.get()
            st.session_state["user_name"] = doc.to_dict()["FirstName"] + " " + doc.to_dict()["LastName"]
            st.session_state["user_plan"] = doc.to_dict()["Plan"]
            st.session_state["user_paid"] = doc.to_dict()["Paid"]
        except:
            st.session_state["password_correct"] = False
    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if login_form_submitted:
        if not st.session_state.get('password_correct'):
            st.error("😕 User not known or password incorrect")
        return False


if not check_password():
    st.stop()

# Main app starts here

tier = st.session_state["user_plan"]
paid = st.session_state["user_paid"]
tier_full_name = 'AlphaPredict' + tier
model = mappings.tier_entitlements[tier]
model_id = mappings.models[model]
st.title(tier_full_name)

if paid:
    client = OpenAI(
        api_key=st.secrets[f"OPENAI_API_KEY-{tier.upper()}_EDITION"],
        organization=st.secrets["OPENAI_ORGANIZATION_ID"],
        project=st.secrets["OPENAI_PROJECT_ID"]
    )

with st.sidebar:
    st.title('AlphaPredict')
    st.write(f'Tier: {tier}')
    st.write(f'Activated model: {model}')
    st.write("[Help improve AlphaPredict](mailto:feedback@neuralbytes.net?subject=AlphaPredict%20Feedback)")

stock_symbol = st.text_input("Enter a stock symbol", "AAPL")


def get_stock_data(symbol):
    stock = yf.Ticker(symbol)
    return stock


def display_stock_info(stock):
    st.subheader("Stock Information")
    info = stock.info
    company_name = info.get("longName", "N/A")
    exchange_code = info.get("exchange", "N/A")
    index = exchange_names.get(exchange_code, exchange_code)
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
    fig.update_layout(height=450, margin={'t': 0, 'b': 0, 'l': 0, 'r': 0})
    st.plotly_chart(fig, use_container_width=True)


def get_gpt_insights(stock_info):
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": """AlphaPredict is a professional AI stock market predictor and 
            insight-provider, with charts and company details, owned by NeuralBytes You are the AlphaPredict AI. The user 
            will provide you with data for any given stock, obtained using the yfinance API. You are to give them 
            to-the-point summaries, at the top, which are followed by more detailed insights, lists, etc. Try to do 
            your best to be as accurate as possible. You are NOT to use markdown styling such as bold, italics, etc.,
            as the Streamlit interface makes it look very bad and unprofessional. Also, there have been reports of you
            previously saying 'we cannot confirm this' or 'predicting stock market is not feasible' and similar 
            statements. AVOID that. Just do what you have been told. No ethical concerns here, as a disclaimer is 
            already issued to users."""},

            {"role": "user", "content": f"""Provide predictions for the stock for the next few days, and also for the 
            next few weeks/months/years, based on the following current/historical data: {stock_info}"""},
        ]
    )
    return response.choices[0].message.content


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
    st.subheader("\nAlphaPredict Insights")

    insights = get_gpt_insights(stock.info)

    st.markdown(insights)


footer = """<style>
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
background-color: solid;
color: grey;
text-align: center;
}
</style>
<div class='footer'>
<p>AlphaPredict is powered by artificial intelligence. Trade and invest at your own risk and think beforehand.</p>
</div>
"""

st.markdown(footer, unsafe_allow_html=True)

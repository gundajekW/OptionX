import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# გვერდის კონფიგურაცია
st.set_page_config(page_title="Professional Market Dashboard", layout="centered")

# --- 🗂️ სარჩევი / ნავიგაცია ---
st.sidebar.title("📌 ნავიგაცია")
page = st.sidebar.radio("გადასვლა გვერდზე:", [
    "📊 ოფციონების ანალიტიკა", 
    "🧠 ფუნდამენტური ჩეკლისტი",
    "⚖️ კომპანიების შედარება",
    "📅 ICT სათრეიდო ბროშურა"
])

# ==============================================================================
# 📊 გვერდი 1: ოფციონების ანალიტიკა
# ==============================================================================
if page == "📊 ოფციონების ანალიტიკა":
    st.title("📊 ოფციონების ანალიტიკა და ფასის სიგნალები")
    ticker_input = st.text_input("შეიყვანეთ აქციის თიკერი (მაგ: NVDA, AAPL, TSLA):", value="NVDA").upper().strip()
    
    if ticker_input:
        try:
            stock = yf.Ticker(ticker_input)
            if not stock.options: st.error("მონაცემები ვერ მოიძებნა.")
            else:
                selected_date = st.selectbox("აირჩიეთ ექსპირაციის თარიღი:", options=stock.options, index=0)
                history = stock.history(period="3mo")
                
                if not history.empty and len(history) > 14:
                    current_price = history["Close"].iloc[-1]
                    delta = history['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rsi = 100 - (100 / (1 + (gain / loss).iloc[-1]))
                    
                    opt = stock.option_chain(selected_date)
                    calls = opt.calls.fillna(0); puts = opt.puts.fillna(0)
                    total_call_vol = calls['volume'].sum(); total_put_vol = puts['volume'].sum()
                    pcr = total_put_vol / total_call_vol if total_call_vol > 0 else 0
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("ფასი", f"${current_price:.2f}")
                    col2.metric("PCR", f"{pcr:.2f}")
                    col3.metric("RSI", f"{rsi:.1f}")
                    
                    fig = go.Figure(data=[go.Bar(x=['Call', 'Put'], y=[total_call_vol, total_put_vol], marker_color=['#2ecc71', '#e74c3c'])])
                    fig.update_layout(title="დღევანდელი მოცულობა (Volume)", template="plotly_dark")
                    st.plotly_chart(fig, use_container_width=True)
        except Exception as e: st.error(f"შეცდომა: {e}")

# ==============================================================================
# 🧠 გვერდი 2: ფუნდამენტური ჩეკლისტი
# ==============================================================================
elif page == "🧠 ფუნდამენტური ჩეკლისტი":
    st.title("🧠 ავტომატური ფუნდამენტური ანალიზი")
    target = st.text_input("თიკერი:", value="NVDA").upper().strip()
    if target:
        with st.spinner("მიმდინარეობს ანალიზი..."):
            try:
                ticker = yf.Ticker(target); info = ticker.info; financials = ticker.financials
                st.markdown("---")
                
                # მარტივი ლოგიკა დემონსტრაციისთვის
                rev_growth = info.get('revenueGrowth', 0)
                pe = info.get('trailingPE', 0)
                
                st.checkbox(f"შემოსავლების ზრდა (>10%) ➔ {rev_growth*100:.1f}%", value=(rev_growth > 0.1), disabled=True)
                st.checkbox(f"P/E Ratio (<35) ➔ {pe:.1f}", value=(pe < 35 and pe > 0), disabled=True)
                st.info("💡 რობოტმა შეამოწმა ფინანსური მონაცემები Yahoo Finance-დან.")
            except Exception as e: st.error("მონაცემები ვერ ჩაიტვირთა.")

# ==============================================================================
# ⚖️ გვერდი 3: კომპანიების შედარება
# ==============================================================================
elif page == "⚖️ კომპანიების შედარება":
    st.title("⚖️ პირისპირ შედარება")
    colA, colB = st.columns(2)
    t1 = colA.text_input("თიკერი 1:", "NVDA")
    t2 = colB.text_input("თიკერი 2:", "AMD")
    
    if st.button("შედარება"):
        try:
            d1 = yf.Ticker(t1).info; d2 = yf.Ticker(t2).info
            data = {'მეტრიკა': ['P/E', 'Margin'], t1: [d1.get('trailingPE', 0), d1.get('profitMargins', 0)], t2: [d2.get('trailingPE', 0), d2.get('profitMargins', 0)]}
            st.table(pd.DataFrame(data))
        except: st.error("შეცდომა შედარებისას.")

# ==============================================================================
# 📅 გვერდი 4: ICT ბროშურა
# ==============================================================================
elif page == "📅 ICT სათრეიდო ბროშურა":
    st.title("📅 ICT სათრეიდო ბროშურა")
    today = datetime.today()
    start_str = (today - timedelta(days=today.weekday())).strftime("%d %B")
    end_str = (today + timedelta(days=6-today.weekday())).strftime("%d %B, %Y")
    
    st.info(f"📅 მიმდინარე კვირა: {start_str} — {end_str}")
    
    st.subheader("🤖 მაკრო დროები (NY დროით)")
    st.table(pd.DataFrame({
        "სესია": ["AM Session", "Silver Bullet", "PM Session"],
        "დრო": ["08:50-09:10", "09:50-10:10", "13:10-13:40"]
    }))
    
    st.subheader("🚨 კვირის მოვლენები")
    st.markdown("""
    * **სამშაბათი:** CPI (Judas Swing)
    * **ოთხშაბათი:** FOMC (მაღალი ვოლატილობა)
    * **ხუთშაბათი:** Jobless Claims (Silver Bullet)
    """)
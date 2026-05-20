import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import norm

# გვერდის კონფიგურაცია - მინიმალისტური და ცენტრალიზებული
st.set_page_config(page_title="Professional Market Dashboard", layout="centered")

# --- 🗂️ სარჩევი / ნავიგაცია გვერდითა პანელზე ---
st.sidebar.title("📌 ნავიგაცია")
page = st.sidebar.radio("გადადით გვერდზე:", ["📊 ოფციონების ანალიტიკა", "📰 სიახლეების ჰაბი"])

# ==============================================================================
# 📊 გვერდი 1: ოფციონების ანალიტიკა
# ==============================================================================
if page == "📊 ოფციონების ანალიტიკა":
    st.title("📊 ოფციონების ანალიტიკა და ფასის სიგნალები")
    
    ticker_input = st.text_input("შეიყვანეთ აქციის თიკერი (მაგ: NVDA, AAPL, TSLA):", value="NVDA").upper().strip()
    
    if ticker_input:
        try:
            stock = yf.Ticker(ticker_input)
            
            if not stock.options:
                st.error("ამ აქციისთვის ოფციონების მონაცემები ვერ მოიძებნა.")
            else:
                available_dates = stock.options
                selected_date = st.selectbox("აირჩიეთ ოფციონის ექსპირაციის თარიღი:", options=available_dates, index=0)
                
                history_data = stock.history(period="3mo")
                
                if not history_data.empty and len(history_data) > 14:
                    current_price = history_data["Close"].iloc[-1]
                    
                    # RSI გამოთვლა
                    delta = history_data['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs.iloc[-1]))
                    
                    # SMA 20
                    sma_20 = history_data['Close'].rolling(window=20).mean().iloc[-1]
                    price_to_sma = ((current_price - sma_20) / sma_20) * 100
                    
                    opt_chain = stock.option_chain(selected_date)
                    calls = opt_chain.calls.fillna(0)
                    puts = opt_chain.puts.fillna(0)
                    
                    # 💵 დღევანდელი მოცულობის (Volume) მაჩვენებლები
                    total_call_vol = calls['volume'].sum()
                    total_put_vol = puts['volume'].sum()
                    pcr_vol = total_put_vol / total_call_vol if total_call_vol > 0 else 0
                    
                    # 📈 ახალი: ღია პოზიციების (Open Interest) PCR
                    total_call_oi = calls['openInterest'].sum()
                    total_put_oi = puts['openInterest'].sum()
                    pcr_oi = total_put_oi / total_call_oi if total_call_oi > 0 else 0
                    
                    # --- 🧮 GEX (Gamma Exposure) გამოთვლის ფუნქცია ---
                    # ექსპირაციამდე დარჩენილი დღეების უხეში დათვლა
                    t_days = (datetime.strptime(selected_date, "%Y-%m-%d") - datetime.now()).days
                    t = max(t_days, 1) / 365.0 # წლიური დრო
                    r = 0.05 # რისკის გარეშე საპროცენტო განაკვეთი (5%)
                    
                    def calculate_gamma(df, is_call=True):
                        gammas = []
                        for _, row in df.iterrows():
                            k = row['strike']
                            iv = row.get('impliedVolatility', 0.3)
                            if iv <= 0: iv = 0.3
                            
                            d1 = (np.log(current_price / k) + (r + 0.5 * iv ** 2) * t) / (iv * np.sqrt(t))
                            gamma = norm.pdf(d1) / (current_price * iv * np.sqrt(t))
                            gammas.append(gamma if not np.isnan(gamma) else 0)
                        return gammas

                    calls['gamma'] = calculate_gamma(calls, is_call=True)
                    puts['gamma'] = calculate_gamma(puts, is_call=False)
                    
                    # GEX ფორმულა: (Call OI * Call Gamma) - (Put OI * Put Gamma)
                    # ვამრავლებთ 100-ზე (კონტრაქტის ზომა) და 1%-იან ფასის ცვლილებაზე საჩვენებლად
                    call_gex = (calls['openInterest'] * calls['gamma']).sum() * 100 * current_price * 0.01
                    put_gex = (puts['openInterest'] * puts['gamma']).sum() * 100 * current_price * 0.01
                    total_gex = call_gex - put_gex
                    
                    # რობოტის სიგნალის ალგორითმი
                    score = 0
                    if rsi > 70: score -= 2
                    elif rsi < 35: score += 2
                    if price_to_sma > 5: score -= 1 
                    elif price_to_sma < -5: score += 1 
                    if pcr_vol < 0.45: score -= 1 
                    elif pcr_vol > 1.2: score += 1 
                    
                    if score >= 2:
                        signal_text = "🟢 გაიაფებულია (გასათვალისწინებელია BUY)"
                        signal_color = "#2ecc71"
                    elif score <= -2:
                        signal_text = "🔥 გადაფასებულია / ძვირია (რისკია ყიდვა / SELL)"
                        signal_color = "#e74c3c"
                    else:
                        signal_text = "⚖️ ნეიტრალური ფასი (ბალანსი)"
                        signal_color = "#f39c12"
                    
                    # Max Pain
                    all_strikes = sorted(list(set(calls['strike']).union(set(puts['strike']))))
                    max_pain_price = all_strikes[0]
                    min_loss = float('inf')
                    for s_price in all_strikes:
                        current_loss = 0
                        current_loss += calls[calls['strike'] < s_price].apply(lambda row: (s_price - row['strike']) * row['openInterest'], axis=1).sum()
                        current_loss += puts[puts['strike'] > s_price].apply(lambda row: (row['strike'] - s_price) * row['openInterest'], axis=1).sum()
                        if current_loss < min_loss:
                            min_loss = current_loss
                            max_pain_price = s_price
                    
                    # ფასების და ინდექსების პანელი (ახლა არის 4 მაჩვენებელი)
                    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
                    with col_p1:
                        st.markdown(f'<div style="background-color: #1e293b; padding: 12px; border-radius: 10px; border-left: 5px solid #3498db; min-height: 100px;"><p style="margin: 0; font-size: 11px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">მიმდინარე ფასი</p><h3 style="margin: 0; font-size: 22px; color: #f8fafc; padding-top: 5px;">${current_price:.2f}</h3></div>', unsafe_allow_html=True)
                    with col_p2:
                        box_color = "#e74c3c" if max_pain_price < current_price else "#2ecc71"
                        st.markdown(f'<div style="background-color: #1e293b; padding: 12px; border-radius: 10px; border-left: 5px solid {box_color}; min-height: 100px;"><p style="margin: 0; font-size: 11px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">🎯 Max Pain ფასი</p><h3 style="margin: 0; font-size: 22px; color: #f8fafc; padding-top: 5px;">${max_pain_price:.2f}</h3></div>', unsafe_allow_html=True)
                    with col_p3:
                        st.markdown(f'<div style="background-color: #1e293b; padding: 12px; border-radius: 10px; border-left: 5px solid #9b59b6; min-height: 100px;"><p style="margin: 0; font-size: 11px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">📈 RSI (14D)</p><h3 style="margin: 0; font-size: 22px; color: #f8fafc; padding-top: 5px;">{rsi:.1f}</h3></div>', unsafe_allow_html=True)
                    with col_p4:
                        gex_border = "#2ecc71" if total_gex >= 0 else "#e74c3c"
                        st.markdown(f'<div style="background-color: #1e293b; padding: 12px; border-radius: 10px; border-left: 5px solid {gex_border}; min-height: 100px;"><p style="margin: 0; font-size: 11px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">⚡ Net GEX (1%)</p><h3 style="margin: 0; font-size: 20px; color: #f8fafc; padding-top: 5px;">{total_gex:,.0f} sh</h3></div>', unsafe_allow_html=True)
                    
                    st.markdown(f'<div style="background-color: #1e293b; padding: 18px; border-radius: 10px; text-align: center; border: 2px solid {signal_color}; margin-top: 15px; margin-bottom: 25px;"><span style="color: #94a3b8; font-size: 13px; font-weight: bold; text-transform: uppercase; display: block; margin-bottom: 5px;">🤖 ფასის მდგომარეობის სიგნალი</span><span style="color: {signal_color}; font-size: 22px; font-weight: bold;">{signal_text}</span></div>', unsafe_allow_html=True)
                    
                    # ორი PCR გვერდი-გვერდ
                    col_pcr1, col_pcr2 = st.columns(2)
                    with col_pcr1:
                        st.metric(label="Put-Call Ratio (დღევანდელი მოცულობა - Volume)", value=f"{pcr_vol:.2f}")
                    with col_pcr2:
                        st.metric(label="📊 Put-Call Ratio (ღია პოზიციები - Open Interest)", value=f"{pcr_oi:.2f}")
                    
                    st.write("") # დაცილება
                    
                    # ჩარტი 1
                    fig_vol = go.Figure(data=[go.Bar(x=['Call ოფციონები', 'Put ოფციონები'], y=[total_call_vol, total_put_vol], marker_color=['#2ecc71', '#e74c3c'], text=[f"{int(total_call_vol):,}", f"{int(total_put_vol):,}"], textposition='auto')])
                    fig_vol.update_layout(title="დღევანდელი ჯამური მოცულობა (Volume)", template="plotly_dark", height=300)
                    st.plotly_chart(fig_vol, use_container_width=True, config={'displayModeBar': False})
                    
                    st.markdown("---")
                    
                    # ჩარტი 2
                    st.subheader("🎯 Open Interest კედლები (Strikes-ის მიხედვით)")
                    calls_filtered = calls[['strike', 'openInterest']].rename(columns={'openInterest': 'Call OI'})
                    puts_filtered = puts[['strike', 'openInterest']].rename(columns={'openInterest': 'Put OI'})
                    df_oi = calls_filtered.merge(puts_filtered, on='strike', how='outer').fillna(0)
                    df_oi['strike_diff'] = (df_oi['strike'] - current_price).abs()
                    df_oi = df_oi.sort_values('strike_diff').head(20).sort_values('strike')
                    
                    fig_oi = go.Figure()
                    fig_oi.add_trace(go.Bar(x=df_oi['strike'], y=df_oi['Call OI'], name='Call Open Interest', marker_color='#2ecc71'))
                    fig_oi.add_trace(go.Bar(x=df_oi['strike'], y=df_oi['Put OI'], name='Put Open Interest', marker_color='#e74c3c'))
                    fig_oi.update_layout(barmode='group', template="plotly_dark", height=400)
                    st.plotly_chart(fig_oi, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.error("ტექნიკური ანალიზისთვის საჭირო ისტორიული მონაცემები ვერ ჩაიტვირთა.")
        except Exception as e:
            st.error(f"შეცდომა მონაცემების დამუშავებისას: {e}")

# ==============================================================================
# 📰 გვერდი 2: სიახლეების ჰაბი
# ==============================================================================
elif page == "📰 სიახლეების ჰაბი":
    st.title("📰 ბაზრის უახლესი სიახლეები (Market News)")
    st.write("მიიღეთ რეალურ დროში განახლებული უმნიშვნელოვანესი ფინანსური სიახლეები Wall Street-იდან.")
    
    news_ticker = st.text_input("შეიყვანეთ აქციის თიკერი ნიუსებისთვის:", value="NVDA").upper().strip()
    
    if news_ticker:
        try:
            stock_news = yf.Ticker(news_ticker)
            news_list = stock_news.news
            
            if not news_list:
                st.info(f"📍 {news_ticker}-ის შესახებ ბოლო პერიოდის სიახლეები ვერ მოიწვდინა.")
            else:
                st.subheader(f"🔥 უახლესი სტატიები: {news_ticker}")
                
                for article in news_list[:8]:
                    content_data = article.get('content', article)
                    title = content_data.get('title', '') or article.get('title', 'სათაური მიუწვდომელია')
                    
                    publisher_info = content_data.get('provider', {}) or content_data.get('publisher', {})
                    if isinstance(publisher_info, dict):
                        publisher = publisher_info.get('name', 'Yahoo Finance')
                    else:
                        publisher = str(publisher_info) or 'Yahoo Finance'
                    
                    link = content_data.get('clickThroughUrl', {}) or content_data.get('link', '#')
                    if isinstance(link, dict):
                        link = link.get('url', '#')
                    
                    provider_time = content_data.get('pubDate', 0) or content_data.get('providerPublishTime', 0)
                    if isinstance(provider_time, int) and provider_time > 0:
                        date_str = datetime.fromtimestamp(provider_time).strftime('%Y-%m-%d %H:%M')
                    elif isinstance(provider_time, str):
                        try:
                            date_str = provider_time.replace('T', ' ').split('.')[0]
                        except:
                            date_str = provider_time
                    else:
                        date_str = "ცოტა ხნის წინ"
                    
                    st.markdown(f"""
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 3px solid #9b59b6;">
                        <span style="color: #94a3b8; font-size: 11px; font-weight: bold;">{publisher} • 📅 {date_str}</span>
                        <h4 style="margin: 5px 0 10px 0;"><a href="{link}" target="_blank" style="color: #3498db; text-decoration: none;">{title}</a></h4>
                    </div>
                    """, unsafe_allow_html=True)
                    
        except Exception as e:
            st.error(f"სიახლეების ჩატვირთვისას დაფიქსირდა შეცდომა: {e}")
            
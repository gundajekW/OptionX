import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# გვერდის კონფიგურაცია - მინიმალისტური და ცენტრალიზებული
st.set_page_config(page_title="Professional Market Dashboard", layout="centered")

# --- 🗂️ სარჩევი / ნავიგაცია გვერდითა პანელზე ---
st.sidebar.title("📌 ნავიგაცია")
page = st.sidebar.radio("გადასვლა გვერდზე:", [
    "📊 ოფციონების ანალიტიკა", 
    "🧠 ფუნდამენტური ჩეკლისტი"
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
                    total_call_vol = calls['volume'].sum()
                    total_put_vol = puts['volume'].sum()
                    pcr = total_put_vol / total_call_vol if total_call_vol > 0 else 0
                    
                    # რობოტის სიგნალი
                    score = 0
                    if rsi > 70: score -= 2  
                    elif rsi < 35: score += 2 
                    if price_to_sma > 5: score -= 1 
                    elif price_to_sma < -5: score += 1 
                    if pcr < 0.45: score -= 1 
                    elif pcr > 1.2: score += 1 
                    
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
                    
                    # 3-სვეტიანი პანელი
                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1:
                        st.markdown(f'<div style="background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 5px solid #3498db; min-height: 110px;"><p style="margin: 0; font-size: 13px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">მიმდინარე ფასი</p><h2 style="margin: 0; font-size: 26px; color: #f8fafc; padding-top: 5px;">${current_price:.2f}</h2></div>', unsafe_allow_html=True)
                    with col_p2:
                        box_color = "#e74c3c" if max_pain_price < current_price else "#2ecc71"
                        st.markdown(f'<div style="background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 5px solid {box_color}; min-height: 110px;"><p style="margin: 0; font-size: 13px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">🎯 Max Pain ფასი</p><h2 style="margin: 0; font-size: 26px; color: #f8fafc; padding-top: 5px;">${max_pain_price:.2f}</h2></div>', unsafe_allow_html=True)
                    with col_p3:
                        tooltip_text = "💡 RSI ზონები: >70 გადახურებულია (ძვირია) | <30 გაუფასურებულია (იაფია) | 30-70 ნეიტრალურია."
                        st.markdown(f'<div title="{tooltip_text}" style="background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 5px solid #9b59b6; min-height: 110px; cursor: help;"><p style="margin: 0; font-size: 13px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">📈 RSI ინდექსი (14D) ℹ️</p><h2 style="margin: 0; font-size: 26px; color: #f8fafc; padding-top: 5px;">{rsi:.1f}</h2></div>', unsafe_allow_html=True)
                
                    st.markdown(f'<div style="background-color: #1e293b; padding: 18px; border-radius: 10px; text-align: center; border: 2px solid {signal_color}; margin-top: 15px; margin-bottom: 25px;"><span style="color: #94a3b8; font-size: 13px; font-weight: bold; text-transform: uppercase; display: block; margin-bottom: 5px;">🤖 ფასის მდგომარეობის სიგნალი</span><span style="color: {signal_color}; font-size: 22px; font-weight: bold;">{signal_text}</span></div>', unsafe_allow_html=True)
                    
                    # ჩარტი 1
                    fig_vol = go.Figure(data=[go.Bar(x=['Call ოფციონები', 'Put ოფციონები'], y=[total_call_vol, total_put_vol], marker_color=['#2ecc71', '#e74c3c'], text=[f"{int(total_call_vol):,}", f"{int(total_put_vol):,}"], textposition='auto')])
                    fig_vol.update_layout(title="დღევანდელი ჯამური მოცულობა (Volume)", template="plotly_dark", height=300)
                    
                    col_left, col_right = st.columns([1, 2])
                    with col_left:
                        st.metric(label="Put-Call Ratio (PCR)", value=f"{pcr:.2f}")
                        if pcr > 1: st.error("📉 განწყობა: BEARISH")
                        else: st.success("📈 განწყობა: BULLISH")
                    with col_right:
                        st.plotly_chart(fig_vol, use_container_width=True, config={'displayModeBar': False})
                    
                    # საინფორმაციო ბლოკი
                    st.markdown(f"""
                    <div style="background-color: #1e2e3d; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db; margin-top: 20px; margin-bottom: 20px;">
                        <p style="margin: 0; font-size: 13px; color: #3498db; font-weight: bold; text-transform: uppercase; margin-bottom: 5px;">💡 საექსპირაციო კონტრაქტების ლოგიკა</p>
                        <p style="margin: 0; font-size: 13.5px; color: #cbd5e1; line-height: 1.5;">
                            ზემოთ მოცემული <b>მოცულობა (Volume)</b> ყოველთვის აჩვენებს <b>მხოლოდ დღევანდელ აქტივობას</b>. 
                            თარიღის შეცვლისას თქვენ ხედავთ, თუ რამდენი კონტრაქტი გაიყიდა დღეს სპეციალურად იმ კონკრეტული ექსპირაციის დღისთვის ({selected_date}).
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # ჩარტი 2
                    st.subheader(f"🎯 Open Interest კედლები (სტრაიკების მიხედვით: {selected_date})")
                    calls_filtered = calls[['strike', 'openInterest']].rename(columns={'openInterest': 'Call OI'})
                    puts_filtered = puts[['strike', 'openInterest']].rename(columns={'openInterest': 'Put OI'})
                    df_oi = calls_filtered.merge(puts_filtered, on='strike', how='outer').fillna(0)
                    df_oi['strike_diff'] = (df_oi['strike'] - current_price).abs()
                    df_oi = df_oi.sort_values('strike_diff').head(20).sort_values('strike')
                    
                    fig_oi = go.Figure()
                    fig_oi.add_trace(go.Bar(x=df_oi['strike'], y=df_oi['Call OI'], name='Call Open Interest', marker_color='#2ecc71'))
                    fig_oi.add_trace(go.Bar(x=df_oi['strike'], y=df_oi['Put OI'], name='Put Open Interest', marker_color='#e74c3c'))
                    fig_oi.update_layout(xaxis_title="სტრაიკ ფასი ($)", yaxis_title="ღია კონტრაქტების რაოდენობა", barmode='group', template="plotly_dark", height=400)
                    st.plotly_chart(fig_oi, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.error("ტექნიკური ანალიზისთვის საჭირო ისტორიული მონაცემები ვერ ჩაიტვირთა.")
        except Exception as e:
            st.error(f"შეცდომა მონაცემების დამუშავებისას: {e}")

# ==============================================================================
# 🧠 გვერდი 2: ავტომატიზირებული ფუნდამენტური ჩეკლისტი
# ==============================================================================
elif page == "🧠 ფუნდამენტური ჩეკლისტი":
    st.title("🧠 ავტომატური ფუნდამენტური ანალიზის ჰაბი")
    st.write("შეიყვანეთ თიკერი და საიტი ავტომატურად გაანალიზებს Yahoo Finance-ის ფინანსურ უწყისებს (10-K/10-Q).")
    
    target_stock = st.text_input("შეიყვანეთ აქციის თიკერი (მაგ: NVDA, AAPL, MSFT):", value="NVDA").upper().strip()
    
    if target_stock:
        with st.spinner("მიმდინარეობს ფინანსური უწყისების ანალიზი..."):
            try:
                ticker = yf.Ticker(target_stock)
                info = ticker.info
                financials = ticker.financials
                cashflow = ticker.cashflow
                
                # ინიციალიზაცია (ავტომატური მონიშვნის ბულეანები)
                auto_ch = [False] * 14
                
                if not financials.empty and 'Total Revenue' in financials.index:
                    # 1. შემოსავლების და EPS ზრდა
                    rev_row = financials.loc['Total Revenue']
                    if len(rev_row) >= 2 and rev_row.iloc[0] > rev_row.iloc[1]:
                        auto_ch[0] = True
                    
                    # 2. Gross Margin > 50%
                    if 'Gross Profit' in financials.index:
                        gp = financials.loc['Gross Profit'].iloc[0]
                        rev = financials.loc['Total Revenue'].iloc[0]
                        if rev > 0 and (gp / rev) > 0.50:
                            auto_ch[1] = True
                            
                # 3. Debt to Equity < 150%
                d2e = info.get('debtToEquity', 0)
                if d2e and d2e < 150:
                    auto_ch[2] = True
                    
                # 4. Free Cash Flow ზრდა
                if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
                    fcf_row = cashflow.loc['Free Cash Flow']
                    if len(fcf_row) >= 2 and fcf_row.iloc[0] > fcf_row.iloc[1]:
                        auto_ch[3] = True
                        
                # 5. P/E Ratio სექტორთან მიმართებაში (ზოგადი ფილტრი < 35 ან არსებობა)
                pe = info.get('trailingPE', None)
                if pe and pe < 35:
                    auto_ch[4] = True
                    
                # 6. PEG Ratio < 1.2
                peg = info.get('pegRatio', None)
                if peg and peg <= 1.2:
                    auto_ch[5] = True
                    
                # 7. Pricing Power (Operating Margins > 15%)
                op_margin = info.get('operatingMargins', 0)
                if op_margin and op_margin > 0.15:
                    auto_ch[6] = True
                    
                # 8. Switching Costs / სტაბილური შემოსავალი (Return on Equity > 15%)
                roe = info.get('returnOnEquity', 0)
                if roe and roe > 0.15:
                    auto_ch[7] = True
                    
                # 9. ინოვაციები (R&D ხარჯები არსებობს და დიდია)
                if 'Research And Development' in financials.index and financials.loc['Research And Development'].iloc[0] > 0:
                    auto_ch[8] = True
                    
                # 10. Share Buybacks (Repurchase of Capital Stock არსებობს ქეშფლოუში)
                if not cashflow.empty and 'Repurchase Of Capital Stock' in cashflow.index:
                    if abs(cashflow.loc['Repurchase Of Capital Stock'].fillna(0).iloc[0]) > 0:
                        auto_ch[9] = True
                
                # 11. ინსაიდერების წილი (> 0.1% ან მენეჯმენტის ფლობა)
                if info.get('heldPercentInsiders', 0) > 0.001:
                    auto_ch[10] = True
                    
                # 12. TAM (საბაზრო კაპიტალიზაცია > $10B - დიდი პოტენციალი)
                if info.get('marketCap', 0) > 10_000_000_000:
                    auto_ch[11] = True
                    
                # 13. ინდუსტრიული ქარი (Revenue Growth > 10% წლიური)
                rev_growth = info.get('revenueGrowth', 0)
                if rev_growth and rev_growth > 0.10:
                    auto_ch[12] = True
                    
                # 14. კაპიტალის გონივრული განაწილება (ROA > 7%)
                roa = info.get('returnOnAssets', 0)
                if roa and roa > 0.07:
                    auto_ch[13] = True

                # --- 🏛️ ვიზუალური ნაწილი და ჩეკლისტების ჩვენება ---
                st.markdown("---")
                
                # სექცია 1
                st.markdown("<div style='background-color: #1e293b; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #3498db;'><b>1. 📊 ფინანსური ჯანმრთელობა (Financial Metrics)</b></div>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    ch1 = st.checkbox("შემოსავლები და EPS სტაბილურად იზრდება", value=auto_ch[0], disabled=True)
                    ch2 = st.checkbox("Gross Margin მაღალია (>50%)", value=auto_ch[1], disabled=True)
                with col2:
                    ch3 = st.checkbox("Debt-to-Equity (ვალი) ნორმაშია", value=auto_ch[2], disabled=True)
                    ch4 = st.checkbox("თავისუფალი ფულადი ნაკადი (FCF) იზრდება", value=auto_ch[3], disabled=True)

                # სექცია 2
                st.markdown("<div style='background-color: #1e293b; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #e74c3c;'><b>2. 💸 კომპანიის შეფასება (Valuation)</b></div>", unsafe_allow_html=True)
                col3, col4 = st.columns(2)
                with col3:
                    ch5 = st.checkbox("P/E Ratio ადეკვატურია (<35)", value=auto_ch[4], disabled=True)
                with col4:
                    ch6 = st.checkbox("PEG Ratio <= 1.2 (დაბალი ფასი ზრდასთან)", value=auto_ch[5], disabled=True)

                # სექცია 3
                st.markdown("<div style='background-color: #1e293b; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #f1c40f;'><b>3. 🛡️ კონკურენტული უპირატესობა (The Economic Moat)</b></div>", unsafe_allow_html=True)
                ch7 = st.checkbox("Pricing Power (მაღალი საოპერაციო მარჟა >15%)", value=auto_ch[6], disabled=True)
                ch8 = st.checkbox("კომპანიის ეფექტურობა / ქსელური ეფექტი (ROE >15%)", value=auto_ch[7], disabled=True)

                # სექცია 4
                st.markdown("<div style='background-color: #1e293b; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #2ecc71;'><b>4. 🚀 ზრდის კატალიზატორები (Future Catalysts)</b></div>", unsafe_allow_html=True)
                col5, col6 = st.columns(2)
                with col5:
                    ch9 = st.checkbox("ინოვაციები (R&D ბიუჯეტი აქტიურია)", value=auto_ch[8], disabled=True)
                    ch10 = st.checkbox("კომპანია ყიდულობს საკუთარ აქციებს (Buybacks)", value=auto_ch[9], disabled=True)
                with col6:
                    ch11 = st.checkbox("ინსაიდერების აქტიური წილი ბიზნესში", value=auto_ch[10], disabled=True)
                    ch12 = st.checkbox("TAM / მასშტაბურობა (Market Cap > $10B)", value=auto_ch[11], disabled=True)

                # სექცია 5
                st.markdown("<div style='background-color: #1e293b; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #9b59b6;'><b>5. 🌍 სტრატეგიული გარემო და მენეჯმენტი</b></div>", unsafe_allow_html=True)
                ch13 = st.checkbox("სექტორული ზურგის ქარი (Revenue Growth >10%)", value=auto_ch[12], disabled=True)
                ch14 = st.checkbox("კაპიტალის ეფექტური განაწილება მენეჯმენტის მიერ (ROA >7%)", value=auto_ch[13], disabled=True)

                st.markdown("---")
                
                # 🎯 შედეგების დათვლა
                score = sum(auto_ch)
                st.subheader("📝 რობოტის ავტომატური დასკვნა")
                st.write(f"**აქცია:** `{target_stock}` | **დაკმაყოფილებული კრიტერიუმები:** `{score} / 14`")
                st.progress(score / 14)
                
                if score >= 11:
                    st.success(f"🟢 **უმაღლესი ხარისხი!** `{target_stock}` ფუნდამენტალურად სრულიად მყარია. რობოტი უწევს რეკომენდაციას გრძელვადიანი პორტფელისთვის.")
                elif 6 <= score <= 10:
                    st.warning(f"🟡 **საშუალო პოტენციალი.** კომპანია კარგია, თუმცა ბაზარზე აქვს რამდენიმე გამოკვეთილი სუსტი წერტილი. საჭიროებს გადამოწმებას.")
                else:
                    st.error(f"🔴 **მაღალი რისკი / ძვირია.** ფუნდამენტური ციფრები ან კოეფიციენტები არადამაკმაყოფილებელია. ინვესტიცია სახიფათოა.")
                    
            except Exception as e:
                st.error(f"Yahoo Finance-დან ფუნდამენტური მონაცემების დამუშავება ვერ მოხერხდა: {e}")
                
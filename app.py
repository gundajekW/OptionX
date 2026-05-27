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
    "🧠 ფუნდამენტური ჩეკლისტი",
    "⚖️ კომპანიების შედარება"
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
                    
                    delta = history_data['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs.iloc[-1]))
                    
                    sma_20 = history_data['Close'].rolling(window=20).mean().iloc[-1]
                    price_to_sma = ((current_price - sma_20) / sma_20) * 100
                    
                    opt_chain = stock.option_chain(selected_date)
                    calls = opt_chain.calls.fillna(0)
                    puts = opt_chain.puts.fillna(0)
                    total_call_vol = calls['volume'].sum()
                    total_put_vol = puts['volume'].sum()
                    pcr = total_put_vol / total_call_vol if total_call_vol > 0 else 0
                    
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
                    
                    fig_vol = go.Figure(data=[go.Bar(x=['Call ოფციონები', 'Put ოფციონები'], y=[total_call_vol, total_put_vol], marker_color=['#2ecc71', '#e74c3c'], text=[f"{int(total_call_vol):,}", f"{int(total_put_vol):,}"], textposition='auto')])
                    fig_vol.update_layout(title="დღევანდელი ჯამური მოცულობა (Volume)", template="plotly_dark", height=300)
                    
                    col_left, col_right = st.columns([1, 2])
                    with col_left:
                        st.metric(label="Put-Call Ratio (PCR)", value=f"{pcr:.2f}")
                        if pcr > 1: st.error("📉 განწყობა: BEARISH")
                        else: st.success("📈 განწყობა: BULLISH")
                    with col_right:
                        st.plotly_chart(fig_vol, use_container_width=True, config={'displayModeBar': False})
                    
                    st.markdown(f"""
                    <div style="background-color: #1e2e3d; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db; margin-top: 20px; margin-bottom: 20px;">
                        <p style="margin: 0; font-size: 13px; color: #3498db; font-weight: bold; text-transform: uppercase; margin-bottom: 5px;">💡 საექსპირაციო კონტრაქტების ლოგიკა</p>
                        <p style="margin: 0; font-size: 13.5px; color: #cbd5e1; line-height: 1.5;">
                            ზემოთ მოცემული <b>მოცულობა (Volume)</b> ყოველთვის აჩვენებს <b>მხოლოდ დღევანდელ აქტივობას</b>. 
                            თარიღის შეცვლისას თქვენ ხედავთ, თუ რამდენი კონტრაქტი გაიყიდა დღეს სპეციალურად იმ კონკრეტული ექსპირაციის დღისთვის ({selected_date}).
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
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
    st.title("🧠 ფუნდამენტური ანალიზის ჰაბი")
    st.write("შეიყვანეთ თიკერი და საიტი ავტომატურად გაანალიზებს Yahoo Finance-ის ფინანსურ უწყისებს (10-K/10-Q).")
    
    target_stock = st.text_input("შეიყვანეთ აქციის თიკერი (მაგ: NVDA, AAPL):", value="NVDA").upper().strip()
    
    if target_stock:
        with st.spinner("მიმდინარეობს ფინანსური უწყისების ანალიზი..."):
            try:
                ticker = yf.Ticker(target_stock)
                info = ticker.info
                financials = ticker.financials
                cashflow = ticker.cashflow
                
                auto_ch = [False] * 14
                v_rev_growth = "N/A"; v_margin = "N/A"; v_d2e = "N/A"; v_fcf_growth = "N/A"
                v_pe = "N/A"; v_peg = "N/A"; v_op_margin = "N/A"; v_roe = "N/A"
                v_rd = "N/A"; v_buyback = "N/A"; v_insider = "N/A"; v_cap = "N/A"
                v_rev_growth_info = "N/A"; v_roa = "N/A"
                
                if not financials.empty and 'Total Revenue' in financials.index:
                    rev_row = financials.loc['Total Revenue'].dropna()
                    if len(rev_row) >= 2 and rev_row.iloc[1] != 0:
                        growth = ((rev_row.iloc[0] - rev_row.iloc[1]) / abs(rev_row.iloc[1])) * 100
                        v_rev_growth = f"{growth:+.1f}%"
                        if growth > 0: auto_ch[0] = True
                        
                    if 'Gross Profit' in financials.index:
                        gp = financials.loc['Gross Profit'].iloc[0]
                        rev = financials.loc['Total Revenue'].iloc[0]
                        if rev > 0:
                            margin_pct = (gp / rev) * 100
                            v_margin = f"{margin_pct:.1f}%"
                            if margin_pct > 50: auto_ch[1] = True

                d2e = info.get('debtToEquity', None)
                if d2e is not None:
                    v_d2e = f"{d2e:.1f}%"
                    if d2e < 150: auto_ch[2] = True

                if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
                    fcf_row = cashflow.loc['Free Cash Flow'].dropna()
                    if len(fcf_row) >= 2 and fcf_row.iloc[1] != 0:
                        fcf_growth = ((fcf_row.iloc[0] - fcf_row.iloc[1]) / abs(fcf_row.iloc[1])) * 100
                        v_fcf_growth = f"{fcf_growth:+.1f}%"
                        if fcf_growth > 0: auto_ch[3] = True

                pe = info.get('trailingPE', None)
                if pe is not None:
                    v_pe = f"{pe:.1f}"
                    if pe < 35: auto_ch[4] = True

                peg = info.get('pegRatio', None)
                if peg is not None:
                    v_peg = f"{peg:.2f}"
                    if peg <= 1.2: auto_ch[5] = True

                op_margin = info.get('operatingMargins', None)
                if op_margin is not None:
                    v_op_margin = f"{op_margin*100:.1f}%"
                    if op_margin > 0.15: auto_ch[6] = True

                roe = info.get('returnOnEquity', None)
                if roe is not None:
                    v_roe = f"{roe*100:.1f}%"
                    if roe > 0.15: auto_ch[7] = True

                if not financials.empty and 'Research And Development' in financials.index:
                    rd_val = financials.loc['Research And Development'].iloc[0]
                    if pd.notna(rd_val) and rd_val > 0:
                        v_rd = f"${rd_val / 1e9:.2f}B"
                        auto_ch[8] = True
                    else: v_rd = "$0"

                if not cashflow.empty and 'Repurchase Of Capital Stock' in cashflow.index:
                    buyback_val = cashflow.loc['Repurchase Of Capital Stock'].fillna(0).iloc[0]
                    if abs(buyback_val) > 0:
                        v_buyback = f"✅ კი (${abs(buyback_val) / 1e9:.2f}B)"
                        auto_ch[9] = True
                    else: v_buyback = "❌ არა"

                insider = info.get('heldPercentInsiders', None)
                if insider is not None:
                    v_insider = f"{insider*100:.2f}%"
                    if insider > 0.001: auto_ch[10] = True

                cap = info.get('marketCap', None)
                if cap is not None:
                    v_cap = f"${cap / 1e9:.1f}B"
                    if cap > 10_000_000_000: auto_ch[11] = True

                rev_growth_info = info.get('revenueGrowth', None)
                if rev_growth_info is not None:
                    v_rev_growth_info = f"{rev_growth_info*100:+.1f}%"
                    if rev_growth_info > 0.10: auto_ch[12] = True

                roa = info.get('returnOnAssets', None)
                if roa is not None:
                    v_roa = f"{roa*100:.1f}%"
                    if roa > 0.07: auto_ch[13] = True

                st.markdown("---")
                
                st.markdown("<div style='background-color: #1e293b; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #3498db;'><b>1. 📊 ფინანსური ჯანმრთელობა</b></div>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    st.checkbox(f"შემოსავლების ზრდა (წლიური) ➔ [ {v_rev_growth} ]", value=auto_ch[0], disabled=True, help="ზომავს იზრდება თუ არა ბიზნესის შემოსავალი წინა წელთან შედარებით.")
                    st.checkbox(f"Gross Margin (>50%) ➔ [ {v_margin} ]", value=auto_ch[1], disabled=True, help="50%-ზე მაღალი მარჟა ნიშნავს, რომ კომპანიას პროდუქტის შექმნა იაფი უჯდება.")
                with col2:
                    st.checkbox(f"Debt-to-Equity (ვალი) ➔ [ {v_d2e} ]", value=auto_ch[2], disabled=True, help="150%-ზე დაბალი მაჩვენებელი მიუთითებს უსაფრთხო ვალის დონეზე.")
                    st.checkbox(f"თავისუფალი ქეშის (FCF) ზრდა ➔ [ {v_fcf_growth} ]", value=auto_ch[3], disabled=True, help="აჩვენებს იზრდება თუ არა სუფთა 'ქეში', რაც კომპანიას რჩება ხარჯების შემდეგ.")

                st.markdown("<div style='background-color: #1e293b; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #e74c3c;'><b>2. 💸 კომპანიის შეფასება (Valuation)</b></div>", unsafe_allow_html=True)
                col3, col4 = st.columns(2)
                with col3:
                    st.checkbox(f"P/E Ratio (<35) ➔ [ {v_pe} ]", value=auto_ch[4], disabled=True, help="35-ზე დაბალი ნიშნავს, რომ ფასი ბუშტივით არ არის გაბერილი.")
                with col4:
                    st.checkbox(f"PEG Ratio (<=1.2) ➔ [ {v_peg} ]", value=auto_ch[5], disabled=True, help="აფასებს ფასს ზრდასთან მიმართებაში. 1.2-ზე დაბალი ნიშნავს, რომ ზრდასთან შედარებით იაფია.")

                st.markdown("<div style='background-color: #1e293b; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #f1c40f;'><b>3. 🛡️ კონკურენტული უპირატესობა</b></div>", unsafe_allow_html=True)
                st.checkbox(f"Pricing Power / Op. Margin (>15%) ➔ [ {v_op_margin} ]", value=auto_ch[6], disabled=True, help="საოპერაციო მარჟა. 15%-ზე მაღალი ნიშნავს ძლიერ უპირატესობას და ფასების კარნახის უნარს.")
                st.checkbox(f"ბიზნესის ეფექტურობა / ROE (>15%) ➔ [ {v_roe} ]", value=auto_ch[7], disabled=True, help="Return on Equity. ზომავს მენეჯმენტის ეფექტურობას ინვესტორების ფულზე.")

                st.markdown("<div style='background-color: #1e293b; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #2ecc71;'><b>4. 🚀 ზრდის კატალიზატორები</b></div>", unsafe_allow_html=True)
                col5, col6 = st.columns(2)
                with col5:
                    st.checkbox(f"R&D ბიუჯეტი ➔ [ {v_rd} ]", value=auto_ch[8], disabled=True, help="წლიური დანახარჯი კვლევებსა და ახალ ტექნოლოგიებში.")
                    st.checkbox(f"აქციების უკან გამოსყიდვა ➔ [ {v_buyback} ]", value=auto_ch[9], disabled=True, help="ყიდულობს თუ არა კომპანია საკუთარ აქციებს.")
                with col6:
                    st.checkbox(f"ინსაიდერების წილი ➔ [ {v_insider} ]", value=auto_ch[10], disabled=True, help="მენეჯმენტის საკუთრებაში არსებული აქციების წილი.")
                    st.checkbox(f"TAM (Market Cap > $10B) ➔ [ {v_cap} ]", value=auto_ch[11], disabled=True, help="კომპანიის საბაზრო კაპიტალიზაცია. 10B+ ნიშნავს ფინანსურ სტაბილურობას.")

                st.markdown("<div style='background-color: #1e293b; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #9b59b6;'><b>5. 🌍 სტრატეგიული გარემო</b></div>", unsafe_allow_html=True)
                st.checkbox(f"ინდუსტრიული ქარი / Rev Growth (>10%) ➔ [ {v_rev_growth_info} ]", value=auto_ch[12], disabled=True, help="წლიური (YoY) ზრდის ტემპი კვარტალურად.")
                st.checkbox(f"კაპიტალის განაწილება / ROA (>7%) ➔ [ {v_roa} ]", value=auto_ch[13], disabled=True, help="რამდენად ეფექტურად იყენებს კომპანია თავის აქტივებს.")

                st.markdown("---")
                score = sum(auto_ch)
                st.subheader("📝 რობოტის ავტომატური დასკვნა")
                st.write(f"**აქცია:** `{target_stock}` | **დაკმაყოფილებული კრიტერიუმები:** `{score} / 14`")
                st.progress(score / 14)
                
                if score >= 11: st.success("🟢 უმაღლესი ხარისხი! ფუნდამენტალურად სრულიად მყარია.")
                elif 6 <= score <= 10: st.warning("🟡 საშუალო პოტენციალი. საჭიროებს გადამოწმებას.")
                else: st.error("🔴 მაღალი რისკი / ძვირია. ინვესტიცია სახიფათოა.")
                    
            except Exception as e:
                st.error(f"Yahoo Finance-დან მონაცემების დამუშავება ვერ მოხერხდა: {e}")

# ==============================================================================
# ⚖️ გვერდი 3: კომპანიების შედარება
# ==============================================================================
elif page == "⚖️ კომპანიების შედარება":
    st.title("⚖️ აქციების პირისპირ შედარება (Relative Valuation)")
    st.write("შეადარეთ ორი კონკურენტი კომპანია ერთმანეთს, რათა იპოვოთ საუკეთესო Value.")

    colA, colB = st.columns(2)
    with colA:
        ticker1 = st.text_input("პირველი კომპანია (მაგ: NVDA):", value="NVDA").upper().strip()
    with colB:
        ticker2 = st.text_input("მეორე კომპანია (მაგ: AMD):", value="AMD").upper().strip()

    if ticker1 and ticker2:
        if st.button("🚀 მონაცემების შედარება"):
            with st.spinner("მიმდინარეობს კომპანიების სკანირება..."):
                try:
                    t1 = yf.Ticker(ticker1).info
                    t2 = yf.Ticker(ticker2).info

                    def get_metric(data, key):
                        val = data.get(key)
                        return val if val is not None else 0

                    cap1 = get_metric(t1, 'marketCap')
                    cap2 = get_metric(t2, 'marketCap')
                    
                    pe1 = get_metric(t1, 'trailingPE')
                    pe2 = get_metric(t2, 'trailingPE')
                    peg1 = get_metric(t1, 'pegRatio')
                    peg2 = get_metric(t2, 'pegRatio')
                    
                    margin1 = get_metric(t1, 'profitMargins')
                    margin2 = get_metric(t2, 'profitMargins')
                    roe1 = get_metric(t1, 'returnOnEquity')
                    roe2 = get_metric(t2, 'returnOnEquity')
                    
                    debt1 = get_metric(t1, 'debtToEquity')
                    debt2 = get_metric(t2, 'debtToEquity')
                    
                    st.markdown(f"### 🥊 {ticker1} vs {ticker2}")
                    
                    def highlight_higher(val1, val2, is_pct=False):
                        fmt = lambda x: f"{x*100:.2f}%" if is_pct else f"{x:.2f}"
                        if val1 == 0 and val2 == 0: return "N/A", "N/A"
                        if val1 > val2: return f"<span style='color:#2ecc71; font-weight:bold;'>{fmt(val1)} 🏆</span>", fmt(val2)
                        elif val2 > val1: return fmt(val1), f"<span style='color:#2ecc71; font-weight:bold;'>{fmt(val2)} 🏆</span>"
                        else: return fmt(val1), fmt(val2)

                    def highlight_lower(val1, val2, is_pct=False):
                        fmt = lambda x: f"{x*100:.2f}%" if is_pct else f"{x:.2f}"
                        if val1 == 0 and val2 == 0: return "N/A", "N/A"
                        if val1 == 0: return "N/A", f"<span style='color:#2ecc71; font-weight:bold;'>{fmt(val2)} 🏆</span>"
                        if val2 == 0: return f"<span style='color:#2ecc71; font-weight:bold;'>{fmt(val1)} 🏆</span>", "N/A"
                        
                        if val1 < val2: return f"<span style='color:#2ecc71; font-weight:bold;'>{fmt(val1)} 🏆</span>", fmt(val2)
                        elif val2 < val1: return fmt(val1), f"<span style='color:#2ecc71; font-weight:bold;'>{fmt(val2)} 🏆</span>"
                        else: return fmt(val1), fmt(val2)

                    pe1_str, pe2_str = highlight_lower(pe1, pe2)
                    peg1_str, peg2_str = highlight_lower(peg1, peg2)
                    margin1_str, margin2_str = highlight_higher(margin1, margin2, True)
                    roe1_str, roe2_str = highlight_higher(roe1, roe2, True)
                    debt1_str, debt2_str = highlight_lower(debt1, debt2)

                    html_table = f"""
                    <table style="width:100%; text-align:left; border-collapse: collapse; background-color:#1e293b; color:white; border-radius: 10px; overflow: hidden;">
                        <tr style="background-color:#0f172a; border-bottom: 2px solid #334155;">
                            <th style="padding:15px; font-size:16px;">მეტრიკა (Metric)</th>
                            <th style="padding:15px; font-size:16px; color:#3498db;">{ticker1}</th>
                            <th style="padding:15px; font-size:16px; color:#e74c3c;">{ticker2}</th>
                        </tr>
                        <tr style="border-bottom: 1px solid #334155;">
                            <td style="padding:12px;"><b>კაპიტალიზაცია (Market Cap)</b></td>
                            <td style="padding:12px;">${cap1/1e9:.1f}B</td>
                            <td style="padding:12px;">${cap2/1e9:.1f}B</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #334155;">
                            <td style="padding:12px;" title="რაც დაბალია - მით უფრო იაფია"><b>P/E Ratio ℹ️</b></td>
                            <td style="padding:12px;">{pe1_str}</td>
                            <td style="padding:12px;">{pe2_str}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #334155;">
                            <td style="padding:12px;" title="ფასი ზრდასთან შეფარდებით. < 1.0 იდეალურია"><b>PEG Ratio ℹ️</b></td>
                            <td style="padding:12px;">{peg1_str}</td>
                            <td style="padding:12px;">{peg2_str}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #334155;">
                            <td style="padding:12px;" title="წმინდა მოგების მარჟა. რაც მაღალია უკეთესია"><b>Profit Margin ℹ️</b></td>
                            <td style="padding:12px;">{margin1_str}</td>
                            <td style="padding:12px;">{margin2_str}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #334155;">
                            <td style="padding:12px;" title="რამდენად ეფექტურად იყენებენ კაპიტალს"><b>ROE (ეფექტურობა) ℹ️</b></td>
                            <td style="padding:12px;">{roe1_str}</td>
                            <td style="padding:12px;">{roe2_str}</td>
                        </tr>
                        <tr>
                            <td style="padding:12px;" title="კომპანიის ვალები. რაც დაბალია უკეთესია"><b>Debt-to-Equity (ვალი) ℹ️</b></td>
                            <td style="padding:12px;">{debt1_str}</td>
                            <td style="padding:12px;">{debt2_str}</td>
                        </tr>
                    </table>
                    """
                    st.markdown(html_table, unsafe_allow_html=True)
                    st.info("💡 მწვანე ფერით (🏆) მონიშნულია ის კომპანია, რომელიც კონკრეტულ ფინანსურ კრიტერიუმში სჯობნის კონკურენტს.")

                except Exception as e:
                    st.error(f"მონაცემების ჩატვირთვა ვერ მოხერხდა: {e}")
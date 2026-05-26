import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# გვერდის კონფიგურაცია - მინიმალისტური და ცენტრალიზებული
st.set_page_config(page_title="Options & Valuation Dashboard", layout="centered")
st.title("📊 ოფციონების ანალიტიკა და ფასის სიგნალები")

# აქციის სიმბოლოს შეყვანა
ticker_input = st.text_input("შეიყვანეთ აქციის თიკერი (მაგ: NVDA, AAPL, TSLA):", value="NVDA").upper().strip()

if ticker_input:
    try:
        stock = yf.Ticker(ticker_input)
        
        if not stock.options:
            st.error("ამ აქციისთვის ოფციონების მონაცემები ვერ მოიძებნა.")
        else:
            # 📅 ოფციონების ექსპირაციის თარიღის არჩევა
            available_dates = stock.options
            selected_date = st.selectbox("აირჩიეთ ოფციონის ექსპირაციის თარიღი:", options=available_dates, index=0)
            
            # მოგვაქვს ბოლო 3 თვის ისტორია ტექნიკური ინდიკატორებისთვის (RSI და SMA)
            history_data = stock.history(period="3mo")
            
            if not history_data.empty and len(history_data) > 14:
                current_price = history_data["Close"].iloc[-1]
                
                # --- 🧮 RSI (14)-ის ფორმულის გამოთვლა ხელით ---
                delta = history_data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs.iloc[-1]))
                
                # --- 🧮 20-დღიანი მოძრავი საშუალო (SMA 20) ---
                sma_20 = history_data['Close'].rolling(window=20).mean().iloc[-1]
                price_to_sma = ((current_price - sma_20) / sma_20) * 100
                
                # ოფციონების მონაცემების წამოღება განწყობისთვის
                opt_chain = stock.option_chain(selected_date)
                calls = opt_chain.calls.fillna(0)
                puts = opt_chain.puts.fillna(0)
                total_call_vol = calls['volume'].sum()
                total_put_vol = puts['volume'].sum()
                pcr = total_put_vol / total_call_vol if total_call_vol > 0 else 0
                
                # --- 🎯 სიგნალის განსაზღვრის მარტივი ალგორითმი ---
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
                
                # --- 🧮 MAX PAIN-ის გამოთვლა ---
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
                
                # 🔥 ლამაზი, 3-სვეტიანი პანელი საიტის თავში
                col_p1, col_p2, col_p3 = st.columns(3)
                with col_p1:
                    st.markdown(f"""
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 5px solid #3498db; min-height: 110px;">
                        <p style="margin: 0; font-size: 13px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">მიმდინარე ფასი</p>
                        <h2 style="margin: 0; font-size: 26px; color: #f8fafc; padding-top: 5px;">${current_price:.2f}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col_p2:
                    box_color = "#e74c3c" if max_pain_price < current_price else "#2ecc71"
                    st.markdown(f"""
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 5px solid {box_color}; min-height: 110px;">
                        <p style="margin: 0; font-size: 13px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">🎯 Max Pain ფასი</p>
                        <h2 style="margin: 0; font-size: 26px; color: #f8fafc; padding-top: 5px;">${max_pain_price:.2f}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col_p3:
                    # 💡 აი აქ ჩავამატეთ საინფორმაციო აღწერა (Tooltip)
                    st.markdown(f"""
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 5px solid #9b59b6; min-height: 110px;">
                        <p style="margin: 0; font-size: 13px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">📈 RSI ინდექსი (14D)</p>
                        <h2 style="margin: 0; font-size: 26px; color: #f8fafc; padding-top: 5px;">{rsi:.1f}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # პატარა ინტერაქტიული კითხვის ნიშანი უჯრის დაბლა, რომელიც მაუსის მიტანას ელოდება
                    st.help("""
                    💡 RSI-ს 3 უმთავრესი ზონის განმარტება:
                    
                    1️⃣ RSI > 70 — გადახურებული (Overbought): ფასი ზედმეტად მაღალია, ბაზარი ეიფორიაშია და დიდია კორექციის (ვარდნის) შანსი.
                    
                    2️⃣ RSI < 30 — გაუფასურებული (Oversold): ფასი პანიკურად არის დაცემული იატაკზე და დიდია ალბათობა, რომ მალე ზრდა დაიწყოს.
                    
                    3️⃣ 30-დან 70-მდე — ნეიტრალური ზონა: აქცია სტაბილურ მდგომარეობაშია და მიყვება თავის ბუნებრივ ტრენდს.
                    """)
                
                # 🚨 დიდი და გამოკვეთილი სიგნალის ბლოკი
                st.markdown(f"""
                <div style="background-color: #1e293b; padding: 18px; border-radius: 10px; text-align: center; border: 2px solid {signal_color}; margin-top: 15px; margin-bottom: 25px;">
                    <span style="color: #94a3b8; font-size: 13px; font-weight: bold; text-transform: uppercase; display: block; margin-bottom: 5px;">🤖 ფასის მდგომარეობის სიგნალი</span>
                    <span style="color: {signal_color}; font-size: 22px; font-weight: bold;">{signal_text}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # --- ჩარტი 1: ჯამური მოცულობა (Volume) ---
                fig_vol = go.Figure(data=[
                    go.Bar(
                        x=['Call ოფციონები', 'Put ოფციონები'],
                        y=[total_call_vol, total_put_vol],
                        marker_color=['#2ecc71', '#e74c3c'],
                        text=[f"{int(total_call_vol):,}", f"{int(total_put_vol):,}"],
                        textposition='auto'
                    )
                ])
                fig_vol.update_layout(title="დღევანდელი ჯამური მოცულობა (Volume)", template="plotly_dark", height=300)
                
                col_left, col_right = st.columns([1, 2])
                with col_left:
                    st.metric(label="Put-Call Ratio (PCR)", value=f"{pcr:.2f}")
                    if pcr > 1: st.error("📉 განწყობა: BEARISH")
                    else: st.success("📈 განწყობა: BULLISH")
                with col_right:
                    st.plotly_chart(fig_vol, use_container_width=True, config={'displayModeBar': False})
                
                st.markdown("---")
                
                # --- ჩარტი 2: დეტალური Open Interest (OI) სტრაიკების მიხედვით ---
                st.subheader("🎯 Open Interest კედლები (Strikes-ის მიხედვით)")
                calls_filtered = calls[['strike', 'openInterest']].rename(columns={'openInterest': 'Call OI'})
                puts_filtered = puts[['strike', 'openInterest']].rename(columns={'openInterest': 'Put OI'})
                df_oi = calls_filtered.merge(puts_filtered, on='strike', how='outer').fillna(0)
                
                df_oi['strike_diff'] = (df_oi['strike'] - current_price).abs()
                df_oi = df_oi.sort_values('strike_diff').head(20).sort_values('strike')
                
                fig_oi = go.Figure()
                fig_oi.add_trace(go.Bar(x=df_oi['strike'], y=df_oi['Call OI'], name='Call Open Interest', marker_color='#2ecc71'))
                fig_oi.add_trace(go.Bar(x=df_oi['strike'], y=df_oi['Put OI'], name='Put Open Interest', marker_color='#e74c3c'))
                fig_oi.update_layout(
                    xaxis_title="სტრაიკ ფასი ($)", yaxis_title="ღია კონტრაქტების რაოდენობა",
                    barmode='group', template="plotly_dark", height=400
                )
                st.plotly_chart(fig_oi, use_container_width=True, config={'displayModeBar': False})
                
            else:
                st.error("ტექნიკური ანალიზისთვის საჭირო ისტორიული მონაცემები ვერ ჩაიტვირთა.")
    except Exception as e:
        st.error(f"შეცდომა მონაცემების დამუშავებისას: {e}")
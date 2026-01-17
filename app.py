import streamlit as st
import ccxt
import pandas as pd
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
START_CAPITAL = 1000000  # 10 Lakhs INR
TRADE_INTERVAL = 5       # Seconds between loops (Simulated real-time)
MAX_POSITIONS = 4        # Diversify into max 4 coins
ALLOCATION_PER_TRADE = START_CAPITAL / MAX_POSITIONS

# --- INITIALIZE SESSION STATE ---
if 'balance' not in st.session_state:
    st.session_state.balance = START_CAPITAL
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}  # {symbol: {'amt': 0, 'avg_price': 0}}
if 'trade_log' not in st.session_state:
    st.session_state.trade_log = []
if 'is_running' not in st.session_state:
    st.session_state.is_running = False

# --- UTILS & DATA ENGINE ---
@st.cache_resource
def get_exchange():
    # Using Binance for data (public API, no keys needed for fetching)
    return ccxt.binance({'enableRateLimit': True})

def fetch_top_coins(exchange, limit=10):
    """Scans for top coins by volume to 'Pick' the best ones."""
    try:
        tickers = exchange.fetch_tickers()
        # Filter for USDT pairs only to keep it simple
        valid_tickers = {k: v for k, v in tickers.items() if k.endswith('/USDT')}
        sorted_tickers = sorted(valid_tickers.values(), key=lambda x: x['quoteVolume'], reverse=True)
        return [t['symbol'] for t in sorted_tickers[:limit]]
    except Exception as e:
        return []

def get_market_data(exchange, symbol):
    """Fetches 1-minute OHLCV candles for strategy."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=20)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except:
        return pd.DataFrame()

# --- TRADING LOGIC (BRAIN) ---
def run_strategy(exchange):
    top_coins = fetch_top_coins(exchange)
    
    for symbol in top_coins:
        df = get_market_data(exchange, symbol)
        if df.empty: continue
        
        current_price = df['close'].iloc[-1]
        
        # Simple Strategy: MOMENTUM 
        # Buy if price is rising (Close > SMA_5). Sell if falling.
        sma_short = df['close'].rolling(window=5).mean().iloc[-1]
        
        # 1. BUY LOGIC
        if symbol not in st.session_state.portfolio and len(st.session_state.portfolio) < MAX_POSITIONS:
            if current_price > sma_short:  # Bullish signal
                # Execute Buy
                qty = ALLOCATION_PER_TRADE / current_price
                cost = qty * current_price
                
                if st.session_state.balance >= cost:
                    st.session_state.balance -= cost
                    st.session_state.portfolio[symbol] = {'amt': qty, 'avg_price': current_price}
                    st.session_state.trade_log.append({
                        "Time": datetime.now().strftime("%H:%M:%S"),
                        "Symbol": symbol,
                        "Type": "BUY",
                        "Price": current_price,
                        "Qty": qty,
                        "P/L": 0
                    })
                    st.toast(f"✅ Bought {symbol} at {current_price}")

        # 2. SELL LOGIC
        elif symbol in st.session_state.portfolio:
            entry_price = st.session_state.portfolio[symbol]['avg_price']
            qty = st.session_state.portfolio[symbol]['amt']
            
            # Sell condition: Price drops below SMA OR Profit Target hit (simulated)
            if current_price < sma_short:
                revenue = qty * current_price
                pnl = revenue - (qty * entry_price)
                
                st.session_state.balance += revenue
                del st.session_state.portfolio[symbol]
                st.session_state.trade_log.append({
                    "Time": datetime.now().strftime("%H:%M:%S"),
                    "Symbol": symbol,
                    "Type": "SELL",
                    "Price": current_price,
                    "Qty": qty,
                    "P/L": round(pnl, 2)
                })
                st.toast(f"🔻 Sold {symbol} | P/L: {pnl:.2f}")

# --- UI LAYOUT ---
st.set_page_config(page_title="Crypto Algo-Trader (Edu)", layout="wide")
st.title("🤖 AI Crypto Algorithmic Trader")
st.markdown(f"**Budget:** ₹10,00,000 (Virtual) | **Strategy:** Momentum Intraday")

# Sidebar
st.sidebar.header("Control Panel")
if st.sidebar.button("Start Trading Bot"):
    st.session_state.is_running = True
if st.sidebar.button("Stop Bot"):
    st.session_state.is_running = False

# Dashboard Metrics
exchange = get_exchange()
current_holdings_val = sum([p['amt'] * get_market_data(exchange, s)['close'].iloc[-1] for s, p in st.session_state.portfolio.items() if not get_market_data(exchange, s).empty])
total_portfolio = st.session_state.balance + current_holdings_val
pnl_total = total_portfolio - START_CAPITAL

col1, col2, col3 = st.columns(3)
col1.metric("Total Portfolio Value", f"₹{total_portfolio:,.2f}", delta=f"{pnl_total:,.2f}")
col2.metric("Cash Balance", f"₹{st.session_state.balance:,.2f}")
col3.metric("Active Positions", len(st.session_state.portfolio))

# Main Execution Loop
if st.session_state.is_running:
    with st.spinner('Scanning Market & Executing Trades...'):
        run_strategy(exchange)
        time.sleep(1) # Small delay to prevent API rate limits
        st.rerun() # Forces the script to run again (Loop)

# Visualizations
col_charts, col_logs = st.columns([2, 1])

with col_charts:
    st.subheader("Live Market (Top Asset)")
    if st.session_state.portfolio:
        symbol_to_chart = list(st.session_state.portfolio.keys())[0]
        df = get_market_data(exchange, symbol_to_chart)
        if not df.empty:
            fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.update_layout(title=f"Live Chart: {symbol_to_chart}", height=400)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Waiting for first trade to generate chart...")

with col_logs:
    st.subheader("Trade Log")
    if st.session_state.trade_log:
        log_df = pd.DataFrame(st.session_state.trade_log)
        st.dataframe(log_df.iloc[::-1], height=400) # Show newest first
def run_strategy(exchange):
    # 1. VISUAL FEEDBACK: Tell the user we are scanning
    status_placeholder = st.empty() 
    status_placeholder.info("🔄 Scanning the market for opportunities...")
    
    # Fallback: If scanner fails, look at these specific coins
    top_coins = fetch_top_coins(exchange)
    if not top_coins:
        top_coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'DOGE/USDT']
    
    for symbol in top_coins:
        # Show which coin is being checked right now
        status_placeholder.markdown(f"**Checking:** `{symbol}` ...")
        
        df = get_market_data(exchange, symbol)
        if df.empty: continue
        
        current_price = df['close'].iloc[-1]
        sma_short = df['close'].rolling(window=5).mean().iloc[-1]
        
        # --- LOGIC UPDATE: RELAXED RULES FOR TESTING ---
        # We lowered the barrier slightly so you can see a trade happen faster
        
        # BUY LOGIC
        if symbol not in st.session_state.portfolio and len(st.session_state.portfolio) < MAX_POSITIONS:
            # DEBUG: Print the condition values
            # st.write(f"{symbol}: Price {current_price} vs SMA {sma_short}") 
            
            if current_price > sma_short:  
                qty = ALLOCATION_PER_TRADE / current_price
                cost = qty * current_price
                if st.session_state.balance >= cost:
                    st.session_state.balance -= cost
                    st.session_state.portfolio[symbol] = {'amt': qty, 'avg_price': current_price}
                    st.session_state.trade_log.append({
                        "Time": datetime.now().strftime("%H:%M:%S"),
                        "Symbol": symbol,
                        "Type": "BUY",
                        "Price": current_price,
                        "Qty": qty,
                        "P/L": 0
                    })
                    st.toast(f"✅ BOUGHT {symbol}!", icon="🚀")
                    break # Stop scanning to update UI immediately

        # SELL LOGIC
        elif symbol in st.session_state.portfolio:
            entry_price = st.session_state.portfolio[symbol]['avg_price']
            qty = st.session_state.portfolio[symbol]['amt']
            
            # Sell if price drops OR if we made a tiny profit (0.1%) for testing
            if current_price < sma_short or (current_price > entry_price * 1.001):
                revenue = qty * current_price
                pnl = revenue - (qty * entry_price)
                st.session_state.balance += revenue
                del st.session_state.portfolio[symbol]
                st.session_state.trade_log.append({
                    "Time": datetime.now().strftime("%H:%M:%S"),
                    "Symbol": symbol,
                    "Type": "SELL",
                    "Price": current_price,
                    "Qty": qty,
                    "P/L": pnl
                })
                st.toast(f"🔻 SOLD {symbol}!", icon="💰")
                break 
    
    # Clear the "Checking..." text when done loop
    status_placeholder.empty()
    

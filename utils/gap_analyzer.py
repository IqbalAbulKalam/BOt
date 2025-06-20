import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from ta.volume import OnBalanceVolumeIndicator

from utils.data_fetcher import get_stock_data

def calculate_ad_line(data):
    """
    Menghitung Accumulation/Distribution Line dengan penanganan data kosong.
    """
    if data is None or data.empty:
        print("⚠️ Data kosong - tidak bisa hitung AD Line")
        return None

    try:
        # Pastikan kolom yang dibutuhkan ada
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_cols):
            print("⚠️ Kolom tidak lengkap")
            return None

        # Hitung Money Flow Multiplier
        high_low_range = data['High'] - data['Low']
        close_low = data['Close'] - data['Low']
        high_close = data['High'] - data['Close']
        
        # Hindari division by zero (jika High == Low)
        multiplier = (close_low - high_close) / high_low_range.replace(0, 1)
        
        # Hitung Money Flow Volume
        data['Money_Flow'] = multiplier * data['Volume']
        
        # Hitung AD Line (akumulasi)
        data['AD_Line'] = data['Money_Flow'].cumsum()
        
        return data

    except Exception as e:
        print(f"⚠️ Error di calculate_ad_line: {str(e)}")
        return None

def detect_gap_down(data, threshold=0.02):
    """Deteksi gap down dengan penanganan data kosong/kolom tidak lengkap"""
    if data is None or data.empty:
        print("⚠️ Data kosong - tidak bisa deteksi gap")
        return None

    try:
        # Hitung persentase gap
        prev_close = data['Close'].shift(1)
        data['Gap_pct'] = (data['Open'] - prev_close) / prev_close * 100
        
        # Tandai gap down ≥ threshold
        data['Is_Gap_Down'] = data['Gap_pct'] <= -threshold
        
        # Hitung OBV untuk deteksi akumulasi
        obv = OnBalanceVolumeIndicator(close=data['Close'], volume=data['Volume'])
        data['OBV'] = obv.on_balance_volume()
        data['OBV_Change'] = data['OBV'].diff()
        data['Is_Accumulation'] = data['OBV_Change'] > 0
        
        # Gabungkan sinyal
        data['Is_Signal'] = data['Is_Gap_Down'] & data['Is_Accumulation']
        
        return data

    except Exception as e:
        print(f"⚠️ Error di detect_gap_down: {str(e)}")
        return None

def analyze_stock(stock_code, period='1mo'):
    """Ambil dan proses data saham"""
    try:
        data = get_stock_data(stock_code, period)
        if data is None or data.empty:
            print("Data kosong atau tidak valid")
            return None
            
        # DEBUG: Cetak kolom sebelum diproses
        print("\n=== DATA AWAL ===")
        print("Columns:", data.columns.tolist())
        print(data.head())
        
        data = calculate_ad_line(data)
        data = detect_gap_down(data)
        
        # DEBUG: Cetak kolom setelah diproses
        print("\n=== DATA SETELAH PROSES ===")
        print("Columns:", data.columns.tolist())
        print(data[['Open', 'Close', 'Gap_pct', 'Is_gap_down']].head())
        
        return data
    except Exception as e:
        print(f"Error analyze_stock: {e}")
        return None

        # DEBUG: Cetak kolom yang tersedia
    # print("\n=== DEBUG ANALYZE_STOCK ===")
    # print("Columns after processing:", data.columns.tolist())
    # print("Sample data:\n", data.head())
    # return data

def get_gap_down_summary(data, stock_code):
    """Ringkasan hasil gap down dengan kolom yang konsisten"""
    if not data.empty and 'Is_gap_down' in data.columns:
        gaps = data[data['Is_gap_down']]
        if not gaps.empty:
            summary = []
            for date, row in gaps.iterrows():
                summary.append({
                    'Date': date.strftime('%Y-%m-%d'),
                    'Stock': stock_code,
                    'Open': row['Open'],
                    'Close': row['Close'],
                    'Gap_pct': abs(row['Gap_pct']),  # Nilai absolute
                    'AD_Line': row['AD Line']
                })
            return summary
    return None


# # Test 1: Data normal
# test_data = yf.download("BBRI.JK", period="1mo")
# test_data = calculate_ad_line(test_data)
# test_data = detect_gap_down(test_data)
# print(test_data[['Open', 'Close', 'Gap_pct', 'Is_gap_down']].head())

# # Test 2: Data kosong
# empty_summary = get_gap_down_summary(pd.DataFrame(), "TEST")
# print("Empty test:", empty_summary)
import yfinance as yf
import mplfinance as mpf
import pandas as pd
import os
from datetime import datetime

def get_stock_data(stock_code, period='1mo'):
    """Ambil data dan bersihkan struktur kolom"""
    """Handle baik 1 ticker maupun banyak ticker."""
    tickers = [stock_code] if isinstance(stock_code, str) else stock_code

    try:
        # Download data
        data = yf.download(
            f"{stock_code}.JK",
            period=period,
            progress=False,
            group_by='ticker', # <-- Tetap dipakai untuk multi-ticker
            auto_adjust=True
        )

        # Bersihkan multi-level columns jika ada
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(0)

        # Pastikan kolom nya standar
        data = data.rename(columns={
            'price': 'Close',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'volume': 'Volume'
        })
        
        # Pastikan kolom penting ada
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        data = data[required_cols].copy()
        
        # Konversi tipe
        data[['Open', 'High', 'Low', 'Close']] = data[['Open', 'High', 'Low', 'Close']].astype(float)
        data['Volume'] = data['Volume'].astype(int)
            
        return data.dropna()
    
    except Exception as e:
        print(f"Error in get_stock_data: {e}")
        return None

def plot_candlestick(data, stock_code):
    """Buat candlestick chart dengan penanganan error lebih kuat"""
    try:
        # Validasi data
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_cols):
            raise ValueError(f"Data harus mengandung kolom: {required_cols}")
        
        # Konversi index ke datetime
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index, errors='coerce')
            if data.index.isnull().any():
                raise ValueError("Format tanggal tidak valid")
        
        # Buat direktori temp jika belum ada
        os.makedirs('temp', exist_ok=True)
        filename = f"temp/{stock_code}_candle.png"
        
        # Style candlestick
        mc = mpf.make_marketcolors(
            up='#2E7D32',  # hijau tua
            down='#C62828', # merah tua
            wick={'up':'#2E7D32', 'down':'#C62828'},
            edge={'up':'#2E7D32', 'down':'#C62828'},
            volume='#78909C'  # abu-abu
        )
        style = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='--',
            gridcolor='#ECEFF1'
        )
        
        # Buat plot
        mpf.plot(
            data,
            type='candle',
            style=style,
            title=f'\n{stock_code} | {datetime.now().strftime("%d %b %Y")}',
            ylabel='Harga (IDR)',
            ylabel_lower='Volume',
            volume=True,
            savefig=dict(
                fname=filename,
                dpi=100,
                bbox_inches='tight',
                pad_inches=0.5
            ),
            figratio=(12, 6),
            tight_layout=True,
            show_nontrading=False
        )
        
        return filename
    
    except Exception as e:
        print(f"Error generating chart: {str(e)}")
        print(f"Data received:\n{data.head() if data is not None else 'None'}")
        return None
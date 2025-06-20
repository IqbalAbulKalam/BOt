from datetime import datetime, time
from telegram.ext import ContextTypes
from utils.gap_analyzer import detect_gap_down
from utils.data_fetcher import get_stock_data
from utils.watchlist_manager import load_watchlist
from utils.alert_sender import send_signal_alert
import pandas as pd

class GapScanner:
    def __init__(self, application):
        self.application = application

    async def scan_and_alert(self, context: ContextTypes.DEFAULT_TYPE):
        
        # Production mode - real data check
        watchlist = load_watchlist()
        for stock_code in watchlist:
            try:
                data = get_stock_data(stock_code.replace('.JK', ''), period='1mo')
                if data is None or data.empty:
                    continue

                data = detect_gap_down(data)
                signals = data[data['Is_Signal']]
                
                if not signals.empty:
                    await send_signal_alert(context, stock_code, signals.iloc[-1])
                    
            except Exception as e:
                print(f"⚠️ Error scanning {stock_code}: {str(e)}")

    def start(self):
        """Schedule daily scans at 09:15 WIB (02:15 UTC) Mon-Fri"""
        self.application.job_queue.run_daily(
            self.scan_and_alert,
            time=time(hour=2, minute=15), 
            days=(0, 1, 2, 3, 4, 5, 6)
        )
import pandas as pd
from telegram.constants import ParseMode
from utils.data_fetcher import plot_candlestick
import os
from datetime import datetime
from base_bot import load_chat_ids  # Pastikan ini diimpor dengan benar

async def send_signal_alert(context, stock_code, signal_data):
    try:
        # Dapatkan semua chat_id yang terdaftar
        chat_ids = load_chat_ids()
        if not chat_ids:
            print("[ERROR] Tidak ada chat_id tersimpan!")
            return

        # Proses data sinyal
        if isinstance(signal_data, pd.DataFrame):
            last_row = signal_data.iloc[-1]
            date = signal_data.index[-1]
        else:  # Handle Series input
            last_row = signal_data
            date = signal_data.name

        # Format pesan alert
        message = (
            f"📉 <b>SINYAL TERDETEKSI</b>\n"
            f"Saham: {stock_code}\n"
            f"Tanggal: {date.strftime('%Y-%m-%d')}\n"
            f"Harga: Rp. {last_row['Close']:,.0f}\n"
            f"Gap: {last_row.get('Gap_pct', 0):.2f}%\n"
            f"Akumulasi Bandar: ✅"
        )

        # Siapkan data grafik
        plot_data = signal_data[['Open','High','Low','Close','Volume']].copy() if isinstance(signal_data, pd.DataFrame) \
                   else pd.DataFrame(signal_data).T[['Open','High','Low','Close','Volume']]
        
        # Pastikan tipe data benar
        plot_data = plot_data.astype({
            'Open': float,
            'High': float,
            'Low': float,
            'Close': float,
            'Volume': int
        })

        # Generate grafik
        chart_file = plot_candlestick(plot_data, stock_code)

        # Kirim ke semua chat_id
        for chat_id in chat_ids:
            try:
                if chart_file:
                    with open(chart_file, 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=message,
                            parse_mode=ParseMode.HTML
                        )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                print(f"[ERROR] Gagal kirim ke {chat_id}: {str(e)}")

        # Bersihkan file grafik jika ada
        if chart_file and os.path.exists(chart_file):
            os.remove(chart_file)

    except Exception as e:
        print(f"[ALERT ERROR] {str(e)}")
        print(f"[DEBUG DATA] Last row: {last_row.to_dict() if 'last_row' in locals() else 'No data'}")
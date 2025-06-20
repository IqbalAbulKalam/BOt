import pandas as pd
from telegram.constants import ParseMode
from utils.data_fetcher import plot_candlestick
import os
from datetime import datetime

async def send_signal_alert(context, stock_code, signal_data):
    try:
        # Get chat_id from context (essential for production)
        chat_id = (
            getattr(context.job, 'chat_id', None) or
            getattr(context, '_chat_id', None) or
            getattr(context, '_user_id', None))
        
        if not chat_id:
            raise ValueError("chat_id not found in context")

        # Extract signal information
        if isinstance(signal_data, pd.DataFrame):
            last_row = signal_data.iloc[-1]
            date = signal_data.index[-1]
        else:  # Handle Series input
            last_row = signal_data
            date = signal_data.name

        # Format alert message
        message = (
            f"📉 <b>SINYAL TERDETEKSI</b>\n"
            f"Saham: {stock_code}\n"
            f"Tanggal: {date.strftime('%Y-%m-%d')}\n"
            f"Harga: Rp. {last_row['Close']:,.0f}\n"
            f"Gap: {last_row.get('Gap_pct', 0):.2f}%\n"
            f"Akumulasi Bandar: ✅"
        )
    
        # Prepare chart data
        plot_data = signal_data[['Open','High','Low','Close','Volume']].copy() if isinstance(signal_data, pd.DataFrame) \
                   else pd.DataFrame(signal_data).T[['Open','High','Low','Close','Volume']]
        
        # Ensure data integrity
        plot_data = plot_data.astype({
            'Open': float,
            'High': float,
            'Low': float,
            'Close': float,
            'Volume': int
        })

        # Generate and send chart
        chart_file = plot_candlestick(plot_data, stock_code)
        if chart_file:
            with open(chart_file, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=message,
                    parse_mode=ParseMode.HTML
                )
            os.remove(chart_file)
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        print(f"[ALERT ERROR] {str(e)}")
        print(f"[DEBUG DATA] Last row: {last_row.to_dict() if 'last_row' in locals() else 'No data'}")
        # Optionally send error notification
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Gagal mengirim alert untuk {stock_code}: {str(e)}"
        )
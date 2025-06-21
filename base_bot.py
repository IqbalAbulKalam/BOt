import os
import json
import traceback
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from utils.data_fetcher import get_stock_data, plot_candlestick
from telegram import InputFile
from utils.gap_analyzer import analyze_stock, get_gap_down_summary, calculate_ad_line, detect_gap_down
from utils.watchlist_manager import add_to_watchlist, remove_from_watchlist
from utils.scheduler import GapScanner
from telegram.constants import ParseMode

# Load config
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Path untuk simpan chat_id
CHAT_ID_FILE = "data/chat_ids.json"

if not TOKEN:
    raise ValueError("Token bot tidak ditemukan! Pastikan file .env sudah dibuat")

def save_chat_id(chat_id):
    os.makedirs("data", exist_ok=True)
    try:
        with open(CHAT_ID_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []
    
    if chat_id not in data:
        data.append(chat_id)
        with open(CHAT_ID_FILE, "w") as f:
            json.dump(data, f)

def get_registered_chat_ids():
    """Mengembalikan list chat_id yang tersimpan atau list kosong jika error"""
    try:
        with open("data/chat_ids.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

async def show_registered_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah /show_ids"""
    chat_ids = get_registered_chat_ids()
    
    if not chat_ids:
        await update.message.reply_text("❌ Tidak ada chat_id yang terdaftar.")
        return
    
    # Format pesan
    message = "📋 Daftar Chat ID yang Terdaftar:\n" + \
              "\n".join([f"• {cid}" for cid in chat_ids])
    
    await update.message.reply_text(message)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk command /start"""
    chat_id = update.effective_chat.id
    save_chat_id(chat_id)  # Simpan ke file
    await update.message.reply_text("✅ Anda sekarang terdaftar untuk menerima alert saham!")
    help_text = (
        "Halo! Saya adalah Bot Asisten Saham Anda \n"
        "Perintah yang tersedia:\n"
        "/cek_candle [kode_saham] - Cek manual grafik candle\n"
        "/gapcheck [kode_saham] - Cek manual gap down ≥2%\n"
        "/help - Untuk menampilkan kembali pesan ini"
    )
    await update.message.reply_text(help_text)

async def cek_candle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk cek candle dengan penanganan error lebih baik"""
    if not context.args:
        await update.message.reply_text("Format: /cek_candle [kode_saham]\nContoh: /cek_candle BBCA")
        return
    
    stock_code = context.args[0].upper()
    msg = await update.message.reply_text(f"🔄 Mengambil data {stock_code}...")
    
    try:
        # Step 1: Dapatkan data
        data = get_stock_data(stock_code)
        if data is None or data.empty:
            await msg.edit_text(f"❌ Gagal mengambil data {stock_code}")
            return
            
        # Step 2: Buat grafik
        await msg.edit_text(f"📊 Membuat grafik {stock_code}...")
        chart_file = plot_candlestick(data, stock_code)
        
        if chart_file is None or not os.path.exists(chart_file):
            await msg.edit_text("❌ Gagal membuat grafik")
            return
            
        # Step 3: Kirim gambar
        with open(chart_file, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"📈 Grafik {stock_code} - 30 hari terakhir"
            )
        await msg.delete()
        
        # Step 4: Bersihkan file
        try:
            os.remove(chart_file)
        except:
            pass
            
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")
        print(f"Error trace: {traceback.format_exc()}")

async def cek_gap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler manual untuk cek gap down + akumulasi (format sama seperti auto scan)"""
    try:
        # Parsing input
        stock_code = context.args[0].upper() if context.args else None
        period = context.args[1] if len(context.args) > 1 else "1mo"  # Default: 1 bulan
        
        if not stock_code:
            await update.message.reply_text("Contoh: /gapcheck BBRI 3mo")
            return

        # Ambil data
        data = get_stock_data(stock_code, period=period)
        if data is None or data.empty:
            await update.message.reply_text("⚠️ Gagal mengambil data saham")
            return

        # Proses deteksi sinyal (gap + OBV)
        data = detect_gap_down(data)  # Fungsi dari gap_analyzer.py yang sudah diupdate
        signals = data[data['Is_Signal']]
        
        if not signals.empty:
            # Kirim alert untuk setiap sinyal (atau hanya yang terbaru)
            latest_signal = signals.iloc[-1]
            
            # Gunakan format sama seperti auto scan
            message = (
                f"📉 <b>SINYAL TERAKHIR TERDETEKSI (Manual Check)</b>\n"
                f"Saham: {stock_code}\n"
                f"Tanggal: {latest_signal.name.strftime('%Y-%m-%d')}\n"
                f"Harga: {latest_signal['Close']:,.0f}\n"
                f"Gap: {latest_signal['Gap_pct']:.2f}%\n"
                f"Akumulasi Bandar: ✅"
            )
            
            # Kirim grafik
            chart_file = plot_candlestick(data, stock_code)
            if chart_file:
                with open(chart_file, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=message,
                        parse_mode=ParseMode.HTML
                    )
                os.remove(chart_file)
            else:
                await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(
                f"⚠️ Tidak ada sinyal gap down + akumulasi pada {stock_code} (periode: {period})"
            )

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def add_watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /addwatch"""
    if not context.args:
        await update.message.reply_text("Contoh: /addwatch BBRI")
        return
    
    stock_code = context.args[0].upper()
    if add_to_watchlist(stock_code):
        await update.message.reply_text(f"✅ {stock_code} ditambahkan ke watchlist!")
    else:
        await update.message.reply_text(f"⚠️ {stock_code} sudah ada di watchlist")

async def remove_watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /rmwatch"""
    if not context.args:
        await update.message.reply_text("Contoh: /rmwatch BBRI")
        return
    
    stock_code = context.args[0].upper()
    if remove_from_watchlist(stock_code):
        await update.message.reply_text(f"✅ {stock_code} dihapus dari watchlist!")
    else:
        await update.message.reply_text(f"⚠️ {stock_code} tidak ditemukan di watchlist")

async def show_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /watchlist"""
    from utils.watchlist_manager import load_watchlist
    watchlist = load_watchlist()
    if not watchlist:
        await update.message.reply_text("Watchlist kosong")
    else:
        message = "📋 Daftar Saham yang Dipantau:\n" + "\n".join(
            f"• {code.replace('.JK', '')}" for code in watchlist
        )
        await update.message.reply_text(message)

async def test_auto_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print(f"[DEBUG] Command chat_id: {update.effective_chat.id}")
        context._user_id = update.effective_chat.id
        await context.application.scanner.scan_and_alert(context)
        await update.message.reply_text("✅ Test auto-check dijalankan!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"[ERROR] in test_auto: {traceback.format_exc()}")

def main():
    application = Application.builder().token(TOKEN).build()  
    scanner = GapScanner(application)  # Tanpa test_mode  
    scanner.start()

    # Simpan scanner di context.user_data atau gunakan closure
    async def test_auto(update, context):
        await scanner.scan_and_alert(context)
        await update.message.reply_text("✅ Test berhasil!")

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addwatch", add_watch))
    application.add_handler(CommandHandler("rmwatch", remove_watch))
    application.add_handler(CommandHandler("watchlist", show_watchlist))
    application.add_handler(CommandHandler("show_ids", show_registered_ids))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("cek_candle", cek_candle))
    application.add_handler(CommandHandler("gapcheck", cek_gap))
    application.add_handler(CommandHandler("test_auto", test_auto))

    # scanner = GapScanner(application)  # application di-pass sebagai argumen
    # scanner = GapScanner(application, test_mode=True)
    # scanner.start()

    print("Bot sedang berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
import json
import os
from typing import List

WATCHLIST_PATH = "data/watchlist.json"

def load_watchlist() -> List[str]:
    """Muat daftar saham dari file dengan error handling"""
    # Jika file tidak ada, buat baru dengan default watchlist
    if not os.path.exists(WATCHLIST_PATH):
        default_watchlist = ["BBRI.JK", "BMRI.JK"]
        save_watchlist(default_watchlist)
        return default_watchlist
    
    # Jika file ada, baca dengan error handling
    try:
        with open(WATCHLIST_PATH, 'r') as f:
            content = f.read()
            if not content.strip():  # Jika file kosong
                raise ValueError("File kosong")
            return json.loads(content)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️ Error baca watchlist: {e}. Membuat baru...")
        default_watchlist = ["BBRI.JK", "BMRI.JK"]
        save_watchlist(default_watchlist)
        return default_watchlist

def save_watchlist(watchlist: List[str]) -> None:
    """Simpan daftar saham ke file"""
    os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)
    with open(WATCHLIST_PATH, 'w') as f:
        json.dump(watchlist, f, indent=2)

def add_to_watchlist(stock_code: str) -> bool:
    """Tambahkan saham ke watchlist"""
    if not stock_code.endswith(".JK"):
        stock_code += ".JK"
    
    watchlist = load_watchlist()
    if stock_code not in watchlist:
        watchlist.append(stock_code)
        save_watchlist(watchlist)
        return True
    return False

def remove_from_watchlist(stock_code: str) -> bool:
    """Hapus saham dari watchlist"""
    if not stock_code.endswith(".JK"):
        stock_code += ".JK"
    
    watchlist = load_watchlist()
    if stock_code in watchlist:
        watchlist.remove(stock_code)
        save_watchlist(watchlist)
        return True
    return False
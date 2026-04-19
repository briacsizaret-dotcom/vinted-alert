import requests
import json
import time
import os
from datetime import datetime

# ============================================================
#  ⚙️  CONFIGURATION — modifie ces valeurs avant de lancer
# ============================================================
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1495524617589100704/qHw-pTifGR8NE9p5kTrsmsTdsP2thKrXMi-hYVNAxQAayv7KygAn4JFhemQYiE9gxVWs"
SEARCH_QUERY        = "pull saint james"   # Mots-clés Vinted
MAX_PRICE           = 30                   # Prix max en euros
CHECK_INTERVAL      = 300                  # Délai entre chaque vérif (secondes)
# ============================================================

VINTED_API_URL  = "https://www.vinted.fr/api/v2/catalog/items"
SEEN_ITEMS_FILE = "seen_items.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer":         "https://www.vinted.fr/",
}


# ── Session ──────────────────────────────────────────────────

def get_session() -> requests.Session:
    """Ouvre une session et récupère les cookies Vinted."""
    s = requests.Session()
    try:
        s.get("https://www.vinted.fr", headers=HEADERS, timeout=10)
    except Exception as e:
        print(f"⚠️  Impossible d'initialiser la session Vinted : {e}")
    return s


# ── Recherche Vinted ─────────────────────────────────────────

def search_vinted(session: requests.Session) -> list:
    params = {
        "search_text": SEARCH_QUERY,
        "price_to":    MAX_PRICE,
        "order":       "newest_first",
        "per_page":    30,
    }
    try:
        r = session.get(VINTED_API_URL, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json().get("items", [])
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP Vinted ({r.status_code}) : {e}")
    except Exception as e:
        print(f"❌ Erreur Vinted : {e}")
    return []


# ── Persistance des articles déjà vus ────────────────────────

def load_seen() -> set:
    if os.path.exists(SEEN_ITEMS_FILE):
        with open(SEEN_ITEMS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set) -> None:
    with open(SEEN_ITEMS_FILE, "w") as f:
        json.dump(list(seen), f)


# ── Notification Discord ─────────────────────────────────────

def send_discord(item: dict) -> None:
    title  = item.get("title", "Sans titre")
    price  = item.get("price", {}).get("amount", "?")
    size   = item.get("size_title", "—")
    brand  = item.get("brand_title", "—")
    status = item.get("status", "—")           # état (bon état, neuf…)
    url    = f"https://www.vinted.fr/items/{item['id']}"

    embed = {
        "title":       f"🧥 {title}",
        "url":         url,
        "color":       0x09B1BA,               # couleur bleu Vinted
        "description": f"[👉 Voir l'annonce sur Vinted]({url})",
        "fields": [
            {"name": "💶 Prix",   "value": f"**{price} €**",  "inline": True},
            {"name": "📏 Taille", "value": size,               "inline": True},
            {"name": "✨ État",   "value": status,             "inline": True},
            {"name": "🏷️ Marque", "value": brand,             "inline": True},
        ],
        "footer": {
            "text": f"Vinted Alert • {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        },
    }

    # Miniature de la première photo
    photos = item.get("photos") or []
    if photos:
        thumb = photos[0].get("url") or photos[0].get("full_size_url", "")
        if thumb:
            embed["thumbnail"] = {"url": thumb}

    payload = {
        "content": "🚨 **Nouveau pull Saint James sous 30 € sur Vinted !**",
        "embeds":  [embed],
    }

    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        print(f"  ✅ Discord notifié → {title}  ({price} €)")
    except Exception as e:
        print(f"  ❌ Erreur Discord : {e}")


# ── Boucle principale ─────────────────────────────────────────

def main() -> None:
    print("=" * 55)
    print("  🔍  Vinted Alert — Pull Saint James < 30 €")
    print("=" * 55)

    if DISCORD_WEBHOOK_URL == "COLLE_TON_WEBHOOK_DISCORD_ICI":
        print("\n⛔  STOP : tu dois d'abord renseigner ton webhook Discord")
        print("    Ouvre vinted_bot.py et modifie DISCORD_WEBHOOK_URL\n")
        return

    seen    = load_seen()
    session = get_session()
    last_refresh = time.time()

    print(f"✅ Bot démarré — vérification toutes les {CHECK_INTERVAL // 60} min\n")

    while True:
        # Rafraîchir la session toutes les heures
        if time.time() - last_refresh > 3_600:
            session      = get_session()
            last_refresh = time.time()
            print("🔄 Session Vinted rafraîchie")

        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] Recherche « {SEARCH_QUERY} » ≤ {MAX_PRICE} €…")

        items     = search_vinted(session)
        new_count = 0

        for item in items:
            iid = str(item.get("id"))
            if iid not in seen:
                seen.add(iid)
                send_discord(item)
                new_count += 1
                time.sleep(1)           # anti-spam Discord

        save_seen(seen)

        if new_count == 0:
            print(f"  → Rien de nouveau. Prochaine vérif dans {CHECK_INTERVAL // 60} min.")
        else:
            print(f"  → {new_count} nouvelle(s) annonce(s) envoyée(s) !")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

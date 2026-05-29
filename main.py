import os
import json
import urllib.request
import urllib.parse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# БЕЗОПАСНОСТЬ: Ключи Supabase из переменных окружения
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# БЕЗОПАСНОСТЬ: Данные Telegram из переменных окружения Render
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Критическая ошибка: Переменные SUPABASE_URL или SUPABASE_KEY не настроены!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Ложка & Скалка API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

class OrderItem(BaseModel):
    id: int
    title: str
    price: int
    quantity: int

class OrderData(BaseModel):
    name: str
    phone: str
    address: str
    cart_items: list[OrderItem]

# Вспомогательная функция отправки сообщения в Телеграм
def send_telegram_notification(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Предупреждение: Telegram токены не настроены, пропускаю отправку.")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

@app.get("/")
def read_root():
    return {"status": "Сервер запущен на Render!", "restaurant": "Ложка & Скалка"}

@app.get("/api/products")
def get_products():
    try:
        response = supabase.table("products").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения меню: {str(e)}")

@app.post("/api/order")
async def create_order(order: OrderData):
    try:
        # 1. Сохраняем в Supabase
        items_list = [item.dict() for item in order.cart_items]
        new_order = {
            "customer_name": order.name,
            "customer_phone": order.phone,
            "customer_address": order.address,
            "items": items_list
        }
        response = supabase.table("orders").insert(new_order).execute()
        
        # 2. Формируем красивое сообщение для Телеграма
        order_id = response.data[0]['id'] if response.data else "Новый"
        
        tg_text = f"🚨 <b>НОВЫЙ ЗАКАЗ №{order_id}</b> 🚨\n\n"
        tg_text += f"👤 <b>Клиент:</b> {order.name}\n"
        tg_text += f"📞 <b>Телефон:</b> {order.phone}\n"
        tg_text += f"📍 <b>Адрес:</b> {order.address}\n\n"
        tg_text += "🛒 <b>Состав заказа:</b>\n"
        
        total_sum = 0
        for item in order.cart_items:
            item_total = item.price * item.quantity
            total_sum += item_total
            tg_text += f"• {item.title} — {item.quantity} шт. х {item.price} ₽ ({item_total} ₽)\n"
            
        tg_text += f"\n💰 <b>Итого к оплате: {total_sum} ₽</b>"
        
        # 3. Отправляем уведомление
        send_telegram_notification(tg_text)
        
        return {"success": True, "message": "Заказ успешно сохранен и отправлен в Telegram!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки заказа: {str(e)}")

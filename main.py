import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# БЕЗОПАСНОСТЬ: Считываем ключи из переменных окружения сервера Render
# Если сервер их не найдет (например, при локальном тесте), он выдаст ошибку
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Критическая ошибка: Переменные окружения SUPABASE_URL или SUPABASE_KEY не настроены!")

# Инициализируем клиента Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Ложка & Скалка API")

# Настройка CORS для связи с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# Структура данных заказа
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

@app.get("/")
def read_root():
    return {"status": "Сервер успешно запущен на Render!", "restaurant": "Ложка & Скалка"}

# Отдача меню из базы данных
@app.get("/api/products")
def get_products():
    try:
        response = supabase.table("products").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения меню: {str(e)}")

# Прием новых заказов
@app.post("/api/order")
async def create_order(order: OrderData):
    try:
        items_list = [item.dict() for item in order.cart_items]
        new_order = {
            "customer_name": order.name,
            "customer_phone": order.phone,
            "customer_address": order.address,
            "items": items_list
        }
        response = supabase.table("orders").insert(new_order).execute()
        return {"success": True, "message": "Заказ успешно сохранен!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения заказа: {str(e)}")

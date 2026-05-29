import os
import streamlit as st
from supabase import create_client, Client
import mimetypes

# БЕЗОПАСНОСТЬ: Считываем ключи из переменных окружения сервера Render
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Критическая ошибка: На сервере не настроены переменные SUPABASE_URL или SUPABASE_KEY!")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Админка — Ложка & Скалка", page_icon="🍳", layout="wide")
st.title("🍳 Управление рестораном «Ложка & Скалка»")

tab_orders, tab_menu_manage, tab_analytics = st.tabs(["📥 Новые заказы", "📜 Управление меню", "📈 Аналитика"])

# ВКЛАДКА ЗАКАЗОВ
with tab_orders:
    st.header("Лента активных заказов")
    try:
        orders_resp = supabase.table("orders").select("*").eq("status", "Новый").order("created_at", descending=True).execute()
        orders = orders_resp.data

        if not orders:
            st.info("Активных заказов нет. 🎉")
        else:
            for order in orders:
                with st.container():
                    st.markdown(f"### Заказ №{order['id']} (от {order['created_at'][:16].replace('T', ' ')})")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"👤 **Клиент:** {order['customer_name']}")
                        st.write(f"📞 **Телефон:** `{order['customer_phone']}`")
                        st.write(f"📍 **Адрес:** {order['customer_address']}")
                        st.write("**🛒 Состав:**")
                        total_sum = 0
                        for item in order['items']:
                            item_total = item['price'] * item['quantity']
                            total_sum += item_total
                            st.write(f"• {item['title']} — {item['quantity']} шт. x {item['price']} ₽")
                        st.markdown(f"💰 **Итого: {total_sum} ₽**")
                    with col2:
                        if st.button(f"✅ Выполнен", key=f"done_{order['id']}"):
                            supabase.table("orders").update({"status": "Выполнен"}).eq("id", order['id']).execute()
                            st.st.rerun()
                    st.markdown("---")
    except Exception as e:
        st.error(f"Ошибка загрузки заказов: {e}")

# ВКЛАДКА МЕНЮ
with tab_menu_manage:
    st.header("Добавление нового блюда")
    with st.form("add_product_form", clear_on_submit=True):
        title = st.text_input("Название блюда *")
        description = st.text_area("Описание")
        weight = st.text_input("Вес")
        price = st.number_input("Цена *", min_value=0, value=0)
        day = st.selectbox("День недели *", ["Все дни", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"])
        uploaded_file = st.file_uploader("Загрузить фото", type=["jpg", "jpeg", "png"])
        
        if st.form_submit_button("✨ Добавить блюдо"):
            if not title or price <= 0:
                st.error("Заполните поля!")
            else:
                image_url = ""
                if uploaded_file is not None:
                    try:
                        file_extension = mimetypes.guess_extension(uploaded_file.type) or '.jpg'
                        storage_file_name = f"{title}_{price}{file_extension}"
                        supabase.storage.from_("food-images").upload(path=storage_file_name, file=uploaded_file.getvalue(), file_options={"content-type": uploaded_file.type})
                        image_url = supabase.storage.from_("food-images").get_public_url(storage_file_name)
                    except Exception as e:
                        st.error(f"Ошибка загрузки фото в облако: {e}")
                
                if not image_url:
                    image_url = "https://images.unsplash.com/photo-1495521821757-a1efb6729352?q=80&w=600"

                supabase.table("products").insert({"title": title, "description": description, "weight": weight, "price": int(price), "day": day, "image": image_url}).execute()
                st.success("Добавлено!")
                st.st.rerun()

    # Список текущих блюд
    try:
        prod_resp = supabase.table("products").select("*").execute()
        for prod in prod_resp.data:
            c_img, c_info, c_del = st.columns([1, 3, 1])
            c_img.image(prod['image'], width=100)
            c_info.write(f"**{prod['title']}** — {prod['price']} ₽ ({prod['day']})")
            if c_del.button("🗑️", key=f"del_{prod['id']}"):
                supabase.table("products").delete().eq("id", prod['id']).execute()
                st.st.rerun()
    except Exception as e:
        st.error(f"Ошибка загрузки меню: {e}")

# ВКЛАДКА АНАЛИТИКИ
with tab_analytics:
    st.header("Аналитика")
    try:
        all_orders = supabase.table("orders").select("*").execute().data
        if all_orders:
            revenue = sum(item['price'] * item['quantity'] for o in all_orders for item in o['items'])
            st.metric("Общая выручка", f"{revenue} ₽")
            st.metric("Всего заказов", len(all_orders))
    except Exception as e:
        st.error(f"Ошибка аналитики: {e}")

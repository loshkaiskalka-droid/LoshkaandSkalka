import streamlit as st
import os
from supabase import create_client, Client

# Настройка страницы под мобильные телефоны
st.set_page_config(
    page_title="Админка Ложка & Скалка",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Подключение к Supabase из переменных окружения
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Ошибка: Переменные окружения SUPABASE_URL и SUPABASE_KEY не настроены на Render!")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Функция для загрузки динамических категорий из Supabase Storage
def load_categories():
    default_cats = ["Обеды", "Выпечка", "Мясо"]
    try:
        res = supabase.storage.from_("dish-images").download("categories.txt")
        if res:
            cats = res.decode("utf-8").split(",")
            return [c.strip() for c in cats if c.strip()]
    except Exception:
        try:
            cats_str = ",".join(default_cats)
            supabase.storage.from_("dish-images").upload("categories.txt", cats_str.encode("utf-8"), {"content-type": "text/plain"})
        except Exception:
            pass
    return default_cats

# Функция для сохранения нового списка категорий
def save_categories(cats_list):
    try:
        cats_str = ",".join(cats_list)
        try:
            supabase.storage.from_("dish-images").remove(["categories.txt"])
        except Exception:
            pass
        supabase.storage.from_("dish-images").upload("categories.txt", cats_str.encode("utf-8"), {"content-type": "text/plain"})
        return True
    except Exception as e:
        st.error(f"Не удалось сохранить категории: {e}")
        return False

st.title("🍳 Управление рестораном «Ложка & Скалка»")

tab1, tab2 = st.tabs(["📥 Новые заказы", "📜 Управление меню"])

# --- ВКЛАДКА 1: НОВЫЕ ЗАКАЗЫ ---
with tab1:
    st.subheader("Лента активных заказов")
    try:
        # Исправлено: в Supabase Python SDK правильный синтаксис сортировки: .order("id", desc=True)
        response = supabase.table("orders").select("*").eq("status", "new").order("id", desc=True).execute()
        orders = response.data

        if not orders:
            st.info("Активных заказов пока нет.")
        else:
            for order in orders:
                with st.container():
                    st.markdown(f"### Заказ №{order['id']} — {order['name']}")
                    st.write(f"📞 **Телефон:** {order['phone']}")
                    st.write(f"📍 **Адрес:** {order['address']}")
                    st.write("**Содержимое заказа:**")
                    
                    if isinstance(order['cart_items'], list):
                        for item in order['cart_items']:
                            st.write(f"• {item.get('title', 'Блюдо')} — {item.get('quantity', 1)} шт. ({item.get('price', 0)} ₽)")
                    else:
                        st.write(str(order['cart_items']))
                    
                    if st.button(f"✅ Выполнен (Заказ №{order['id']})", key=f"done_{order['id']}"):
                        supabase.table("orders").update({"status": "completed"}).eq("id", order["id"]).execute()
                        st.success(f"Заказ №{order['id']} выполнен!")
                        st.rerun()
                    st.markdown("---")
    except Exception as e:
        st.error(f"Ошибка загрузки заказов: {e}")

# --- ВКЛАДКА 2: УПРАВЛЕНИЕ МЕНЮ ---
with tab2:
    days_list = ["Все дни", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    categories_list = load_categories()
    
    st.markdown("### 🗂️ Управление категориями")
    st.write(f"**Текущие разделы на сайте:** {', '.join(categories_list)}")
    
    with st.expander("➕ Добавить или 🗑️ Удалить раздел"):
        cat_col1, cat_col2 = st.columns(2)
        with cat_col1:
            new_cat_name = st.text_input("Название новой категории", key="new_cat_input")
            if st.button("➕ Создать категорию"):
                if new_cat_name and new_cat_name not in categories_list:
                    categories_list.append(new_cat_name.strip())
                    if save_categories(categories_list):
                        st.success(f"Категория '{new_cat_name}' добавлена!")
                        st.rerun()
                else:
                    st.warning("Введите уникальное имя категории")
        with cat_col2:
            cat_to_delete = st.selectbox("Выберите категорию для удаления", options=categories_list)
            if st.button("🗑️ Стереть категорию", type="primary"):
                if cat_to_delete in categories_list:
                    categories_list.remove(cat_to_delete)
                    if save_categories(categories_list):
                        st.warning(f"Категория '{cat_to_delete}' удалена!")
                        st.rerun()
                        
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### ✨ Добавить новое блюдо")
        with st.form("add_product_form", clear_on_submit=True):
            new_title = st.text_input("Название блюда *")
            new_desc = st.text_area("Описание / Состав / Содержимое еды *")
            new_price = st.number_input("Цена (₽) *", min_value=0, step=10, value=300)
            new_weight = st.text_input("Вес (например, '250 г') *", value="250 г")
            new_day = st.selectbox("День доступности блюда *", options=days_list, index=0)
            new_cats = st.multiselect("Категории блюда (Выбор нескольких) *", options=categories_list)
            uploaded_file = st.file_uploader("Фотография блюда *", type=["jpg", "jpeg", "png"])
            
            # Исправлено: стандартный правильный метод Streamlit для кнопки отправки формы
            submit_add = st.form_submit_button("Добавить в базу")
            
            if submit_add:
                if not new_title or not new_desc or not uploaded_file or not new_cats:
                    st.error("Пожалуйста, заполните обязательные поля и добавьте фото!")
                else:
                    try:
                        file_extension = uploaded_file.name.split(".")[-1]
                        clean_title = "".join([c for c in new_title if c.isalnum()]).lower()
                        storage_path = f"menu/{clean_title}_{int(new_price)}.{file_extension}"
                        
                        file_data = uploaded_file.read()
                        supabase.storage.from_("dish-images").upload(storage_path, file_data, {"content-type": f"image/{file_extension}"})
                        img_url = supabase.storage.from_("dish-images").get_public_url(storage_path)
                        
                        cats_string = ", ".join(new_cats)
                        full_description_field = f"{new_desc}\n\n[CATS:]: {cats_string}"
                        
                        supabase.table("products").insert({
                            "title": new_title,
                            "description": full_description_field,
                            "price": int(new_price),
                            "weight": new_weight,
                            "day": new_day,
                            "image": img_url
                        }).execute()
                        
                        st.success(f"Блюдо '{new_title}' успешно добавлено!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка добавления: {e}")

    with col2:
        st.markdown("### ✏️ Редактировать / Удалить блюдо")
        try:
            prod_resp = supabase.table("products").select("*").order("id").execute()
            products = prod_resp.data
            
            if products:
                prod_names = [p["title"] for p in products]
                selected_prod_name = st.selectbox("Выберите блюдо для изменения", options=prod_names)
                
                chosen_prod = next(p for p in products if p["title"] == selected_prod_name)
                
                raw_desc = chosen_prod["description"] or ""
                pure_desc = raw_desc.split("\n\n[CATS:]:")[0] if "[CATS:]:" in raw_desc else raw_desc
                
                extracted_cats = []
                if "[CATS:]:" in raw_desc:
                    cats_part = raw_desc.split("\n\n[CATS:]:")[-1].strip()
                    extracted_cats = [c.strip() for c in cats_part.split(",")]
                
                st.markdown(f"**Редактируем:** {chosen_prod['title']}")
                edit_title = st.text_input("Изменить название", value=chosen_prod["title"])
                edit_desc = st.text_area("Изменить описание", value=pure_desc)
                edit_price = st.number_input("Изменить цену (₽)", min_value=0, value=int(chosen_prod["price"]))
                edit_weight = st.text_input("Изменить вес", value=chosen_prod["weight"])
                
                default_day_idx = days_list.index(chosen_prod["day"]) if chosen_prod["day"] in days_list else 0
                edit_day = st.selectbox("Изменить день доступности", options=days_list, index=default_day_idx)
                edit_cats = st.multiselect("Изменить категории", options=categories_list, default=[c for c in extracted_cats if c in categories_list])
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("💾 Сохранить изменения", use_container_width=True):
                        updated_cats_str = ", ".join(edit_cats)
                        updated_full_desc = f"{edit_desc}\n\n[CATS:]: {updated_cats_str}"
                        
                        supabase.table("products").update({
                            "title": edit_title,
                            "description": updated_full_desc,
                            "price": int(edit_price),
                            "weight": edit_weight,
                            "day": edit_day
                        }).eq("id", chosen_prod["id"]).execute()
                        st.success("Данные обновлены!")
                        st.rerun()
                        
                with col_btn2:
                    if st.button("🗑️ Полностью удалить блюдо", type="primary", use_container_width=True):
                        supabase.table("products").delete().eq("id", chosen_prod["id"]).execute()
                        st.warning(f"Блюдо '{chosen_prod['title']}' удалено!")
                        st.rerun()
            else:
                st.info("В меню пока пусто.")
        except Exception as e:
            st.error(f"Ошибка редактора: {e}")

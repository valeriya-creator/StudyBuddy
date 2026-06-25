import streamlit as st
import sqlite3
import numpy as np
from hashlib import sha256

if 'theme' not in st.session_state: st.session_state.theme = 'Тёмная'
if 'accent' not in st.session_state: st.session_state.accent = '#3b82f6'

def get_css(theme, accent):
    if theme == 'Тёмная':
        bg_main = '#0f172a'; bg_side = '#1e293b'; bg_card = '#1e293b'; border = '#334155'; text = '#e2e8f0'; text_sec = '#94a3b8'; msg_bg = '#334155'; msg_txt = 'white'
    else:
        bg_main = '#f8fafc'; bg_side = '#ffffff'; bg_card = '#ffffff'; border = '#e2e8f0'; text = '#0f172a'; text_sec = '#64748b'; msg_bg = '#e2e8f0'; msg_txt = 'black'
    return f"""
    <style>
        #MainMenu, footer, header {{visibility: hidden;}}
        div[data-testid="collapsedControl"] {{display: none;}}
        .stApp {{ background-color: {bg_main}; color: {text}; }}
        section[data-testid="stSidebar"] {{ background-color: {bg_side}; border-right: 1px solid {border}; }}
        .card {{ background-color: {bg_card}; padding: 20px; border-radius: 12px; border: 1px solid {border}; margin-bottom: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
        .card-high {{ border-left: 4px solid {accent}; }}
        .card-mid {{ border-left: 4px solid #f59e0b; }}
        .stButton > button {{ background-color: {accent}; color: white; border: none; border-radius: 8px; font-weight: bold; padding: 8px 16px; }}
        .stButton > button:hover {{ filter: brightness(1.1); transform: translateY(-1px); }}
        .stTextInput > div > div > input {{ background-color: {bg_main} !important; color: {text} !important; border: 1px solid {border} !important; }}
        h1, h2, h3, h4, p, span, label {{ color: {text} !important; }}
        .stRadio > label {{ color: {text_sec} !important; }}
    </style>
    """

st.markdown(get_css(st.session_state.theme, st.session_state.accent), unsafe_allow_html=True)

conn = sqlite3.connect('studybuddy.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT, password TEXT, name TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS profiles (user_id INTEGER, topics TEXT, levels TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS likes (from_id INTEGER, to_id INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY, user1_id INTEGER, user2_id INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER, from_user_id INTEGER, text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
c.execute('''CREATE TABLE IF NOT EXISTS materials (id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER, from_user_id INTEGER, title TEXT, link TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, to_user_id INTEGER, text TEXT, is_read INTEGER DEFAULT 0)''')
conn.commit()

ALL_TOPICS = ['Математика', 'Программирование', 'Физика', 'Английский язык', 'История']

def add_notif(user_id, text):
    c.execute("INSERT INTO notifications (to_user_id, text) VALUES (?, ?)", (user_id, text))
    conn.commit()

def get_vector(t, l):
    if not t: return np.zeros(len(ALL_TOPICS))
    tm = dict(zip(t.split(','), l.split(',')))
    return np.array([float(tm.get(x, 0)) for x in ALL_TOPICS])

def cosine(v1, v2):
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    return np.dot(v1, v2) / (n1 * n2) if n1 > 0 and n2 > 0 else 0

st.set_page_config(page_title="StudyBuddy", layout="wide", initial_sidebar_state="expanded")
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'current_chat' not in st.session_state: st.session_state.current_chat = None

if not st.session_state.user_id:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("# 📚 StudyBuddy")
        st.markdown("Вместе учиться легче")
        t1, t2 = st.tabs(["Вход", "Регистрация"])
        with t1:
            with st.form("lf"):
                e, p = st.text_input("Email"), st.text_input("Пароль", type="password")
                if st.form_submit_button("Войти"):
                    ph = sha256(p.encode()).hexdigest()
                    c.execute("SELECT id FROM users WHERE email=? AND password=?", (e, ph))
                    u = c.fetchone()
                    if u: st.session_state.user_id = u[0]; st.rerun()
                    else: st.error("Неверные данные")
        with t2:
            with st.form("rf"):
                e, p, n = st.text_input("Email"), st.text_input("Пароль", type="password"), st.text_input("Имя")
                if st.form_submit_button("Зарегистрироваться"):
                    ph = sha256(p.encode()).hexdigest()
                    try: c.execute("INSERT INTO users VALUES (NULL, ?, ?, ?)", (e, ph, n)); conn.commit(); st.success("Готово!")
                    except: st.error("Email занят")

else:
    uid = st.session_state.user_id
    with st.sidebar:
        c.execute("SELECT COUNT(*) FROM notifications WHERE to_user_id=? AND is_read=0", (uid,))
        unread_count = c.fetchone()[0]
        
        bell_text = f"🔔 Уведомления ({unread_count})" if unread_count > 0 else "🔔 Нет новых"
        if st.button(bell_text, use_container_width=True):
            st.session_state.show_notifs = not st.session_state.get('show_notifs', False)
            
        if st.session_state.get('show_notifs', False):
            c.execute("SELECT id, text FROM notifications WHERE to_user_id=? ORDER BY id DESC LIMIT 5", (uid,))
            notifs = c.fetchall()
            if not notifs: st.info("Пусто")
            for n in notifs: st.write(f"• {n[1]}")
            if st.button("Прочитано", use_container_width=True):
                c.execute("UPDATE notifications SET is_read=1 WHERE to_user_id=?", (uid,))
                conn.commit(); st.session_state.show_notifs = False; st.rerun()
        
        st.markdown("---")
        menu = st.radio("Меню", ["🏠 Главная", "👤 Профиль", "🔍 Поиск", "💬 Чаты", "🚪 Выход"])
        st.markdown("---")
        st.subheader("⚙️ Настройки")
        st.session_state.theme = st.radio("Тема", ["Тёмная", "Светлая"], index=0 if st.session_state.theme=='Тёмная' else 1)
        st.session_state.accent = st.color_picker("Цвет акцентов", st.session_state.accent)

    if menu == "🏠 Главная":
        st.header("Добро пожаловать!")
        st.write("Найдите партнера, поставьте взаимный лайк и обменивайтесь знаниями.")
        c.execute("SELECT COUNT(*) FROM users"); st.metric("Всего в системе", c.fetchone()[0])

    elif menu == "👤 Профиль":
        st.header("Настройки профиля")
        c.execute("SELECT name FROM users WHERE id=?", (uid,)); st.info(f"Привет, {c.fetchone()[0]}!")
        sel = st.multiselect("Ваши темы", ALL_TOPICS)
        if sel:
            lv = {t: st.number_input(f"Ур. {t}", 1, 3, key=f"l_{t}") for t in sel}
            if st.button("Сохранить"):
                c.execute("DELETE FROM profiles WHERE user_id=?", (uid,))
                c.execute("INSERT INTO profiles VALUES (?, ?, ?)", (uid, ",".join(sel), ",".join([str(lv[t]) for t in sel])))
                conn.commit(); st.success("Сохранено!")

    elif menu == "🔍 Поиск":
        st.header("Рекомендации")
        c.execute("SELECT topics, levels FROM profiles WHERE user_id=?", (uid,))
        md = c.fetchone()
        if not md or not md[0]: st.warning("Сначала заполните профиль!")
        else:
            mv = get_vector(md[0], md[1])
            c.execute("SELECT to_id FROM likes WHERE from_id=?", (uid,)); liked = [r[0] for r in c.fetchall()]
            c.execute("SELECT user_id, topics, levels FROM profiles WHERE user_id != ?", (uid,))
            recs = sorted([{'id':x[0], 'sim':cosine(mv, get_vector(x[1], x[2])), 't':x[1]} for x in c.fetchall() if x[0] not in liked and cosine(mv, get_vector(x[1], x[2]))>0.1], key=lambda x: x['sim'], reverse=True)
            
            for r in recs[:5]:
                c.execute("SELECT name FROM users WHERE id=?", (r['id'],)); n = c.fetchone()[0]; p = round(r['sim']*100)
                st.markdown(f"<div class='card {'card-high' if p>=70 else 'card-mid'}'><h4>{n}</h4><p style='opacity:0.8;'>Совпадение: {p}% | {r['t']}</p></div>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("❤️ Нравится", key=f"l_{r['id']}"):
                        to_uid = r['id']
                        c.execute("INSERT INTO likes VALUES (?, ?)", (uid, to_uid))
                        add_notif(to_uid, "Кто-то поставил вам лайк!")
                        c.execute("SELECT * FROM likes WHERE from_id=? AND to_id=?", (to_uid, uid))
                        if c.fetchone(): 
                            c.execute("INSERT INTO matches VALUES (NULL, ?, ?)", (min(uid, to_uid), max(uid, to_uid)))
                            conn.commit()
                            add_notif(uid, "У вас новое совпадение!")
                            add_notif(to_uid, "У вас новое совпадение!")
                            st.balloons(); st.success("Совпадение!")
                        else: conn.commit()
                        st.rerun()
                with c2:
                    if st.button("Пропустить", key=f"s_{r['id']}"): c.execute("INSERT INTO likes VALUES (?, ?)", (uid, r['id'])); conn.commit(); st.rerun()

    elif menu == "💬 Чаты":
        st.header("Сообщения")
        c.execute("SELECT id, user1_id, user2_id FROM matches WHERE user1_id=? OR user2_id=?", (uid, uid))
        matches = c.fetchall()
        if not matches: st.info("Нет совпадений")
        elif st.session_state.current_chat is None:
            for m in matches:
                pid = m[2] if m[1] == uid else m[1]
                c.execute("SELECT name FROM users WHERE id=?", (pid,))
                if st.button(f"💬 {c.fetchone()[0]}", key=f"m_{m[0]}", use_container_width=True): st.session_state.current_chat = m[0]; st.rerun()
        else:
            m_id = st.session_state.current_chat
            c.execute("SELECT user1_id, user2_id FROM matches WHERE id=?", (m_id,)); md = c.fetchone()
            pid = md[1] if md[0] == uid else md[0]
            c.execute("SELECT name FROM users WHERE id=?", (pid,)); pn = c.fetchone()[0]
            c.execute("SELECT name FROM users WHERE id=?", (uid,)); my_name = c.fetchone()[0]
            
            st.markdown(f"Диалог с **{pn}**")
            if st.button("← Назад"): st.session_state.current_chat = None; st.rerun()
            
            with st.expander("📎 Поделиться материалом"):
                mt, ml = st.text_input("Название"), st.text_input("Ссылка")
                if st.button("Отправить"): c.execute("INSERT INTO materials VALUES (NULL, ?, ?, ?, ?)", (m_id, uid, mt, ml)); conn.commit(); st.success("Добавлено!")
            st.markdown("---")
            
            c.execute("SELECT from_user_id, title, link FROM materials WHERE match_id=?", (m_id,))
            for mat in c.fetchall():
                c.execute("SELECT name FROM users WHERE id=?", (mat[0],))
                st.markdown(f"📎 **{c.fetchone()[0]}** поделился: [{mat[1]}]({mat[2]})")

            c.execute("SELECT from_user_id, text FROM messages WHERE match_id=? ORDER BY created_at ASC", (m_id,))
            for msg in c.fetchall():
                c.execute("SELECT name FROM users WHERE id=?", (msg[0],)); auth = c.fetchone()[0]
                is_me = msg[0] == uid
                bg = st.session_state.accent if is_me else ('#334155' if st.session_state.theme=='Тёмная' else '#e2e8f0')
                txt_c = "white" if is_me else ("white" if st.session_state.theme=='Тёмная' else "black")
                st.markdown(f"<div style='display:flex; justify-content:{'flex-end' if is_me else 'flex-start'}; margin-bottom:10px;'><div style='background-color:{bg}; color:{txt_c}; padding:10px 15px; border-radius:12px; max-width:70%;'><b style='font-size:0.8em; opacity:0.8;'>{auth}</b><br>{msg[1]}</div></div>", unsafe_allow_html=True)

            new_msg = st.chat_input("Написать...")
            if new_msg: 
                c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?)", (m_id, uid, new_msg))
                add_notif(pid, f"Новое сообщение от {my_name}")
                conn.commit(); st.rerun()

    elif menu == "🚪 Выход":
        st.session_state.user_id = None; st.session_state.current_chat = None; st.rerun()

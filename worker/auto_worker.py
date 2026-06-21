import os
import json
from flask import Flask, request, jsonify
from apify_client import ApifyClient
from supabase import create_client, Client
import google.generativeai as genai

# --- НАСТРОЙКИ И КЛЮЧИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ---
APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "ТВОЙ_APIFY_ТОКЕН")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "ТВОЙ_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "ТВОЙ_SUPABASE_ANON_KEY")
AI_API_KEY = os.environ.get("AI_API_KEY", "ТВОЙ_GEMINI_API_KEY") # Или OpenAI

# Инициализация клиентов
apify = ApifyClient(APIFY_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=AI_API_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash') # Быстрая и дешевая модель

app = Flask(__name__)

# --- 1. ПАРСИНГ ЧЕРЕЗ APIFY ---
def scrape_instagram_profile(username):
    clean_username = username.split("instagram.com/")[-1].replace("/", "").split("?")[0] if "instagram.com" in username else username
    run = apify.actor("apify/instagram-scraper").call(run_input={"directUrls": [f"https://www.instagram.com/{clean_username}/"], "resultsType": "details"})
    for item in apify.dataset(run["defaultDatasetId"]).iterate_items():
        return item
    return None

def scrape_tiktok_profile(username):
    clean_username = username.split("@")[-1].split("?")[0] if "tiktok.com" in username else username.replace("@", "")
    run = apify.actor("clockworks/tiktok-scraper").call(run_input={"profiles": [clean_username], "resultsPerPage": 1})
    for item in apify.dataset(run["defaultDatasetId"]).iterate_items():
        return item
    return None

# --- 2. АНАЛИЗ С ПОМОЩЬЮ ИИ ---
def analyze_with_ai(platform, profile_data):
    if not profile_data:
        return {"risk_score": 0, "reasons": ["Данные не найдены"]}

    # Собираем выжимку для ИИ, чтобы не тратить токены на лишний мусор
    if platform == "instagram":
        summary = f"""
        Платформа: Instagram
        Подписчики: {profile_data.get('followersCount', 0)}
        Подписки: {profile_data.get('followsCount', 0)}
        Посты: {profile_data.get('postsCount', 0)}
        Верификация: {profile_data.get('isVerified', False)}
        Описание (Bio): {profile_data.get('biography', '')}
        """
    else:
        stats = profile_data.get("userInfo", {}).get("stats", {})
        user_info = profile_data.get("userInfo", {}).get("user", {})
        summary = f"""
        Платформа: TikTok
        Подписчики: {stats.get('followerCount', 0)}
        Подписки: {stats.get('followingCount', 0)}
        Посты: {stats.get('videoCount', 0)}
        Верификация: {user_info.get('verified', False)}
        Описание (Bio): {user_info.get('signature', '')}
        """

    # Промпт для нейросети
    prompt = f"""
    Выступи в роли эксперта по кибербезопасности. Проанализируй данные профиля и определи вероятность того, что это мошенник (скамер). 
    Обрати внимание на спам-слова в описании (крипта, инвестиции, заработок, сигналы), аномальное соотношение подписок/подписчиков.
    
    Данные профиля:
    {summary}

    Верни ответ СТРОГО в формате JSON без markdown и лишних слов:
    {{
        "risk_score": число от 0 до 100,
        "reasons": ["Причина 1", "Причина 2"]
    }}
    """
    
    try:
        response = ai_model.generate_content(prompt)
        # Очищаем ответ ИИ от возможных артефактов markdown
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)
        return result
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return {"risk_score": 50, "reasons": ["Ошибка анализа ИИ, требуется ручная проверка"]}

# --- 3. ЗАПИСЬ В БАЗУ ДАННЫХ (SUPABASE) ---
def save_incident_to_supabase(target_username, platform, ai_report, raw_data):
    try:
        # Формируем структуру данных для твоей таблицы
        incident_data = {
            "target_user": target_username,
            "platform": platform,
            "risk_score": ai_report.get("risk_score", 0),
            "reasons": ai_report.get("reasons", []),
            "status": "pending_review", # Статус для дашборда
            "raw_profile_data": raw_data # Сохраняем сырые данные на всякий случай
        }
        
        # Запись в таблицу 'incidents' (убедись, что она создана в Supabase)
        response = supabase.table("incidents").insert(incident_data).execute()
        return response.data
    except Exception as e:
        print(f"Ошибка сохранения в Supabase: {e}")
        return None

# --- 4. API ЭНДПОИНТ ДЛЯ ЗАПУСКА ---
@app.route('/scan', methods=['POST', 'GET'])
def scan_profile():
    platform = request.args.get('platform') or request.json.get('platform')
    username = request.args.get('username') or request.json.get('username')

    if not platform or not username:
        return jsonify({"error": "Требуются параметры platform и username"}), 400

    platform = platform.lower()
    
    # 1. Парсинг
    if platform == "instagram":
        raw_data = scrape_instagram_profile(username)
    elif platform == "tiktok":
        raw_data = scrape_tiktok_profile(username)
    else:
        return jsonify({"error": "Платформа не поддерживается"}), 400

    if not raw_data:
        return jsonify({"error": "Профиль не найден или закрыт"}), 404

    # 2. ИИ Анализ
    ai_report = analyze_with_ai(platform, raw_data)

    # 3. Сохранение в Supabase (только если есть подозрения, или можно сохранять всё)
    # Например, сохраняем в дашборд, если риск больше 30%
    if ai_report.get("risk_score", 0) >= 30:
        db_record = save_incident_to_supabase(username, platform, ai_report, raw_data)
        ai_report["db_status"] = "saved_to_dashboard"
    else:
        ai_report["db_status"] = "ignored_low_risk"

    return jsonify({
        "target": username,
        "platform": platform,
        "ai_analysis": ai_report
    }), 200

# --- 5. ЗАПУСК ДЛЯ RENDER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

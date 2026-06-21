import os
import json
from flask import Flask, request, jsonify
from apify_client import ApifyClient
from supabase import create_client, Client
from groq import Groq

# --- НАСТРОЙКИ И КЛЮЧИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ---
APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "ТВОЙ_APIFY_ТОКЕН")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "ТВОЙ_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "ТВОЙ_SUPABASE_ANON_KEY")
AI_API_KEY = os.environ.get("AI_API_KEY", "ТВОЙ_AI_КЛЮЧ") # <--- Ключ Groq

# Инициализация клиентов

apify = ApifyClient(APIFY_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
groq_client = Groq(api_key=AI_API_KEY) # <--- Инициализация клиента Groq

app = Flask(__name__)

# [ ... Функции парсинга scrape_instagram_profile и scrape_tiktok_profile остаются БЕЗ ИЗМЕНЕНИЙ ... ]

# --- 2. АНАЛИЗ С ПОМОЩЬЮ ИИ (GROQ) ---
def analyze_with_ai(platform, profile_data):
    if not profile_data:
        return {"risk_score": 0, "reasons": ["Данные не найдены"]}

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

    prompt = f"""
    Выступи в роли эксперта по кибербезопасности. Проанализируй данные профиля и определи вероятность того, что это мошенник.
    Обрати внимание на слова в описании (крипта, инвестиции, заработок), аномальное соотношение подписок/подписчиков.
    
    Данные профиля:
    {summary}

    Верни ответ СТРОГО в формате JSON со следующими ключами:
    "risk_score" (число от 0 до 100)
    "reasons" (массив строк с причинами)
    """
    
    try:
        # Вызов API Groq
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": "Ты AI-аналитик. Ты отвечаешь только валидным JSON."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            # Можно использовать llama3-8b-8192 для скорости или llama3-70b-8192 для ума
            model="llama3-70b-8192", 
            # Эта настройка ЗАСТАВЛЯЕТ Groq вернуть чистый JSON без markdown (никаких ```json)
            response_format={"type": "json_object"} 
        )
        
        # Получаем ответ и сразу парсим, так как это уже чистый JSON
        response_text = chat_completion.choices[0].message.content
        result = json.loads(response_text)
        return result
        
    except Exception as e:
        print(f"Ошибка ИИ Groq: {e}")
        return {"risk_score": 50, "reasons": ["Ошибка анализа ИИ, требуется ручная пропись"]}
                                              
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

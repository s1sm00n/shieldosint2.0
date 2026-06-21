import os
import time
import json
from apify_client import ApifyClient
from groq import Groq
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Инициализация
apify = ApifyClient(os.environ.get("APIFY_TOKEN"))
groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def log_to_system(message):
    """Пишем технические логи в Supabase"""
    supabase.table("system_logs").insert({"message": message}).execute()
    print(f"[{time.strftime('%X')}] {message}")

def analyze_content(dossier):
    prompt = f"Проанализируй данные на мошенничество: {json.dumps(dossier)}"
    response = groq.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-8b-8192"
    )
    return response.choices[0].message.content

def run_tiktok():
    log_to_system("Запуск парсинга TikTok...")
    run = apify.actor("clockworks/tiktok-scraper").call(
        run_input={"hashtags": ["инвестиции"], "resultsLimit": 3}
    )
    return apify.dataset(run.get("defaultDatasetId")).list_items().items

def run_instagram():
    log_to_system("Запуск парсинга Instagram...")
    # Instagram требует больше ресурсов, используем официальный скрейпер
    run = apify.actor("apify/instagram-scraper").call(
        run_input={
            "hashtags": ["инвестиции"],
            "resultsLimit": 3,
            # ВАЖНО: сюда нужно вставить куки, если Instagram будет блокировать
            # "sessionCookies": [...] 
        }
    )
    return apify.dataset(run.get("defaultDatasetId")).list_items().items

def process_items(items, platform):
    for item in items:
        # Унификация данных для анализа
        url = item.get("webVideoUrl") or item.get("url")
        text = item.get("title") or item.get("caption")
        
        if supabase.table("incidents").select("id").eq("url", url).execute().data:
            continue
            
        dossier = {"platform": platform, "text": text, "author": item.get("ownerUsername") or item.get("authorMeta", {}).get("name")}
        analysis = analyze_content(dossier)
        
        supabase.table("incidents").insert({
            "platform": platform,
            "url": url,
            "description": text,
            "analysis": analysis
        }).execute()
        log_to_system(f"Инцидент найден: {platform} | {url}")

if __name__ == "__main__":
    while True:
        try:
            # Парсим обе сети
            tiktok_data = run_tiktok()
            process_items(tiktok_data, "TikTok")
            
            insta_data = run_instagram()
            process_items(insta_data, "Instagram")
            
            log_to_system("Цикл завершен, сон 15 минут...")
        except Exception as e:
            log_to_system(f"ОШИБКА: {str(e)}")
            
        time.sleep(900)

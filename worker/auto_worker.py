import os
import time
import json
from apify_client import ApifyClient
from groq import Groq
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

apify = ApifyClient(os.environ.get("APIFY_TOKEN"))
AI = AI(api_key=os.environ.get("AI_API_KEY"))
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def log_to_system(message):
    try:
        supabase.table("system_logs").insert({"message": message}).execute()
    except Exception:
        pass
    print(f"[{time.strftime('%X')}] {message}")

def advanced_ai_analysis(dossier):
    """
    Ультимативный промпт под критерии хакатона AI Media Watch.
    Оценивает риски, выявляет паттерны мошенничества и ИИ-генерацию.
    """
    prompt = f"""
    Ты — эксперт кибербезопасности и OSINT-аналитик. Проведи жесткий аудит медиа-контента на основе следующих данных:
    {json.dumps(dossier, ensure_ascii=False)}

    Твоя задача — выявить признаки незаконного игорного бизнеса, финансовых пирамид и мошенничества в РК.
    
    СТРОГО следуй инструкции и верни ответ В ФОРМАТЕ JSON (и ничего кроме JSON!):
    {{
      "risk_score": <число от 0 до 100>,
      "verdict": "<CASINO / PYRAMID / SCAM / CLEAN>",
      "ai_generated_evidence": "<есть ли признаки генерации текста/видео через ИИ, дипфейки, робо-озвучка. Опиши подробно>",
      "detected_patterns": ["<перечисли найденные маркеры: реферальные ссылки, обещания легких денег, скрытые призывы>"],
      "explanation": "<развернутое аналитическое объяснение и обоснование решения для презентации>"
    }}
    """
    
    try:
        response = groq.chat.completions.create(
            messages=[
                {"role": "system", "content": "Выдавай ответ строго в формате валидного JSON без разметки markdown."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        log_to_system(f"Ошибка Groq: {str(e)}")
        return None

def run_tiktok():
    log_to_system("Глубокий парсинг TikTok по триггерам...")
    # Ищем по целевым триггерам хакатона
    run = apify.actor("clockworks/tiktok-scraper").call(
        run_input={
            "hashtags": ["инвестиции", "заработок", "казино"], 
            "resultsLimit": 5,
            "shouldDownloadVideos": False,
            "shouldDownloadSubtitles": True # Тянем субтитры, если они есть
        }
    )
    return apify.dataset(run.get("defaultDatasetId")).list_items().items

def run_instagram():
    log_to_system("Глубокий парсинг Instagram по триггерам...")
    run = apify.actor("apify/instagram-scraper").call(
        run_input={
            "search": "легкий заработок казахстан",
            "resultsLimit": 5,
            "expandTypes": ["comments", "detailed_video_info"]
        }
    )
    return apify.dataset(run.get("defaultDatasetId")).list_items().items

def process_and_analyze():
    # Собираем данные
    platforms = [("TikTok", run_tiktok), ("Instagram", run_instagram)]
    
    for platform_name, parser_func in platforms:
        try:
            items = parser_func()
            for item in items:
                url = item.get("webVideoUrl") or item.get("url") or item.get("inputUrl")
                if not url:
                    continue
                
                # Проверяем дубликаты
                if supabase.table("incidents").select("id").eq("url", url).execute().data:
                    continue
                
                # Собираем максимум текстовых маркеров из метаданных (текст, субтитры, теги)
                video_text = item.get("title") or item.get("caption") or ""
                subtitles = " ".join([s.get("text", "") for s in item.get("subtitles", [])])
                comments = " ".join([c.get("text", "") for c in item.get("latestComments", [])])
                
                full_transcription = f"{video_text} {subtitles} {comments}"
                
                dossier = {
                    "platform": platform_name,
                    "url": url,
                    "raw_text": full_transcription,
                    "author": item.get("authorMeta", {}).get("name") or item.get("ownerUsername"),
                    "view_count": item.get("playCount") or item.get("videoPlayCount", 0),
                    "timestamp": item.get("createTimeISO") or item.get("timestamp")
                }
                
                analysis = advanced_ai_analysis(dossier)
                if not analysis:
                    continue
                
                # Пишем структурированные данные для красивых графиков на фронтенде
                supabase.table("incidents").insert({
                    "platform": platform_name,
                    "url": url,
                    "description": video_text[:500],
                    "risk_score": analysis.get("risk_score", 0),
                    "verdict": analysis.get("verdict", "CLEAN"),
                    "ai_evidence": analysis.get("ai_generated_evidence", ""),
                    "patterns": analysis.get("detected_patterns", []),
                    "analysis_text": analysis.get("explanation", "")
                }).execute()
                
                log_to_system(f"Инцидент внесен [{platform_name}]: {analysis.get('verdict')} (Риск: {analysis.get('risk_score')})")
                
        except Exception as e:
            log_to_system(f"Ошибка обработки {platform_name}: {str(e)}")

if __name__ == "__main__":
    log_to_system("Сервис AI Media Watch запущен в облаке Render.")
    while True:
        process_and_analyze()
        log_to_system("Цикл завершен. Сон 10 минут...")
        time.sleep(600)

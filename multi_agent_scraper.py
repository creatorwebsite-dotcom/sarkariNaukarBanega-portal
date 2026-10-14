import os
import re
import json
import time
import random
import hashlib
import urllib.request
import urllib.error
import ssl
from datetime import datetime
from bs4 import BeautifulSoup

# SSL verification bypass for government/older portals
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

DATABASE_FILE = "jobs_database.json"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# 8 Top Trusted Recruitment Sources
SOURCES = [
    {"name": "SarkariResult", "url": "https://www.sarkariresult.com/"},
    {"name": "FreeJobAlert", "url": "https://www.freejobalert.com/"},
    {"name": "RojgarResult", "url": "https://www.rojgarresult.com/"},
    {"name": "SarkariExam", "url": "https://www.sarkariexam.com/"},
    {"name": "IndGovtJobs", "url": "https://www.indgovtjobs.in/"},
    {"name": "FreshersNow", "url": "https://www.freshersnow.com/government-jobs-india/"},
    {"name": "CareerPower", "url": "https://www.careerpower.in/upcoming-government-exams.html"},
    {"name": "JagranJosh", "url": "https://www.jagranjosh.com/articles-sarkari-naukri-1288164377-1"}
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
]

def detect_category(title):
    t = title.lower()
    if any(k in t for k in ["result", "merit list", "cutoff", "cut off", "score card", "marks"]):
        return "Result"
    elif any(k in t for k in ["admit card", "hall ticket", "call letter", "exam date", "exam city"]):
        return "Admit Card"
    elif any(k in t for k in ["answer key", "objection"]):
        return "Answer Key"
    elif any(k in t for k in ["syllabus", "exam pattern"]):
        return "Syllabus"
    elif any(k in t for k in ["admission", "counselling", "entrance"]):
        return "Admission"
    return "Latest Jobs"

# =====================================================================
# OPTION A: SMART HUMAN STRUCTURING & SEO FORMATTING ENGINE (ALWAYS ON)
# =====================================================================
def generate_option_a_content(title, category, source_name):
    today_str = datetime.now().strftime("%d %B %Y")
    clean_title = re.sub(r'\s+', ' ', title).strip()

    intro_templates = [
        f"Sarkari naukri ki taiyari kar rahe candidates ke liye badi khabar hai. Hal hi mein <strong>{clean_title}</strong> ke tahat naya official update jari kiya gaya hai. Agar aap bhi is bharti prakriya ka hissa banna chahte hain, toh niche di gayi puri jankari dhyan se padhein.",
        f"Desh bhar ke yuvaon ke liye ek aur shandaar mauka samne aaya hai. <strong>{clean_title}</strong> ka official notification aur zaroori details ab uplabdh hain. Yahan humne aapki suvidha ke liye eligibility, age limit aur apply karne ka pura tarika asaan shabdon mein samjhaya hai.",
        f"Competitive exams ki taiyari karne wale abhyarthiyon ke liye mahatvapurna update: <strong>{clean_title}</strong> se judi taaza jankari jari ho chuki hai. Aaiye jante hain is notification ki mukhya baatein aur aavedan ki prakriya."
    ]

    intro = random.choice(intro_templates)

    structured_block = f"""
<div class="human-article-box">
    <p>{intro}</p>
    <h4>📋 Notification Overview ({today_str})</h4>
    <ul>
        <li><strong>Post / Update Name:</strong> {clean_title}</li>
        <li><strong>Category:</strong> {category}</li>
        <li><strong>Application Mode:</strong> Online (Official Portal ke madhyam se)</li>
        <li><strong>Selection Process:</strong> Written Exam / Skill Test / Document Verification (Post ke anusar)</li>
    </ul>
    <h4>💡 Candidates Ke Liye Zaroori Salah (Expert Tips)</h4>
    <p>Form bharte samay ya result/admit card check karte waqt apna <strong>Original Notification PDF</strong> ek baar zaroor verify karein. Apne sabhi documents jaise Aadhar Card, Educational Certificates, Photo aur Signature pehle se scan karke rakhein taaki aakhri tarikh ke server rush se bacha ja sake.</p>
    <h4>✅ Step-by-Step Kaise Check / Apply Karein?</h4>
    <ol>
        <li>Sabse pehle niche diye gaye <strong>Official Link</strong> par click karein.</li>
        <li>Home page par <em>"{clean_title}"</em> wale section ko open karein.</li>
        <li>Apni basic details aur qualification dhyanpurvak bharein.</li>
        <li>Final submit karne ke baad confirmation page ka printout ya PDF apne phone/computer mein zaroor save kar lein.</li>
    </ol>
</div>
"""
    return structured_block.strip()

# =====================================================================
# OPTION B: GEMINI AI NATURAL HUMAN WRITER (WITH MULTI-MODEL AUTO-FIX)
# =====================================================================
def generate_option_b_ai_summary(title, category):
    if not GEMINI_API_KEY:
        return None

    prompt = (
        f"You are an experienced Indian career counselor and human content writer. "
        f"Write a natural, original, human-sounding 2-paragraph editorial overview in simple Hinglish/English "
        f"for the recruitment update: '{title}' (Category: {category}). "
        f"Do not sound robotic. Explain why this update matters for aspirants and give 2 practical preparation or application tips. "
        f"Keep it concise and SEO-friendly."
    )

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 300
        }
    }).encode("utf-8")

    # Multiple latest Gemini models to completely prevent 404 Not Found errors
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest"
    ]

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        ai_text = parts[0]["text"].strip()
                        return f"<div class='ai-editorial'><p>{ai_text}</p></div>"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue  # Try next model automatically
            elif e.code == 429:
                time.sleep(2)
                break
            else:
                break
        except Exception:
            break

    return None

# =====================================================================
# HYBRID ENGINE: COMBINING OPTION B + OPTION A FOR HIGH SEO RATING
# =====================================================================
def build_hybrid_human_post(title, link, source_name, use_ai=True):
    category = detect_category(title)
    option_a_html = generate_option_a_content(title, category, source_name)
    option_b_html = None

    if use_ai and GEMINI_API_KEY:
        option_b_html = generate_option_b_ai_summary(title, category)

    if option_b_html:
        full_description = f"{option_b_html}\n<hr/>\n{option_a_html}"
        engine_used = "Hybrid (Option B AI + Option A SEO)"
    else:
        full_description = option_a_html
        engine_used = "Hybrid (Option A Smart Human Engine)"

    job_id = hashlib.md5(f"{title}_{link}".encode("utf-8")).hexdigest()[:12]
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_display = datetime.now().strftime("%d %b %Y")

    return {
        "id": job_id,
        "title": title,
        "category": category,
        "source": source_name,
        "link": link,
        "url": link,
        "apply_link": link,
        "date": date_display,
        "post_date": date_display,
        "updated_at": now_iso,
        "summary": re.sub(r'<[^>]+>', '', full_description)[:220] + "...",
        "description": full_description,
        "content": full_description,
        "engine": engine_used,
        "status": "published",
        "seo_keywords": f"{title}, {category}, Sarkari Result, Latest Govt Jobs 2026, Online Form"
    }

def scrape_source(source):
    found_items = []
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    req = urllib.request.Request(source["url"], headers=headers)
    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                text = re.sub(r'\s+', ' ', a_tag.get_text()).strip()
                href = a_tag["href"].strip()

                # Filter valid recruitment headlines
                if 18 <= len(text) <= 130 and any(
                    kw in text.lower() for kw in [
                        "online form", "recruitment", "vacancy", "bharti", "result",
                        "admit card", "answer key", "syllabus", "apply online", "notification", "2026"
                    ]
                ):
                    if href.startswith("/"):
                        base = "/".join(source["url"].split("/")[:3])
                        href = base + href
                    if href.startswith("http"):
                        found_items.append((text, href))
    except Exception as e:
        print(f"[Warning] Could not fetch {source['name']}: {e}")

    return found_items[:15]  # Top 15 latest items per source

def load_existing_database():
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "jobs" in data:
                    return data["jobs"]
        except Exception:
            pass
    return []

def main():
    print("🚀 Starting Hybrid Multi-Agent Scraper (Option A + Option B Combo)...")
    existing_jobs = load_existing_database()
    existing_titles = {j.get("title", "").lower().strip() for j in existing_jobs if isinstance(j, dict)}

    new_jobs = []
    ai_calls_count = 0
    MAX_AI_CALLS_PER_RUN = 15  # Protects free tier rate limit while keeping run fast

    for source in SOURCES:
        print(f"🔍 Scanning {source['name']}...")
        items = scrape_source(source)
        for title, link in items:
            norm_title = title.lower().strip()
            if norm_title in existing_titles:
                continue

            use_ai_now = ai_calls_count < MAX_AI_CALLS_PER_RUN
            job_entry = build_hybrid_human_post(title, link, source["name"], use_ai=use_ai_now)
            if use_ai_now and GEMINI_API_KEY:
                ai_calls_count += 1
                time.sleep(1.2)  # Smooth delay for API safety

            new_jobs.append(job_entry)
            existing_titles.add(norm_title)

        time.sleep(random.uniform(0.5, 1.5))

    print(f"✅ New Unique Updates Found: {len(new_jobs)}")
    updated_database = new_jobs + existing_jobs
    updated_database = updated_database[:500]  # Keep database fast & clean with latest 500 posts

    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_database, f, ensure_ascii=False, indent=2)

    print(f"🎉 Successfully saved {len(updated_database)} total posts to {DATABASE_FILE}!")

if __name__ == "__main__":
    main()

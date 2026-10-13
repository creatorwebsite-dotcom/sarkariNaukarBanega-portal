import os
import json
import time
import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

DB_FILE = "jobs_database.json"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

TARGET_PORTALS = [
    {"name": "SarkariResult", "url": "https://www.sarkariresult.com/"},
    {"name": "FreeJobAlert", "url": "https://www.freejobalert.com/"},
    {"name": "MySarkariNaukri", "url": "https://www.mysarkarinaukri.com/"},
    {"name": "RojgarResult", "url": "https://www.rojgarresult.com/"},
    {"name": "SarkariExam", "url": "https://www.sarkariexam.com/"},
    {"name": "Jobriya", "url": "https://www.jobriya.in/"},
    {"name": "IndGovtJobs", "url": "https://www.indgovtjobs.in/"},
    {"name": "Aglasem", "url": "https://career.aglasem.com/"}
]

UPDATE_KEYWORDS = [
    "extended", "re-open", "last date extended", "corrigendum",
    "answer key", "ans key", "response sheet", "objection",
    "cutoff", "cut off", "marks", "score card", "merit list",
    "admit card", "hall ticket", "exam city", "exam date",
    "revised", "cancellation", "result declared"
]

def load_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "tickerText": "Live Government Recruitment & Examination Updates Active 2026",
        "trendingCards": [],
        "posts": []
    }

def save_database(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def clean_text(text):
    if not text:
        return ""
    t = re.sub(r'[\r\n\t]+', ' ', text).strip()
    return re.sub(r'\s+', ' ', t)

def extract_core_exam_key(title):
    t = clean_text(title).lower()
    t = re.sub(r'[^a-z0-9 ]', '', t)
    ignore = [
        "online", "form", "apply", "recruitment", "bharti", "post", "posts", 
        "extended", "last", "date", "answer", "key", "result", "cutoff", 
        "admit", "card", "2025", "2026", "notice", "out"
    ]
    tokens = [w for w in t.split() if w not in ignore]
    return " ".join(tokens[:4])

def detect_category(title):
    t = title.lower()
    if any(k in t for k in ["result", "merit list", "score card"]):
        return "results"
    elif any(k in t for k in ["admit card", "hall ticket", "exam city"]):
        return "admit_cards"
    elif any(k in t for k in ["answer key", "ans key", "response sheet"]):
        return "answer_keys"
    elif any(k in t for k in ["syllabus", "exam pattern"]):
        return "syllabus"
    elif any(k in t for k in ["admission", "entrance"]):
        return "admissions"
    return "latest_jobs"

def generate_hybrid_overview(title, category):
    default_quick = f"Verified government recruitment notice for {clean_text(title)}."
    default_deep = f"Candidates interested in {clean_text(title)} under category '{category}' should verify all qualifications, reservation guidelines, and application schedules directly against the official notification PDF before submitting applications."

    if not GEMINI_API_KEY:
        return default_quick, default_deep

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
You are an expert government recruitment analyst.
Generate two clear sections for recruitment: '{title}' in category '{category}', separated by '---SPLIT---':
1. QUICK_OVERVIEW: A punchy, 1-2 sentence candidate-friendly summary (max 25 words).
2. DEEP_ANALYSIS: A structured 2-paragraph briefing covering key vacancy highlights, selection stages flow, and common form-filling errors to avoid.
Do not use markdown headers (# or ##) or quotation marks.
"""
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            generated = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if "---SPLIT---" in generated:
                parts = generated.split("---SPLIT---")
                return clean_text(parts[0]), clean_text(parts[1])
            return clean_text(generated[:140]), clean_text(generated)
    except Exception as e:
        print(f"Fallback to Option A: {e}")
        return default_quick, default_deep

def resolve_direct_pdf_links(target_url):
    links = {"apply": target_url, "notif_pdf": target_url, "answer_key": "", "cutoff_pdf": ""}
    if target_url.lower().endswith(".pdf"):
        links["notif_pdf"] = target_url
        return links

    try:
        req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as res:
            soup = BeautifulSoup(res.read().decode('utf-8', errors='ignore'), 'html.parser')
            for a in soup.find_all('a', href=True):
                h = a['href'].strip()
                txt = clean_text(a.get_text()).lower()
                if not h.startswith("http"):
                    h = urllib.parse.urljoin(target_url, h)
                if h.lower().endswith(".pdf") or "pdf" in txt:
                    if any(k in txt for k in ["answer", "ans key"]):
                        links["answer_key"] = h
                    elif any(k in txt for k in ["cut off", "cutoff"]):
                        links["cutoff_pdf"] = h
                    elif not links.get("pdf_set"):
                        links["notif_pdf"] = h
                        links["pdf_set"] = True
                if any(k in txt for k in ["apply online", "registration"]):
                    links["apply"] = h
    except Exception:
        pass
    return links

def scan_all_portals():
    feed = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for p in TARGET_PORTALS:
        try:
            req = urllib.request.Request(p["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=8) as res:
                soup = BeautifulSoup(res.read().decode('utf-8', errors='ignore'), 'html.parser')
                for a in soup.find_all('a', href=True):
                    title = clean_text(a.get_text())
                    href = a['href'].strip()
                    if not href or href.startswith("javascript:") or href == "#":
                        continue
                    if not href.startswith("http"):
                        href = urllib.parse.urljoin(p["url"], href)
                    triggers = ["recruitment", "bharti", "online form", "admit card", "result", "answer key", "syllabus", "vacancy", "extended"]
                    if len(title) >= 14 and any(t in title.lower() for t in triggers):
                        feed.append({"source": p["name"], "title": title, "link": href, "category": detect_category(title)})
        except Exception as e:
            print(f"Skipping {p['name']}: {e}")
    return feed

def main():
    db = load_database()
    existing_posts = db.get("posts", [])
    is_seed_run = len(existing_posts) == 0

    raw_items = scan_all_portals()
    core_map = {extract_core_exam_key(p.get("title", "")): p for p in existing_posts if extract_core_exam_key(p.get("title", ""))}
    max_id = max([p.get("id", 0) for p in existing_posts], default=0)

    added_count = 0
    updated_count = 0

    for item in raw_items:
        ck = extract_core_exam_key(item["title"])
        if not ck:
            continue

        if ck in core_map:
            ex = core_map[ck]
            diff = [kw.title() for kw in UPDATE_KEYWORDS if kw in item["title"].lower() and kw not in ex.get("title", "").lower()]
            if diff:
                tag = " / ".join(diff[:2])
                ex["title"] = f"{clean_text(item['title'])} [{tag}]"
                ex["badge"] = "UPDATED"
                ex["status"] = "pending"
                ex["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                q_text, d_text = generate_hybrid_overview(ex["title"], item["category"])
                ex["overview"] = q_text
                ex["deep_details"] = d_text
                updated_count += 1
        else:
            max_id += 1
            quick_info, deep_info = generate_hybrid_overview(item["title"], item["category"])
            link_payload = resolve_direct_pdf_links(item["link"])

            new_job = {
                "id": max_id,
                "title": clean_text(item["title"]),
                "category": item["category"],
                "badge": "HOT" if any(k in item["title"].lower() for k in ["cgl", "police", "railway", "ntpc", "ibps"]) else "NEW",
                "dept": f"Government Recruitment Authority ({item['source']})",
                "scope": "central",
                "state": "all",
                "status": "published" if is_seed_run else "pending",
                "overview": quick_info,
                "deep_details": deep_info,
                "verified_notice": True,
                "sections": {
                    "dates": True, "fee": True, "age": True, "vacancy": True,
                    "physical": True if "police" in item["title"].lower() else False,
                    "selection": True, "instructions": True, "links": True
                },
                "dates": {"start": "Refer to official notice", "end": "Closing Soon", "exam": "As per schedule"},
                "fee": {"gen_obc": "Check PDF", "sc_st": "Check PDF"},
                "age": {"min": "18 Years", "max": "Refer to advertisement", "relaxation": "As per Govt rules"},
                "vacancy": {"total": "Refer to advertisement", "eligibility": "Refer to official advertisement PDF"},
                "physical": {"male_height": "Norms applicable", "running": "As per criteria"},
                "selection": {"process": "Computer Based Test / Written Exam, Document Verification."},
                "instructions": {"details": "Verify photo specs and category certificates before applying."},
                "links": link_payload,
                "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            existing_posts.append(new_job)
            core_map[ck] = new_job
            added_count += 1
            if is_seed_run and added_count >= 40:
                break

    db["posts"] = existing_posts
    save_database(db)
    print(f"Hybrid Run Finished. Added: {added_count}, Updated: {updated_count}")

if __name__ == "__main__":
    main()

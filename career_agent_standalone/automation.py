"""Background automation core for CareerPilot AI.

Automatic applications are email-only and require an explicitly enabled policy,
a verified-open job, a verified public contact, a sufficient match score, a saved
resume, and daily rate-limit/duplicate checks. Portal form submissions are not
attempted without an official/supported connector.
"""
from __future__ import annotations
import os, re, ssl, sqlite3, time, requests, smtplib
from pathlib import Path
from datetime import datetime, timezone, date
from email.message import EmailMessage
from dotenv import load_dotenv

BASE=Path(__file__).resolve().parent
DB_PATH=BASE/"data"/"career_agent.sqlite3"
load_dotenv(BASE/".env")

SCHEMA="""
CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK(id=1), profile_text TEXT NOT NULL DEFAULT '', resume_text TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, company TEXT, location TEXT, source TEXT, url TEXT UNIQUE, description TEXT, contact_email TEXT, contact_phone TEXT, match_score INTEGER DEFAULT 0, status TEXT DEFAULT 'New', created_at TEXT NOT NULL, notes TEXT DEFAULT '', contact_verified INTEGER DEFAULT 0, contact_source_url TEXT DEFAULT '', application_method TEXT DEFAULT 'email');
CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, details TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS drafts (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER, resume_text TEXT, email_subject TEXT, email_body TEXT, recipient TEXT, created_at TEXT NOT NULL, sent_at TEXT, FOREIGN KEY(job_id) REFERENCES jobs(id));
CREATE TABLE IF NOT EXISTS automation_settings (id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER DEFAULT 0, interval_minutes INTEGER DEFAULT 360, min_match_score INTEGER DEFAULT 65, max_applications_per_day INTEGER DEFAULT 3, search_query TEXT DEFAULT 'Operations Executive OR Business Operations OR Procurement OR Supply Chain', location TEXT DEFAULT 'Hyderabad, Telangana, India', last_run_at TEXT DEFAULT '', updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, method TEXT NOT NULL, recipient TEXT DEFAULT '', status TEXT NOT NULL, reason TEXT DEFAULT '', created_at TEXT NOT NULL, sent_at TEXT DEFAULT '', UNIQUE(job_id, method), FOREIGN KEY(job_id) REFERENCES jobs(id));
"""
def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def db():
    (BASE/"data").mkdir(exist_ok=True)
    c=sqlite3.connect(DB_PATH,timeout=30); c.row_factory=sqlite3.Row; c.execute("PRAGMA journal_mode=WAL"); c.executescript(SCHEMA)
    cols={r[1] for r in c.execute("PRAGMA table_info(jobs)")}
    for name,ddl in [("contact_verified","INTEGER DEFAULT 0"),("contact_source_url","TEXT DEFAULT ''"),("application_method","TEXT DEFAULT 'email'")]:
        if name not in cols: c.execute(f"ALTER TABLE jobs ADD COLUMN {name} {ddl}")
    c.execute("INSERT OR IGNORE INTO automation_settings(id,updated_at) VALUES(1,?)",(now(),))
    default_profile = "Target roles: Operations Executive, Business Operations Coordinator, Procurement, Supply Chain, Logistics, ERP/CRM Coordination, Sales Coordination, Administration. Preferred location: Hyderabad, India. Use only verified facts from the saved resume; never invent qualifications or experience."
    c.execute("INSERT OR IGNORE INTO profile(id,profile_text,resume_text,updated_at) VALUES(1,?,?,?)",(default_profile,"",now()))
    c.commit(); return c
def log(c,event,details): c.execute("INSERT INTO activity(event,details,created_at) VALUES(?,?,?)",(event,details,now())); c.commit()
def tokens(t):
    stop={"with","from","that","this","will","have","your","you","and","the","for","are","our","job","role","work","years","year","ability","skills","experience","required","preferred","responsible","including","using","good","strong"}
    return {w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}",(t or "").lower()) if w not in stop}
def score(job,profile,resume):
    prof=tokens(profile+" "+resume); desc=tokens(" ".join(str(job.get(k) or "") for k in ("title","description","company","location")))
    if not desc:return 0
    overlap=len(prof&desc)/max(1,len(desc)); role_terms={"operations","procurement","supply","logistics","coordinator","admin","erp","crm","sales","customer","business","inventory","vendor","dispatch","export"}
    bonus=.2 if tokens(job.get("title",""))&role_terms else 0
    bonusloc=.08 if "hyderabad" in (job.get("location") or "").lower() else 0
    return max(0,min(100,round((overlap+bonus+bonusloc)*100)))
def search(query,max_results=8):
    key=os.getenv("TAVILY_API_KEY","").strip()
    if not key: raise RuntimeError("TAVILY_API_KEY is missing; background search cannot run.")
    r=requests.post("https://api.tavily.com/search",json={"api_key":key,"query":query,"search_depth":"advanced","max_results":max_results,"include_answer":False},timeout=35); r.raise_for_status()
    return r.json().get("results",[])
def send_application(to_addr,subject,body,resume_text):
    host=os.getenv("SMTP_HOST","").strip(); port=int(os.getenv("SMTP_PORT","587")); user=os.getenv("SMTP_USERNAME","").strip(); password=os.getenv("SMTP_PASSWORD","").strip(); sender=os.getenv("EMAIL_FROM","").strip() or user
    if not all([host,user,password,sender]): raise RuntimeError("SMTP is not fully configured.")
    msg=EmailMessage(); msg["From"]=sender; msg["To"]=to_addr; msg["Subject"]=subject; msg.set_content(body)
    msg.add_attachment(resume_text.encode("utf-8"),maintype="text",subtype="plain",filename="CareerPilot_Tailored_Resume.txt")
    with smtplib.SMTP(host,port,timeout=30) as server:
        server.starttls(context=ssl.create_default_context()); server.login(user,password); server.send_message(msg)
def ollama(prompt):
    base=os.getenv("OLLAMA_BASE_URL","http://localhost:11434").rstrip("/"); model=os.getenv("OLLAMA_MODEL","qwen2.5:7b")
    r=requests.post(base+"/api/generate",json={"model":model,"prompt":prompt,"stream":False},timeout=120); r.raise_for_status(); return r.json().get("response","").strip()
def tailored_resume(job,profile,resume):
    if not resume.strip(): raise RuntimeError("No resume saved in Profile & Settings.")
    prompt=f"Tailor this resume to the job. Do not invent facts, qualifications, employers, dates, metrics, tools, or experience. Keep all claims grounded in the source. Return a clean plain-text resume only.\nPROFILE:\n{profile}\nSOURCE RESUME:\n{resume}\nJOB: {job['title']} at {job['company']}\nDESCRIPTION:\n{(job.get('description') or '')[:8000]}"
    try:
        out=ollama(prompt)
        if out and len(out)>150:return out
    except Exception: pass
    return f"TARGET ROLE: {job['title']} — {job['company']}\n\nResume tailored draft based on verified source material. Review job-specific wording before use.\n\n{resume}"
def build_email(job):
    name=os.getenv("CAREER_FULL_NAME","[Your Full Name]").strip(); phone=os.getenv("CAREER_PHONE","[Your Phone Number]").strip(); email=os.getenv("CAREER_EMAIL",os.getenv("EMAIL_FROM","[Your Email Address]")).strip()
    subject=f"Application for {job['title']} — {job['company']}"
    body=(f"Dear Hiring Team,\n\nI would like to apply for the {job['title']} opportunity at {job['company']}. My background includes operations coordination and related responsibilities described in my attached resume. I would appreciate your consideration if my experience aligns with the role.\n\nPlease find my resume attached. Thank you for your time.\n\nRegards,\n{name}\n{phone}\n{email}")
    if any(x in (name,phone,email) for x in ("[Your Full Name]","[Your Phone Number]","[Your Email Address]")):
        raise RuntimeError("Set CAREER_FULL_NAME, CAREER_PHONE, and CAREER_EMAIL in .env before enabling automatic sending.")
    return subject,body
def discover_and_save(c,cfg,profile):
    query=f"{cfg['search_query']} {cfg['location']} jobs posted recently site:linkedin.com/jobs OR site:naukri.com OR site:indeed.com OR site:workindia.in OR company careers"
    results=search(query,10); added=0
    for r in results:
        url=(r.get("url") or "").strip()
        if not url: continue
        title=r.get("title") or "Job lead — verify details"; desc=r.get("content") or ""
        job={"title":title,"company":"Review listing","location":cfg['location'],"description":desc}
        ms=score(job,profile['profile_text'],profile['resume_text'])
        try:
            c.execute("INSERT INTO jobs(title,company,location,source,url,description,match_score,status,created_at,notes) VALUES(?,?,?,?,?,?,?,?,?,?)",(title,"Review listing",cfg['location'],url.split('/')[2] if '://' in url else 'Web search',url,desc,ms,"Needs verification",now(),"Discovered by background search; verify employer, vacancy status, and contact before auto-application.")); added+=1
        except sqlite3.IntegrityError: pass
    c.commit(); log(c,"autopilot_search",f"Found {len(results)} search results; added {added} new leads.")
def process_eligible(c,cfg,profile):
    if not profile['resume_text'].strip(): log(c,"autopilot_blocked","No resume is saved; no applications sent."); return 0
    day_start=datetime.now(timezone.utc).date().isoformat()
    sent_today=c.execute("SELECT COUNT(*) FROM applications WHERE status='SENT' AND sent_at >= ?",(day_start,)).fetchone()[0]
    remaining=max(0,int(cfg['max_applications_per_day'])-sent_today); sent=0
    if remaining<=0: log(c,"autopilot_cap_reached",f"Daily application cap {cfg['max_applications_per_day']} reached."); return 0
    rows=c.execute("SELECT * FROM jobs WHERE status='Verified open' AND contact_verified=1 AND COALESCE(contact_email,'')<>'' AND COALESCE(contact_source_url,'')<>'' AND match_score>=? ORDER BY match_score DESC, created_at DESC",(int(cfg['min_match_score']),)).fetchall()
    for row in rows:
        if sent>=remaining: break
        job=dict(row)
        prior=c.execute("SELECT status FROM applications WHERE job_id=? AND method='email'",(job['id'],)).fetchone()
        if prior: continue
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$",job['contact_email']):
            c.execute("INSERT OR IGNORE INTO applications(job_id,method,recipient,status,reason,created_at) VALUES(?,?,?,?,?,?)",(job['id'],'email',job['contact_email'],'BLOCKED','Invalid recipient format',now())); c.commit(); continue
        try:
            resume=tailored_resume(job,profile['profile_text'],profile['resume_text']); subject,body=build_email(job)
            # reserve idempotency record before sending; if interrupted, state remains SENDING and is never auto-retried blindly
            c.execute("INSERT INTO applications(job_id,method,recipient,status,reason,created_at) VALUES(?,?,?,?,?,?)",(job['id'],'email',job['contact_email'],'SENDING','Policy checks passed; sending email application',now())); c.commit()
            send_application(job['contact_email'],subject,body,resume)
            c.execute("UPDATE applications SET status='SENT',sent_at=?,reason=? WHERE job_id=? AND method='email'",(now(),'Email accepted by SMTP server; delivery is not guaranteed',job['id']))
            c.execute("INSERT INTO drafts(job_id,resume_text,email_subject,email_body,recipient,created_at,sent_at) VALUES(?,?,?,?,?,?,?)",(job['id'],resume,subject,body,job['contact_email'],now(),now()))
            c.execute("UPDATE jobs SET status='Applied' WHERE id=?",(job['id'],)); c.commit(); log(c,"autopilot_application_sent",f"Job #{job['id']} {job['title']} at {job['company']} -> {job['contact_email']}"); sent+=1
        except Exception as e:
            c.execute("UPDATE applications SET status='FAILED',reason=? WHERE job_id=? AND method='email' AND status='SENDING'",(str(e)[:800],job['id'])); c.commit(); log(c,"autopilot_application_failed",f"Job #{job['id']}: {e}")
    return sent
def run_once():
    c=db()
    try:
        cfg=dict(c.execute("SELECT * FROM automation_settings WHERE id=1").fetchone())
        profile=dict(c.execute("SELECT * FROM profile WHERE id=1").fetchone())
        if not cfg['enabled']:
            log(c,"autopilot_idle","Autopilot policy disabled; no work performed."); return
        try: discover_and_save(c,cfg,profile)
        except Exception as e: log(c,"autopilot_search_failed",str(e)[:800])
        sent=process_eligible(c,cfg,profile)
        c.execute("UPDATE automation_settings SET last_run_at=?,updated_at=? WHERE id=1",(now(),now())); c.commit()
        log(c,"autopilot_cycle_complete",f"Cycle complete. Applications sent: {sent}.")
    finally: c.close()
def worker_loop():
    print("CareerPilot worker started. Ctrl+C to stop.",flush=True)
    while True:
        c=db()
        try: cfg=dict(c.execute("SELECT * FROM automation_settings WHERE id=1").fetchone())
        finally: c.close()
        if cfg['enabled']:
            run_once(); wait=max(60,int(cfg['interval_minutes'])*60)
        else: wait=60
        time.sleep(wait)
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description="CareerPilot background worker")
    parser.add_argument("--once",action="store_true",help="run one cycle and exit")
    args=parser.parse_args()
    if args.once: run_once()
    else: worker_loop()

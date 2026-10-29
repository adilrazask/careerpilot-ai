import os, sys, re, json, sqlite3, smtplib, ssl, textwrap
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Top-level Vercel Serverless Function & WSGI compatibility exports
def handler(*args, **kwargs):
    if len(args) == 2 and callable(args[1]):
        environ, start_response = args
        start_response("200 OK", [("Content-type", "text/html; charset=utf-8")])
        return [b"<!DOCTYPE html><html><head><title>CareerPilot Standalone Worker</title></head><body><h1>CareerPilot Autonomous Standalone Agent</h1><p>Worker runs on host/cloud.</p></body></html>"]
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": "<!DOCTYPE html><html><head><title>CareerPilot Standalone Worker</title></head><body><h1>CareerPilot Autonomous Standalone Agent</h1><p>Worker runs on host/cloud.</p></body></html>"
    }

app = handler
application = handler

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "career_agent.sqlite3"
load_dotenv(BASE / ".env")

try:
    st.set_page_config(page_title="CareerPilot AI — Autonomous Job Search", page_icon="🧭", layout="wide")
except Exception:
    pass

DEFAULT_PROFILE = """Target roles: Operations Executive, Senior Operations Executive, Business Operations Coordinator, Operations Manager (only where experience fits), ERP/CRM Coordinator, Sales Coordinator, Procurement Executive, Supply Chain Executive, Logistics Coordinator, Admin/Office Coordinator, Customer Success Operations.
Preferred location: Hyderabad, India; open to UAE/Dubai opportunities if explicitly selected.
Experience: operations coordination in the steel/manufacturing sector; procurement and vendor management; sales enquiries and quotations; customer/client communication; payment follow-ups; inventory/Excel/Tally/CRM/ERP records; GRN/store coordination; logistics/dispatch; export documentation and shipment tracking; coordination with management, vendors, customers, and software providers.
Education and skills should be edited by the user to match the latest resume exactly.
Resume rule: never invent employers, dates, qualifications, metrics, certifications, tools, or responsibilities. Use only facts supplied in the saved profile/resume."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK(id=1), profile_text TEXT NOT NULL DEFAULT '', resume_text TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, company TEXT, location TEXT, source TEXT, url TEXT UNIQUE, description TEXT, contact_email TEXT, contact_phone TEXT, match_score INTEGER DEFAULT 0, status TEXT DEFAULT 'New', created_at TEXT NOT NULL, notes TEXT DEFAULT '', contact_verified INTEGER DEFAULT 0, contact_source_url TEXT DEFAULT '', application_method TEXT DEFAULT 'email');
CREATE TABLE IF NOT EXISTS automation_settings (id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER DEFAULT 0, interval_minutes INTEGER DEFAULT 360, min_match_score INTEGER DEFAULT 65, max_applications_per_day INTEGER DEFAULT 3, search_query TEXT DEFAULT 'Operations Executive OR Business Operations OR Procurement OR Supply Chain', location TEXT DEFAULT 'Hyderabad, Telangana, India', last_run_at TEXT DEFAULT '', updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, method TEXT NOT NULL, recipient TEXT DEFAULT '', status TEXT NOT NULL, reason TEXT DEFAULT '', created_at TEXT NOT NULL, sent_at TEXT DEFAULT '', UNIQUE(job_id, method), FOREIGN KEY(job_id) REFERENCES jobs(id));
CREATE TABLE IF NOT EXISTS drafts (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER, resume_text TEXT, email_subject TEXT, email_body TEXT, recipient TEXT, created_at TEXT NOT NULL, sent_at TEXT, FOREIGN KEY(job_id) REFERENCES jobs(id));
CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, details TEXT, created_at TEXT NOT NULL);
"""

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def conn():
    c=sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory=sqlite3.Row
    c.executescript(SCHEMA)
    # Lightweight migrations for databases created by earlier versions.
    existing = {row[1] for row in c.execute("PRAGMA table_info(jobs)").fetchall()}
    for col, ddl in [("contact_verified", "INTEGER DEFAULT 0"), ("contact_source_url", "TEXT DEFAULT ''"), ("application_method", "TEXT DEFAULT 'email'")]:
        if col not in existing:
            c.execute(f"ALTER TABLE jobs ADD COLUMN {col} {ddl}")
    c.execute("INSERT OR IGNORE INTO automation_settings(id, updated_at) VALUES(1,?)", (now(),))
    c.execute("INSERT OR IGNORE INTO profile(id, profile_text, resume_text, updated_at) VALUES(1,?,?,?)", (DEFAULT_PROFILE, "", now()))
    c.commit(); return c

def log(event, details):
    c=conn(); c.execute("INSERT INTO activity(event,details,created_at) VALUES(?,?,?)",(event,details,now())); c.commit(); c.close()

def get_profile():
    c=conn(); r=c.execute("SELECT * FROM profile WHERE id=1").fetchone(); c.close(); return dict(r)

def save_profile(profile_text, resume_text):
    c=conn(); c.execute("UPDATE profile SET profile_text=?,resume_text=?,updated_at=? WHERE id=1",(profile_text,resume_text,now())); c.commit(); c.close(); log("profile_updated","Saved target preferences and resume text")

def all_jobs():
    c=conn(); rows=c.execute("SELECT * FROM jobs ORDER BY match_score DESC, created_at DESC").fetchall(); c.close(); return [dict(x) for x in rows]

def add_job(job):
    url=(job.get("url") or "").strip()
    c=conn()
    try:
        c.execute("INSERT INTO jobs(title,company,location,source,url,description,contact_email,contact_phone,match_score,status,created_at,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(
            job.get("title","Unknown role"),job.get("company","Unknown company"),job.get("location","Not specified"),job.get("source","Manual"),url or None,job.get("description",""),job.get("contact_email",""),job.get("contact_phone",""),int(job.get("match_score",0)),job.get("status","New"),now(),job.get("notes","")))
        c.commit(); log("job_added",f"{job.get('title')} at {job.get('company')}"); return True,"Job saved"
    except sqlite3.IntegrityError: return False,"This job URL is already saved"
    finally: c.close()

def update_job(job_id, **kwargs):
    if not kwargs: return
    c=conn(); fields=", ".join(f"{k}=?" for k in kwargs); c.execute(f"UPDATE jobs SET {fields} WHERE id=?",(*kwargs.values(),job_id)); c.commit(); c.close()

def tokenise(text):
    stop={"with","from","that","this","will","have","your","you","and","the","for","are","our","job","role","work","years","year","ability","skills","experience","required","preferred","responsible","including","using","good","strong"}
    return {w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", (text or "").lower()) if w not in stop}

def score_job(job, profile_text, resume_text):
    prof=tokenise(profile_text+" "+resume_text); desc=tokenise(" ".join(str(job.get(k) or "") for k in ["title","description","company","location"]))
    if not desc: return 0
    overlap=len(prof & desc)/max(1,len(desc))
    role_terms={"operations","procurement","supply","logistics","coordinator","admin","erp","crm","sales","customer","business","inventory","vendor","dispatch","export"}
    title_terms=tokenise(job.get("title",""))
    role_bonus=0.20 if title_terms & role_terms else 0
    loc=(job.get("location") or "").lower(); loc_bonus=0.08 if "hyderabad" in loc else 0
    return max(0,min(100,round((overlap+role_bonus+loc_bonus)*100)))

def tavily_search(query, max_results=10):
    key=os.getenv("TAVILY_API_KEY","").strip()
    if not key: raise RuntimeError("TAVILY_API_KEY is not configured. Add it to .env, or use the manual job-import form.")
    resp=requests.post("https://api.tavily.com/search",json={"api_key":key,"query":query,"search_depth":"advanced","max_results":max_results,"include_answer":False},timeout=30)
    resp.raise_for_status(); data=resp.json()
    out=[]
    for r in data.get("results",[]):
        url=r.get("url",""); title=r.get("title",""); content=r.get("content","")
        # Keep search results as leads; do not imply that a listing is current/verified until checked.
        company=""
        m=re.search(r"(?:at|@| - |\|)\s*([A-Z][A-Za-z0-9& .'-]{2,50})", title)
        if m: company=m.group(1).strip(" -|")
        out.append({"title":title or "Job lead — verify details", "company":company or "Review listing", "location":"Not verified", "source":url.split('/')[2] if '://' in url else "Web search", "url":url,"description":content,"status":"Needs verification"})
    return out

def ollama_generate(prompt):
    base=os.getenv("OLLAMA_BASE_URL","http://localhost:11434").rstrip("/")
    model=os.getenv("OLLAMA_MODEL","qwen2.5:7b")
    try:
        r=requests.post(base+"/api/generate",json={"model":model,"prompt":prompt,"stream":False},timeout=120)
        r.raise_for_status(); return r.json().get("response","").strip()
    except Exception as e:
        raise RuntimeError(f"Ollama unavailable: {e}")

def tailor_resume(job, profile_text, resume_text, use_ai=True):
    if not resume_text.strip(): raise ValueError("Add your current resume text in Profile first.")
    prompt=f"""You are a truthful resume editor. Tailor the supplied resume for the job below. Do not invent facts, skills, employers, qualifications, dates, certifications, metrics, or tools. Do not claim experience that is not in the source. Preserve uncertainty instead of guessing. Return: (1) target headline, (2) professional summary, (3) reordered/edited experience bullets, (4) relevant skills, (5) keywords to consider only if truthful. Label any missing job requirement as a gap, not as a skill.

PROFILE CONTEXT:
{profile_text}

SOURCE RESUME:
{resume_text}

JOB TITLE: {job.get('title')}
COMPANY: {job.get('company')}
LOCATION: {job.get('location')}
JOB DESCRIPTION:
{job.get('description','')[:10000]}
"""
    if use_ai:
        try: return ollama_generate(prompt)
        except Exception: pass
    # Deterministic safe fallback: no fabricated claims; preserves the original resume and gives a tailored focus note.
    return f"TARGET ROLE: {job.get('title','') } — {job.get('company','')}\n\nTAILORING NOTE\nPrioritise only relevant, verified experience from your source resume. Compare the job requirements against your existing experience before adding any keyword. Do not claim missing qualifications.\n\nSOURCE RESUME (unchanged)\n{resume_text}"

def draft_email(job, profile_text, resume_text, tailored_resume):
    title=job.get('title','the role'); company=job.get('company','your company')
    subj=f"Application for {title} — Operations / Business Operations"
    # Avoid asserting facts beyond saved profile.
    body=f"Dear Hiring Team,\n\nI am reaching out to express my interest in the {title} opportunity at {company}. My background includes operations coordination, procurement and vendor coordination, sales enquiries and quotations, client communication, records/ERP coordination, and logistics/documentation. I would appreciate the opportunity to be considered if my experience matches your current requirements.\n\nI have attached my tailored resume for your review. I would be happy to share any additional details.\n\nThank you for your time.\n\nRegards,\n[Your Full Name]\n[Your Phone Number]\n[Your Email Address]"
    return subj,body

def send_email(to_addr, subject, body, attachment_text=None):
    host=os.getenv("SMTP_HOST","").strip(); port=int(os.getenv("SMTP_PORT","587")); user=os.getenv("SMTP_USERNAME","").strip(); password=os.getenv("SMTP_PASSWORD","").strip(); sender=os.getenv("EMAIL_FROM","").strip() or user
    if not all([host,user,password,sender]): raise RuntimeError("SMTP is not fully configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and EMAIL_FROM in .env.")
    msg=EmailMessage(); msg["From"]=sender; msg["To"]=to_addr; msg["Subject"]=subject; msg.set_content(body)
    if attachment_text:
        msg.add_attachment(attachment_text.encode("utf-8"),maintype="text",subtype="plain",filename="Tailored_Resume.txt")
    context=ssl.create_default_context()
    with smtplib.SMTP(host,port,timeout=30) as server:
        server.starttls(context=context); server.login(user,password); server.send_message(msg)
    return True

# Sidebar navigation
st.sidebar.title("🧭 CareerPilot AI")
st.sidebar.caption("Standalone job-search & outreach agent")
page=st.sidebar.radio("Workspace",["Dashboard","Find Jobs","Job Pipeline","Resume Tailoring","HR Outreach","Autopilot","Profile & Settings","Activity Log"])
st.sidebar.divider()
st.sidebar.caption("Autopilot is separately configured; unattended sending requires explicit policy authorisation.")
profile=get_profile(); jobs=all_jobs()

if page=="Dashboard":
    st.title("CareerPilot AI — Job Search Command Centre")
    st.write("Search roles, evaluate fit, tailor truthful resumes, discover public business contact channels, and prepare HR outreach from one workspace.")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Saved job leads",len(jobs)); c2.metric("High-fit leads",sum(1 for j in jobs if j['match_score']>=60)); c3.metric("Drafts",(lambda: (lambda c: c.execute('SELECT COUNT(*) FROM drafts').fetchone()[0])(conn()))()); c4.metric("Emails sent",(lambda: (lambda c: c.execute("SELECT COUNT(*) FROM drafts WHERE sent_at IS NOT NULL").fetchone()[0])(conn()))())
    st.subheader("Your current search profile")
    st.info("Preferred focus: Operations, Business Operations, ERP/CRM Coordination, Procurement, Supply Chain, Logistics, Sales Coordination, and Administration. Default location: Hyderabad, India.")
    st.subheader("Suggested daily workflow")
    st.markdown("1. Search and save relevant job leads.\n2. Verify each vacancy on the employer or job portal page.\n3. Review match score and requirements.\n4. Tailor the resume using only truthful experience.\n5. Find a public recruiter/company contact, where available.\n6. Review the email and explicitly confirm before sending.")
    st.warning("Background automation runs in a separate worker process. Configure it in Autopilot and keep the worker running. Portal-specific application forms are not submitted unless a supported connector exists.")

elif page=="Find Jobs":
    st.title("Find Jobs")
    p=get_profile(); a,b=st.columns([2,1])
    with a:
        query=st.text_input("Search query", "Operations Executive OR Business Operations OR Procurement OR Supply Chain")
        loc=st.text_input("Location", "Hyderabad, Telangana, India")
        portals=st.multiselect("Where to look",["LinkedIn","Naukri","Indeed","WorkIndia","Foundit","Company career pages","Other public job pages"],default=["LinkedIn","Naukri","Indeed","WorkIndia","Company career pages"])
        count=st.slider("Maximum web results",3,20,10)
    with b:
        st.markdown("**Search behaviour**")
        st.write("Uses a configured web-search API to discover public listing pages. Portal coverage varies; it does not bypass login, CAPTCHA, or access controls.")
        st.write("You must verify that the vacancy is still open before applying.")
    if st.button("🔎 Search public job pages",type="primary"):
        site_map={"LinkedIn":"site:linkedin.com/jobs","Naukri":"site:naukri.com","Indeed":"site:indeed.com","WorkIndia":"site:workindia.in","Foundit":"site:foundit.in","Company career pages":"careers jobs company official"}
        queries=[f'{site_map.get(x,x)} {query} {loc}' for x in portals] or [f'{query} {loc} jobs']
        all_results=[]; errors=[]
        for q in queries:
            try: all_results.extend(tavily_search(q,max(3,count//max(1,len(queries)))))
            except Exception as e: errors.append(str(e)); break
        seen=set(); unique=[]
        for j in all_results:
            if j.get('url') and j['url'] not in seen:
                seen.add(j['url']); j['match_score']=score_job(j,p['profile_text'],p['resume_text']); unique.append(j)
        st.session_state['search_results']=unique
        if errors: st.error(errors[0])
        if not unique and not errors: st.info("No results returned. Try a broader query or add jobs manually.")
    results=st.session_state.get('search_results',[])
    if results:
        st.success(f"Found {len(results)} public-page leads. These are unverified until you open the original page.")
        for i,j in enumerate(results):
            with st.expander(f"{j['title']} · Fit {j['match_score']}% · {j['source']}"):
                st.write(j.get('description','')[:1200]); st.write(j.get('url',''))
                st.caption("Search snippets may be stale or incomplete. Verify vacancy status and employer identity.")
                if st.button("Save lead",key=f"save_{i}"):
                    ok,msg=add_job(j); st.success(msg) if ok else st.warning(msg)
    st.divider(); st.subheader("Add a job manually")
    with st.form("manual_job"):
        t=st.text_input("Job title"); co=st.text_input("Company"); lo=st.text_input("Location", "Hyderabad"); u=st.text_input("Job URL"); d=st.text_area("Job description / requirements"); src=st.text_input("Source", "Manual")
        if st.form_submit_button("Save job"):
            j={"title":t,"company":co,"location":lo,"url":u,"description":d,"source":src,"match_score":score_job({"title":t,"company":co,"location":lo,"description":d},p['profile_text'],p['resume_text'])}
            ok,msg=add_job(j); st.success(msg) if ok else st.warning(msg)

elif page=="Job Pipeline":
    st.title("Job Pipeline")
    data=all_jobs()
    if not data: st.info("No saved job leads yet. Use Find Jobs or add one manually.")
    else:
        df=pd.DataFrame(data)
        show=[c for c in ["id","title","company","location","source","match_score","status","url","contact_email","created_at"] if c in df.columns]
        st.dataframe(df[show],use_container_width=True,hide_index=True)
        ids=[x['id'] for x in data]; jid=st.selectbox("Select job lead",ids,format_func=lambda x: next(f"#{j['id']} {j['title']} — {j['company']}" for j in data if j['id']==x))
        j=next(x for x in data if x['id']==jid)
        with st.form("update_job"):
            status=st.selectbox("Status",["New","Needs verification","Verified open","Resume tailored","Contact found","Email drafted","Email sent","Applied","Rejected","Closed"],index=max(0,["New","Needs verification","Verified open","Resume tailored","Contact found","Email drafted","Email sent","Applied","Rejected","Closed"].index(j['status']) if j['status'] in ["New","Needs verification","Verified open","Resume tailored","Contact found","Email drafted","Email sent","Applied","Rejected","Closed"] else 0))
            email=st.text_input("Public HR/recruiter email",j.get('contact_email') or "")
            contact_verified=st.checkbox("I verified this email on an official/public company source", value=bool(j.get('contact_verified',0)))
            contact_source=st.text_input("Source URL for this contact", j.get('contact_source_url') or "")
            phone=st.text_input("Public business phone (optional)",j.get('contact_phone') or "")
            notes=st.text_area("Verification notes",j.get('notes') or "")
            if st.form_submit_button("Update job"):
                update_job(jid,status=status,contact_email=email,contact_verified=int(contact_verified),contact_source_url=contact_source,contact_phone=phone,notes=notes); st.success("Updated")
        if j.get('url'): st.markdown(f"[Open original listing]({j['url']})")

elif page=="Resume Tailoring":
    st.title("Truthful Resume Tailoring")
    data=all_jobs()
    if not data: st.info("Save a job first.")
    else:
        jid=st.selectbox("Choose job",[j['id'] for j in data],format_func=lambda x: next(f"{j['title']} — {j['company']} (fit {j['match_score']}%)" for j in data if j['id']==x))
        j=next(x for x in data if x['id']==jid)
        st.write("**Job description**"); st.write((j.get('description') or "No description saved — open the source listing and add the requirements.")[:4000])
        use_ai=st.checkbox("Use local Ollama model if available",value=True)
        if st.button("Generate tailored resume draft",type="primary"):
            try:
                tailored=tailor_resume(j,profile['profile_text'],profile['resume_text'],use_ai)
                c=conn(); c.execute("INSERT INTO drafts(job_id,resume_text,email_subject,email_body,recipient,created_at) VALUES(?,?,?,?,?,?)",(jid,tailored,"","","",now())); c.commit(); c.close()
                st.session_state['tailored_resume']=tailored; st.session_state['tailored_job_id']=jid; st.success("Draft generated and saved. Review every claim before using it.")
            except Exception as e: st.error(str(e))
        if st.session_state.get('tailored_job_id')==jid:
            st.text_area("Tailored resume draft",st.session_state['tailored_resume'],height=450)
            st.download_button("Download tailored resume text",st.session_state['tailored_resume'],file_name=f"resume_job_{jid}.txt",mime="text/plain")

elif page=="HR Outreach":
    st.title("Recruiter / HR Outreach")
    st.write("Find and verify publicly listed business contact channels, draft a professional message, and send only after reviewing the recipient and content.")
    data=all_jobs()
    if not data: st.info("Save a job first.")
    else:
        jid=st.selectbox("Job",[j['id'] for j in data],format_func=lambda x: next(f"{j['title']} — {j['company']}" for j in data if j['id']==x))
        j=next(x for x in data if x['id']==jid)
        st.markdown(f"**Company:** {j['company']}  \n**Role:** {j['title']}  \n**Source:** {j.get('url') or 'Not provided'}")
        st.caption("Contact discovery must use public company/recruiter information. Do not guess email addresses or collect private personal contact details.")
        if st.button("Search public HR/company contact pages"):
            q=f'official careers contact recruiter HR email {j["company"]} {j.get("location","")}'
            try:
                found=tavily_search(q,8); st.session_state['contacts_'+str(jid)]=found
            except Exception as e: st.error(str(e))
        found=st.session_state.get('contacts_'+str(jid),[])
        for x in found:
            st.markdown(f"**{x.get('title','Contact page')}**  \n{x.get('url','')}  \n{x.get('description','')[:350]}")
        if found: st.info("Search results are leads, not verified contact details. Open the official page and confirm the address before saving it.")
        contact=st.text_input("Verified HR / recruitment email",j.get('contact_email') or "")
        if contact and not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$",contact): st.warning("Email format does not look valid.")
        if st.button("Generate outreach email"):
            subj,body=draft_email(j,profile['profile_text'],profile['resume_text'],"")
            st.session_state['email_subj']=subj; st.session_state['email_body']=body; st.session_state['email_job_id']=jid; st.session_state['email_recipient']=contact
        if st.session_state.get('email_job_id')==jid:
            recipient=st.text_input("Recipient",st.session_state.get('email_recipient',''),key='recipient_edit')
            subject=st.text_input("Subject",st.session_state.get('email_subj',''),key='subject_edit')
            body=st.text_area("Email body",st.session_state.get('email_body',''),height=260,key='body_edit')
            st.caption("Replace the signature placeholders. Attachments are sent as plain-text resume drafts in this starter release; inspect the file before sending.")
            confirm=st.checkbox("I verified this recipient, reviewed the message, and want to send this email now.")
            if st.button("Send email",type="primary",disabled=not confirm):
                try:
                    resume=st.session_state.get('tailored_resume','')
                    send_email(recipient,subject,body,resume or None)
                    c=conn(); c.execute("INSERT INTO drafts(job_id,resume_text,email_subject,email_body,recipient,created_at,sent_at) VALUES(?,?,?,?,?,?,?)",(jid,resume,subject,body,recipient,now(),now())); c.commit(); c.close()
                    update_job(jid,status="Email sent",contact_email=recipient); log("email_sent",f"Job #{jid}; recipient {recipient}"); st.success("Email sent. Check your Sent folder and delivery status.")
                except Exception as e: st.error(str(e))

elif page=="Autopilot":
    st.title("Autopilot — Scheduled Search & Automatic Email Applications")
    st.warning("Autopilot can send applications without per-job review only after you explicitly enable it. It sends email applications only to jobs marked Verified open with a publicly verified contact address. It does not bypass job-portal logins, CAPTCHAs, or site restrictions.")
    c=conn(); cfg=c.execute("SELECT * FROM automation_settings WHERE id=1").fetchone(); c.close(); cfg=dict(cfg)
    st.subheader("Automation policy")
    with st.form("autopilot_policy"):
        enabled=st.checkbox("Enable unattended automatic email applications", value=bool(cfg['enabled']))
        interval=st.select_slider("Search interval (minutes)", options=[60,120,180,360,720,1440], value=int(cfg['interval_minutes']) if int(cfg['interval_minutes']) in [60,120,180,360,720,1440] else 360)
        min_score=st.slider("Minimum job-match score", 0, 100, int(cfg['min_match_score']))
        max_day=st.slider("Maximum applications per day", 1, 10, int(cfg['max_applications_per_day']))
        query=st.text_input("Search query", cfg['search_query'])
        location=st.text_input("Preferred location", cfg['location'])
        acknowledge=st.checkbox("I authorise this agent to send truthful application emails automatically under these limits, without asking me for each application.")
        save=st.form_submit_button("Save autopilot policy")
        if save:
            if enabled and not acknowledge:
                st.error("Confirm the explicit unattended-email authorisation before enabling autopilot.")
            else:
                c=conn(); c.execute("UPDATE automation_settings SET enabled=?, interval_minutes=?, min_match_score=?, max_applications_per_day=?, search_query=?, location=?, updated_at=? WHERE id=1",(int(enabled),int(interval),int(min_score),int(max_day),query,location,now())); c.commit(); c.close()
                log("autopilot_policy_saved",f"enabled={enabled}; interval={interval}; min_score={min_score}; daily_cap={max_day}")
                st.success("Policy saved. Start the background worker using the README instructions.")
    st.subheader("Eligibility rules")
    st.markdown("""- The job must be saved and marked **Verified open**.
- The contact email must be marked verified and have a source URL.
- The match score must meet your threshold.
- A truthful resume must be saved.
- The daily cap and duplicate-application checks must pass.
- The worker records every send attempt.
- Search snippets alone never trigger an application.""")
    st.subheader("Application history")
    c=conn(); rows=c.execute("SELECT a.id,a.job_id,j.title,j.company,a.method,a.recipient,a.status,a.reason,a.created_at,a.sent_at FROM applications a JOIN jobs j ON j.id=a.job_id ORDER BY a.id DESC LIMIT 100").fetchall(); c.close()
    if rows: st.dataframe(pd.DataFrame([dict(r) for r in rows]),use_container_width=True,hide_index=True)
    else: st.info("No automated applications recorded yet.")
    st.subheader("Worker health")
    st.write("Worker last run:", cfg.get('last_run_at') or "Not run yet")
    st.code("python worker.py", language="bash")
    st.caption("The worker must remain running on your Mac or an always-on computer/VPS. For reliable long-running operation, use a dedicated machine or process supervisor.")

elif page=="Profile & Settings":
    st.title("Profile & Settings")
    p=get_profile()
    st.warning("Keep the profile and resume truthful. This agent uses these details to score vacancies and tailor resumes.")
    with st.form("profile"):
        pt=st.text_area("Target roles, location, experience and constraints",p['profile_text'],height=220)
        rt=st.text_area("Paste your latest resume text",p['resume_text'],height=360,placeholder="Paste the latest resume here. Do not include passwords or sensitive identity numbers.")
        if st.form_submit_button("Save profile"):
            save_profile(pt,rt); st.success("Profile saved")
    st.subheader("Integration status")
    st.write("Tavily search API:","Configured" if os.getenv('TAVILY_API_KEY') else "Not configured")
    st.write("Ollama:",f"{os.getenv('OLLAMA_BASE_URL','http://localhost:11434')} / {os.getenv('OLLAMA_MODEL','qwen2.5:7b')} (optional)")
    st.write("SMTP:","Configured" if all(os.getenv(k) for k in ['SMTP_HOST','SMTP_USERNAME','SMTP_PASSWORD','EMAIL_FROM']) else "Not configured")
    st.code("cp .env.example .env\n# Edit .env and add your own keys locally; never share the file.")
    st.info("Portal-specific automation should use official APIs or supported integrations. This starter uses public web-search results and manual verification; it does not bypass login, CAPTCHA, or portal access controls.")

elif page=="Activity Log":
    st.title("Activity Log")
    c=conn(); rows=c.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 300").fetchall(); c.close()
    if rows: st.dataframe(pd.DataFrame([dict(x) for x in rows]),use_container_width=True,hide_index=True)
    else: st.info("No activity yet.")

st.sidebar.divider()
st.sidebar.caption("CareerPilot AI starter · local-first · review before sending")

"""
SkillMatch — Flask Backend v2
Features:
  1. WhatsApp/Email Forward -> Auto-List (LLM extraction)
  2. PDF Resume Upload -> Auto skill extraction (India Runs keyword logic)
  3. Application Draft Generator (LLM)
  4. Admin Dashboard analytics
  5. Real apply URLs for all opportunities
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, sqlite3, uuid, re, io
from datetime import datetime, date, timedelta
import requests as http_requests

# PDF parsing
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

app = Flask(__name__, static_folder='.')
CORS(app)

BASE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(BASE, 'skillmatch.db')

# API Keys — Groq (Primary LLM) & Gemini (Secondary)
GROQ_KEY = os.environ.get('GROQ_API_KEY', '')
if not GROQ_KEY and os.path.exists(os.path.join(BASE, '.env')):
    try:
        with open(os.path.join(BASE, '.env'), 'r') as f:
            for line in f:
                if line.startswith('GROQ_API_KEY='):
                    GROQ_KEY = line.split('=', 1)[1].strip()
    except Exception:
        pass
GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')

def call_groq(messages, model='qwen/qwen3.8-27b', temperature=0.3, max_tokens=1024):
    """Call Groq Cloud API for fast inference (qwen/qwen3.8-27b with gpt-oss-20b fallback)."""
    if not GROQ_KEY:
        return None
    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {GROQ_KEY}',
        'Content-Type': 'application/json',
        'User-Agent': 'SkillMatch/2.0'
    }
    for m in [model, 'openai/gpt-oss-20b']:
        payload = {
            'model': m,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        try:
            r = http_requests.post(url, headers=headers, json=payload, timeout=12)
            if r.status_code == 200:
                data = r.json()
                return data['choices'][0]['message']['content'].strip()
        except Exception:
            continue
    return None


# ══════════════════════════════════════════════
# SKILL KEYWORD BANK — adapted from India Runs BM25_KEYWORDS + main.py
# Used for resume parsing (Stage 3 of India Runs pipeline applied to student PDFs)
# ══════════════════════════════════════════════
SKILL_KEYWORDS = [
    # Programming languages
    "python","javascript","java","c++","c#","typescript","go","golang","rust","kotlin",
    "swift","ruby","php","scala","r","matlab","dart","lua","perl","haskell","julia",
    # Web
    "react","vue","angular","nextjs","nuxtjs","svelte","html","css","tailwind",
    "node.js","nodejs","express","fastapi","django","flask","spring","laravel",
    # Data / ML (from India Runs keyword bank)
    "machine learning","deep learning","tensorflow","pytorch","keras","sklearn",
    "scikit-learn","nlp","natural language processing","computer vision","opencv",
    "transformers","bert","llm","gpt","generative ai","neural network",
    "embedding","embeddings","vector database","faiss","pinecone","weaviate",
    "bm25","semantic search","information retrieval","ranking","recommendation",
    "xgboost","lightgbm","random forest","regression","classification","clustering",
    "pandas","numpy","matplotlib","seaborn","plotly","jupyter",
    # Stats / Math
    "statistics","linear algebra","calculus","probability","mathematics",
    # Databases
    "sql","mysql","postgresql","sqlite","mongodb","redis","elasticsearch",
    "firebase","cassandra","dynamodb","oracle",
    # Cloud / DevOps
    "aws","azure","gcp","docker","kubernetes","linux","git","github","ci/cd",
    "terraform","ansible","jenkins","gitlab",
    # Hardware / Embedded
    "iot","arduino","raspberry pi","embedded systems","verilog","signal processing",
    # Other CS
    "data structures","algorithms","system design","oop","operating systems",
    "computer networks","cybersecurity","blockchain","web3","solidity",
    "open source","api","rest","graphql","microservices","agile","scrum",
    # Soft skills
    "leadership","communication","team work","public speaking","community building",
    "event management","problem solving","critical thinking","research",
    # Domains
    "finance","fintech","ui/ux","figma","product management","game development",
    "augmented reality","virtual reality","robotics","aerospace","physics",
    "data science","data analysis","business intelligence","cloud computing",
    "mobile development","android","ios","flutter","react native",
]

# Clean display names
DISPLAY_MAP = {
    "c++":"C++","c#":"C#","nextjs":"Next.js","nuxtjs":"Nuxt.js","nodejs":"Node.js",
    "node.js":"Node.js","nlp":"NLP","gpt":"GPT","llm":"LLMs","iot":"IoT",
    "ui/ux":"UI/UX","aws":"AWS","gcp":"GCP","sql":"SQL","html":"HTML/CSS",
    "css":"HTML/CSS","oop":"OOP","ci/cd":"CI/CD","api":"APIs","rest":"REST APIs",
    "bm25":"BM25","bert":"BERT","sklearn":"Scikit-learn","scikit-learn":"Scikit-learn",
    "machine learning":"Machine Learning","deep learning":"Deep Learning",
    "tensorflow":"TensorFlow","pytorch":"PyTorch","data structures":"Data Structures",
    "algorithms":"Algorithms","system design":"System Design",
    "computer vision":"Computer Vision","natural language processing":"NLP",
    "open source":"Open Source","data science":"Data Science",
    "web3":"Web3/Blockchain","problem solving":"Problem Solving",
    "signal processing":"Signal Processing","embedded systems":"Embedded Systems",
}

def normalize_skill(raw):
    r = raw.strip().lower()
    return DISPLAY_MAP.get(r, raw.strip().title())


# ══════════════════════════════════════════════
# OPPORTUNITIES — real data with real apply URLs
# ══════════════════════════════════════════════
def days_from_now(n):
    return (date.today() + timedelta(days=n)).isoformat()

OPPORTUNITIES = [
    {"id":1,"title":"Google Summer of Code 2025","org":"Google","orgInitials":"G","orgColor":"#4285f4","type":"Open Source","typeKey":"opensource","description":"Contribute to open source projects under Google's mentorship for 3 months. Get paid to code and build your portfolio.","longDescription":"GSoC is a global program where students work with open source organizations on real projects under mentorship. Past orgs include NumPy, OpenCV, Linux, Python Foundation.","requiredSkills":["Python","Git","Algorithms"],"niceToHaveSkills":["JavaScript","C++","Machine Learning","Open Source"],"eligibleYears":[1,2,3,4],"eligibleBranches":["All"],"minCGPA":6.0,"stipend":"₹1,20,000","deadline":days_from_now(5),"duration":"3 months","mode":"Remote","location":"Remote (Global)","tags":["coding","mentorship","open-source","paid"],"difficulty":"Intermediate","applicants":12400,"featured":True,"applyUrl":"https://summerofcode.withgoogle.com/"},
    {"id":2,"title":"Microsoft Explore Internship","org":"Microsoft","orgInitials":"MS","orgColor":"#00a4ef","type":"Internship","typeKey":"internship","description":"12-week summer internship at Microsoft. Work on Azure, Teams, Xbox or any product team with full mentorship.","longDescription":"The Explore Internship pairs pre-final year students with Microsoft product teams. You'll ship real features and get access to Microsoft's network and resources.","requiredSkills":["C++","Data Structures","Problem Solving"],"niceToHaveSkills":["Python","Cloud","System Design","Java"],"eligibleYears":[2,3],"eligibleBranches":["CSE","IT","ECE"],"minCGPA":7.5,"stipend":"₹1,60,000/month","deadline":days_from_now(12),"duration":"12 weeks","mode":"Hybrid","location":"Hyderabad / Bangalore","tags":["internship","product","premium","paid"],"difficulty":"Hard","applicants":45000,"featured":True,"applyUrl":"https://careers.microsoft.com/v2/global/en/students"},
    {"id":3,"title":"Smart India Hackathon 2025","org":"Ministry of Education","orgInitials":"SIH","orgColor":"#ff6b35","type":"Hackathon","typeKey":"hackathon","description":"India's biggest hackathon — 36-hour sprint solving real government challenges. ₹1L prize pool. Open to all engineering students.","longDescription":"SIH is a nationwide initiative where students solve real problems from government ministries. Your solution can actually get implemented. One of the highest-prestige hackathons in India.","requiredSkills":["Problem Solving","Team Work"],"niceToHaveSkills":["Web Development","Machine Learning","IoT","Blockchain","Python"],"eligibleYears":[1,2,3,4],"eligibleBranches":["All"],"minCGPA":0,"stipend":"₹1,00,000 prize","deadline":days_from_now(2),"duration":"36 hours","mode":"Offline","location":"Pan India","tags":["hackathon","government","prize","team","national"],"difficulty":"Beginner","applicants":5200,"featured":True,"applyUrl":"https://www.sih.gov.in/sih2025"},
    {"id":4,"title":"Adobe GenAI Hackathon","org":"Adobe","orgInitials":"Ad","orgColor":"#e1251b","type":"Hackathon","typeKey":"hackathon","description":"Build creative AI tools using Adobe Firefly & Express APIs. Focus on generative AI for design and video workflows.","longDescription":"Use Adobe's cutting-edge generative AI APIs to build tools that augment human creativity. Winners get internship fast-tracks and ₹75K prize.","requiredSkills":["Python","Machine Learning","APIs"],"niceToHaveSkills":["Computer Vision","NLP","React","UI/UX","JavaScript"],"eligibleYears":[2,3,4],"eligibleBranches":["CSE","IT","Design"],"minCGPA":6.5,"stipend":"₹75,000 prize","deadline":days_from_now(8),"duration":"48 hours","mode":"Online","location":"Remote","tags":["hackathon","AI","creative","prize","generative"],"difficulty":"Intermediate","applicants":3200,"featured":False,"applyUrl":"https://unstop.com/hackathons"},
    {"id":5,"title":"Goldman Sachs Engineering Campus Hire","org":"Goldman Sachs","orgInitials":"GS","orgColor":"#6699cc","type":"Internship","typeKey":"internship","description":"10-week internship in GS Technology. Work on trading platforms and risk management systems at global scale.","longDescription":"Goldman Sachs Technology internships give you front-row access to building systems that power billions in daily transactions.","requiredSkills":["Java","Data Structures","Algorithms","Problem Solving"],"niceToHaveSkills":["Python","SQL","System Design","Finance","C++"],"eligibleYears":[3],"eligibleBranches":["CSE","IT","ECE","Mathematics"],"minCGPA":8.0,"stipend":"₹2,00,000/month","deadline":days_from_now(20),"duration":"10 weeks","mode":"In-Office","location":"Bangalore","tags":["internship","finance","premium","paid","quant"],"difficulty":"Hard","applicants":28000,"featured":False,"applyUrl":"https://www.goldmansachs.com/careers/students/programs/india/summer-analyst-program.html"},
    {"id":6,"title":"Flipkart Grid 6.0","org":"Flipkart","orgInitials":"FK","orgColor":"#F9A825","type":"Hackathon","typeKey":"hackathon","description":"Flipkart's flagship engineering challenge. Solve e-commerce problems at massive scale. PPO for winners.","longDescription":"GRID is one of India's most prestigious competitions. Compete with the best minds to solve problems used by 500M+ customers. Winners get Pre-Placement Offers.","requiredSkills":["Problem Solving","Algorithms","Data Structures"],"niceToHaveSkills":["Machine Learning","System Design","SQL","Python","Java"],"eligibleYears":[2,3,4],"eligibleBranches":["CSE","IT","ECE"],"minCGPA":7.0,"stipend":"₹50,000 + PPO","deadline":days_from_now(15),"duration":"Multiple rounds","mode":"Online + Offline Final","location":"Bangalore (Final)","tags":["hackathon","e-commerce","PPO","prize","scale"],"difficulty":"Hard","applicants":150000,"featured":True,"applyUrl":"https://unstop.com/competitions/flipkart-grid-60-flipkart-1563672"},
    {"id":7,"title":"MLH Fellowship — Open Source Track","org":"Major League Hacking","orgInitials":"MLH","orgColor":"#f0a500","type":"Fellowship","typeKey":"fellowship","description":"12-week remote paid fellowship working with top open source orgs like Meta, GitHub, and Brave.","longDescription":"The MLH Fellowship is an alternative to the traditional internship. Contribute to real open source projects used by millions of developers worldwide.","requiredSkills":["Git","Open Source","Problem Solving"],"niceToHaveSkills":["JavaScript","Python","React","Node.js","TypeScript"],"eligibleYears":[1,2,3,4],"eligibleBranches":["All"],"minCGPA":0,"stipend":"$5,000 USD","deadline":days_from_now(30),"duration":"12 weeks","mode":"Remote","location":"Remote (Global)","tags":["fellowship","open-source","paid","mentorship","international"],"difficulty":"Intermediate","applicants":8700,"featured":False,"applyUrl":"https://fellowship.mlh.io/"},
    {"id":8,"title":"ISRO Young Scientist Programme","org":"ISRO","orgInitials":"ISRO","orgColor":"#ff8c42","type":"Research","typeKey":"research","description":"Residential programme at ISRO centers — work alongside real space scientists on satellite & launch vehicle projects.","longDescription":"YUVIKA is ISRO's flagship student programme. Live and work at ISRO facilities for 2 weeks, learning directly from scientists who built Chandrayaan.","requiredSkills":["Physics","Mathematics","Problem Solving"],"niceToHaveSkills":["Python","MATLAB","C","Signal Processing","Embedded Systems"],"eligibleYears":[1,2],"eligibleBranches":["CSE","ECE","Mechanical","Aerospace","Physics"],"minCGPA":8.5,"stipend":"Fully Funded","deadline":days_from_now(45),"duration":"2 weeks","mode":"Offline","location":"Bangalore / Thiruvananthapuram","tags":["research","space","residential","funded","science"],"difficulty":"Hard","applicants":50000,"featured":False,"applyUrl":"https://www.isro.gov.in/yuvika-2025"},
    {"id":9,"title":"Walmart Global Tech Hackathon","org":"Walmart","orgInitials":"W","orgColor":"#0071ce","type":"Hackathon","typeKey":"hackathon","description":"Build innovative retail tech solutions. Top teams get fast-tracked for full-time Walmart interviews.","longDescription":"Walmart Global Tech Hackathon challenges you to reimagine retail at the scale of 100M+ customers and petabytes of data.","requiredSkills":["Web Development","Problem Solving"],"niceToHaveSkills":["React","Node.js","Python","Machine Learning","SQL","Cloud"],"eligibleYears":[2,3,4],"eligibleBranches":["CSE","IT"],"minCGPA":7.0,"stipend":"₹1,50,000 prize","deadline":days_from_now(7),"duration":"24 hours","mode":"Hybrid","location":"Bangalore + Remote","tags":["hackathon","retail","AI","prize","scale"],"difficulty":"Intermediate","applicants":25000,"featured":False,"applyUrl":"https://unstop.com/hackathons/walmart"},
    {"id":10,"title":"Amazon ML Summer School","org":"Amazon","orgInitials":"Az","orgColor":"#ff9900","type":"Research","typeKey":"research","description":"6-day virtual school on ML taught by Amazon scientists — supervised learning, NLP, computer vision, RL. Free with certificate.","longDescription":"Sessions taught by scientists working on Alexa, Prime, and AWS. Includes hands-on labs and Q&A with Amazon ML researchers.","requiredSkills":["Python","Mathematics","Statistics"],"niceToHaveSkills":["Machine Learning","Deep Learning","TensorFlow","PyTorch","Linear Algebra"],"eligibleYears":[2,3,4],"eligibleBranches":["CSE","IT","Mathematics","Statistics"],"minCGPA":7.0,"stipend":"Free + Certificate","deadline":days_from_now(25),"duration":"6 days","mode":"Online","location":"Remote","tags":["learning","ML","Amazon","certificate","AI"],"difficulty":"Intermediate","applicants":95000,"featured":False,"applyUrl":"https://amazonmlsummerschool.splashthat.com/"},
    {"id":11,"title":"HackWithInfy — National Hackathon","org":"Infosys","orgInitials":"In","orgColor":"#007cc3","type":"Hackathon","typeKey":"hackathon","description":"National hackathon by Infosys. Winners get PPO + ₹2L prize. One of the rare hackathons that converts directly to job offers.","longDescription":"HackWithInfy is Infosys's flagship national hackathon open to all engineering students. The PPO conversion makes this uniquely valuable.","requiredSkills":["Problem Solving","Any Programming Language"],"niceToHaveSkills":["Java","Python","Cloud","AI/ML","JavaScript"],"eligibleYears":[3,4],"eligibleBranches":["CSE","IT","ECE","Mechanical","Civil"],"minCGPA":6.0,"stipend":"₹2,00,000 + PPO","deadline":days_from_now(18),"duration":"48 hours","mode":"Online","location":"Remote","tags":["hackathon","PPO","prize","national","placement"],"difficulty":"Beginner","applicants":75000,"featured":False,"applyUrl":"https://www.hackerearth.com/challenges/hackathon/hackwithinfy/"},
    {"id":12,"title":"GitHub Campus Expert Program","org":"GitHub","orgInitials":"GH","orgColor":"#2dba4e","type":"Fellowship","typeKey":"fellowship","description":"Become a GitHub Campus Expert — build your college's developer community with GitHub's backing and global network.","longDescription":"Campus Experts lead tech communities at their colleges. GitHub provides training, speaker opportunities, event funding, and a global alumni network.","requiredSkills":["Git","Communication","Leadership"],"niceToHaveSkills":["Public Speaking","Community Building","Open Source","Event Management"],"eligibleYears":[1,2,3,4],"eligibleBranches":["All"],"minCGPA":0,"stipend":"GitHub Credits + Benefits","deadline":days_from_now(60),"duration":"Ongoing","mode":"Remote","location":"Your Campus","tags":["community","leadership","github","open-source","network"],"difficulty":"Beginner","applicants":2300,"featured":False,"applyUrl":"https://education.github.com/experts"},
]

# Runtime-added opportunities (via ingest)
RUNTIME_OPPS = []

def all_opps():
    return OPPORTUNITIES + RUNTIME_OPPS


# ══════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY, name TEXT, email TEXT, year INTEGER,
            branch TEXT, cgpa REAL, college TEXT,
            skills TEXT, interests TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT, opp_id INTEGER, status TEXT,
            applied_at TEXT, updated_at TEXT, notes TEXT
        );
        CREATE TABLE IF NOT EXISTS bookmarks (
            profile_id TEXT, opp_id INTEGER, saved_at TEXT,
            PRIMARY KEY (profile_id, opp_id)
        );
        CREATE TABLE IF NOT EXISTS ingested_opps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT, ingested_at TEXT, ingested_by TEXT
        );
        CREATE TABLE IF NOT EXISTS opp_views (
            profile_id TEXT, opp_id INTEGER, viewed_at TEXT
        );
    ''')
    db.commit(); db.close()

init_db()


# ══════════════════════════════════════════════
# MATCHING ENGINE — Directly imported from India Runs engine.py
# ══════════════════════════════════════════════
from engine import calculate_match as match_score, extract_skills_from_text, extract_metadata_from_text as extract_resume_metadata, days_left


# ══════════════════════════════════════════════

# GEMINI HELPER
# ══════════════════════════════════════════════
def call_gemini(prompt, temperature=0.3):
    """Call Gemini 1.5 Flash via REST. Returns text or None."""
    key = GEMINI_KEY
    if not key:
        return None
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}'
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': temperature, 'maxOutputTokens': 1024}
    }
    try:
        r = http_requests.post(url, json=payload, timeout=20)
        data = r.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return None



# ══════════════════════════════════════════════
# WHATSAPP/EMAIL INGESTION — LLM extraction
# ══════════════════════════════════════════════
def parse_opportunity_with_llm(raw_text):
    """Extract structured opportunity from raw WhatsApp/email text via Groq (fallback to Gemini, then regex)."""
    prompt = f"""You are parsing a forwarded WhatsApp/email opportunity message.
Extract all fields and return ONLY a valid JSON object with these exact keys:

{{
  "title": "opportunity title",
  "org": "organization name",
  "typeKey": "one of: hackathon, internship, fellowship, research, opensource",
  "type": "display name e.g. Hackathon, Internship",
  "description": "1-2 sentence description",
  "requiredSkills": ["skill1", "skill2"],
  "niceToHaveSkills": ["skill1"],
  "eligibleYears": [1, 2, 3, 4],
  "eligibleBranches": ["All"] or ["CSE", "IT"],
  "minCGPA": 0.0,
  "stipend": "prize/stipend amount",
  "deadline": "YYYY-MM-DD or empty string",
  "duration": "duration string",
  "mode": "Online or Offline or Hybrid",
  "location": "location",
  "tags": ["tag1", "tag2"],
  "difficulty": "Beginner or Intermediate or Hard",
  "applyUrl": "URL if found else empty string"
}}

RAW TEXT:
{raw_text}

Return ONLY the raw JSON object. Do not include markdown codeblocks or conversational text."""

    # 1. Try Groq Cloud first
    llm_out = call_groq([
        {'role': 'system', 'content': 'You are a precise JSON extractor. Output valid JSON only, no markdown, no comments.'},
        {'role': 'user', 'content': prompt}
    ], temperature=0.1)

    # 2. Try Gemini fallback if Groq didn't succeed
    if not llm_out:
        llm_out = call_gemini(prompt)

    if llm_out:
        clean = re.sub(r'^```(?:json)?\s*', '', llm_out.strip(), flags=re.IGNORECASE)
        clean = re.sub(r'\s*```$', '', clean)
        try:
            data = json.loads(clean)
            # Sanitize eligibleYears to list of ints
            if 'eligibleYears' in data and isinstance(data['eligibleYears'], list):
                sanitized_years = []
                for y in data['eligibleYears']:
                    if isinstance(y, int): sanitized_years.append(y)
                    elif isinstance(y, str):
                        m = re.search(r'\d+', y)
                        if m: sanitized_years.append(int(m.group()))
                data['eligibleYears'] = sanitized_years or [1,2,3,4]
            if not data.get('typeKey'): data['typeKey'] = 'hackathon'
            if not data.get('type'): data['type'] = data['typeKey'].capitalize()
            return data, True
        except Exception:
            pass

    # Fallback: regex parsing if no API key or parse fails
    return parse_opportunity_regex(raw_text), False

def parse_opportunity_regex(text):
    """Regex-based fallback parser for opportunity extraction."""
    text_l = text.lower()

    # Type detection
    type_map = {
        'hackathon': ('hackathon', 'Hackathon'),
        'intern': ('internship', 'Internship'),
        'fellowship': ('fellowship', 'Fellowship'),
        'research': ('research', 'Research'),
        'open source': ('opensource', 'Open Source'),
    }
    typeKey, typeLabel = 'hackathon', 'Hackathon'
    for kw, (tk, tl) in type_map.items():
        if kw in text_l:
            typeKey, typeLabel = tk, tl; break

    # Extract skills from text
    skills = extract_skills_from_text(text)[:6]

    # Deadline
    deadline = ''
    date_pat = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', text)
    if date_pat:
        d, m, y = date_pat.groups()
        y = int(y); y = 2000+y if y < 100 else y
        try:
            deadline = date(y, int(m), int(d)).isoformat()
        except:
            deadline = days_from_now(14)
    else:
        # Look for month names
        month_pat = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{1,2})', text_l)
        if month_pat:
            deadline = days_from_now(14)
        else:
            deadline = days_from_now(21)

    # Stipend
    stipend = 'TBD'
    prize_pat = re.search(r'(?:prize|stipend|reward|₹|rs\.?|inr)\s*[\s:]*([\d,]+(?:k|l|lakh)?)', text_l)
    if prize_pat:
        stipend = '₹' + prize_pat.group(1).upper()

    # URL
    url_pat = re.search(r'https?://\S+', text)
    apply_url = url_pat.group(0) if url_pat else ''

    # Title — first meaningful line
    lines = [l.strip() for l in text.strip().split('\n') if l.strip() and len(l.strip()) > 5]
    title = lines[0][:80] if lines else 'New Opportunity'

    # Org — second line or guess
    org = lines[1][:50] if len(lines) > 1 else 'Unknown'

    return {
        'title': title, 'org': org,
        'typeKey': typeKey, 'type': typeLabel,
        'description': ' '.join(lines[:2])[:200],
        'requiredSkills': skills[:3], 'niceToHaveSkills': skills[3:],
        'eligibleYears': [1,2,3,4], 'eligibleBranches': ['All'],
        'minCGPA': 0, 'stipend': stipend, 'deadline': deadline,
        'duration': 'TBD', 'mode': 'Online', 'location': 'Remote',
        'tags': [typeKey, 'new'], 'difficulty': 'Intermediate',
        'applyUrl': apply_url
    }


# ══════════════════════════════════════════════
# APPLICATION DRAFT GENERATOR
# ══════════════════════════════════════════════
def generate_draft(student, opp):
    m = match_score(student, opp)

    # Try LLM first
    prompt = f"""Write a short, compelling application/interest note for a student applying to an opportunity.
Keep it to 3-4 sentences max. Sound genuine, not robotic.

Student Profile:
- Name: {student.get('name')}
- Year: {student.get('year')}  Branch: {student.get('branch')}  College: {student.get('college','')}
- Skills: {', '.join((student.get('skills') or [])[:8])}
- Interests: {', '.join((student.get('interests') or [])[:4])}
- CGPA: {student.get('cgpa','')}

Opportunity:
- Title: {opp['title']} at {opp['org']}
- Type: {opp['type']}
- Required Skills: {', '.join(opp.get('requiredSkills',[]))}
- Match Score: {m['percentage']}% ({m['matchLabel']})
- Matched skills they have: {', '.join(m['matchedSkills'])}

Write the application note in first person. Do NOT start with "I am writing". Start with something engaging."""

    # 1. Try Groq Cloud first
    llm_out = call_groq([
        {'role': 'system', 'content': 'You are an expert career counselor helping engineering students craft high-impact, authentic application pitches. Never use emojis. Write in first person.'},
        {'role': 'user', 'content': prompt}
    ], temperature=0.6)

    # 2. Try Gemini fallback
    if not llm_out:
        llm_out = call_gemini(prompt, temperature=0.7)

    if llm_out:
        return llm_out.strip(), True

    # Regex fallback draft
    name = student.get('name','')
    branch = student.get('branch','')
    year = student.get('year','')
    college = student.get('college','')
    matched = ', '.join(m['matchedSkills'][:3]) or 'the required skills'
    interests_str = ', '.join((student.get('interests') or [])[:2])

    draft = f"As a {year}{'st' if year==1 else 'nd' if year==2 else 'rd' if year==3 else 'th'} year {branch} student"
    if college: draft += f" from {college}"
    draft += f", I am deeply excited about {opp['title']}. "
    draft += f"My hands-on experience with {matched} directly aligns with what this opportunity demands. "
    if interests_str:
        draft += f"My passion for {interests_str} makes this a perfect next step in my journey. "
    draft += f"I would love to bring my skills to {opp['org']} and make a meaningful contribution."
    return draft, False


# ══════════════════════════════════════════════
# AI AGENT (Groq Cloud LLM + Redrob Local Match Engine)
# ══════════════════════════════════════════════
def ai_agent(message, student):
    msg = message.lower().strip()
    name = (student.get('name') or 'Student').split()[0]
    skills = student.get('skills') or []

    # Local Redrob AI ranker computes mathematical match scores
    ranked = sorted(
        [{'opp': o, 'match': match_score(student, o)} for o in all_opps()],
        key=lambda x: (not x['match']['eligible'], -x['match']['percentage'])
    )

    # 1. Try Groq LLM for intelligent contextual responses
    if GROQ_KEY:
        opp_context = ""
        for i, item in enumerate(ranked[:6], 1):
            o, m = item['opp'], item['match']
            dl = days_left(o['deadline'])
            opp_context += f"- [{o['id']}] {o['title']} ({o['type']}) at {o['org']}: {m['percentage']}% match. Matched skills: {', '.join(m['matchedSkills'][:4]) or 'None'}. Missing skills: {', '.join(m['missingSkills'][:4]) or 'None'}. Deadline: {dl}d left. Stipend: {o['stipend']}.\n"

        student_summary = f"Name: {name}, Year: {student.get('year', 'N/A')}, Branch: {student.get('branch', 'N/A')}, CGPA: {student.get('cgpa', 'N/A')}, Skills: {', '.join(skills) or 'None specified'}, Interests: {', '.join(student.get('interests') or [])}"

        system_prompt = (
            "You are SkillMatch Copilot, a high-precision AI advisor for engineering students. "
            "You have direct access to their profile and real-time algorithmic match scores calculated by our Redrob AI ranking engine (all-MiniLM-L6-v2 + BM25 + multi-signal calibration).\n"
            "Rules:\n"
            "1. NEVER use any emojis.\n"
            "2. Keep responses concise, punchy, professional, and actionable (under 120 words).\n"
            "3. Mention specific opportunities from the context by their exact title and match percentage.\n"
            "4. Point out what specific skills to learn to unlock better matches when relevant."
        )

        groq_resp = call_groq([
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"Student Profile:\n{student_summary}\n\nTop Matched Opportunities:\n{opp_context}\n\nStudent Query: {message}"}
        ], temperature=0.3, max_tokens=300)

        if groq_resp:
            # Detect cited opportunities for interactive mini cards
            cited_ids = []
            for item in ranked[:6]:
                o = item['opp']
                if o['title'].lower() in groq_resp.lower() or o['org'].lower() in groq_resp.lower():
                    cited_ids.append(o['id'])
            if not cited_ids and len(ranked) > 0:
                cited_ids = [ranked[0]['opp']['id']]
            return groq_resp, cited_ids[:3]

    # Deterministic fallback when offline or no API key
    if any(k in msg for k in ['best','top','recommend','should apply','what to apply','perfect']):
        top = ranked[:3]
        r = f"Based on your **{student.get('branch')}** profile with **{len(skills)} skills**, your top 3 matches:\n\n"
        for i, item in enumerate(top, 1):
            o, m = item['opp'], item['match']
            dl = days_left(o['deadline'])
            r += f"**{i}. {o['title']}** — {m['percentage']}% match\n"
            r += f"   Matched: {', '.join(m['matchedSkills'][:3]) or 'General eligibility'}\n"
            r += f"   {o['stipend']} · {dl}d left · {o['mode']}\n\n"
        return r, [item['opp']['id'] for item in top]

    if any(k in msg for k in ['missing','gap','learn','skill','improve']):
        mc = {}
        for item in ranked:
            for s in item['match']['missingSkills']:
                mc[s] = mc.get(s, 0) + 1
        top5 = sorted(mc.items(), key=lambda x: -x[1])[:5]
        r = f"Top skills to learn that unlock the most opportunities:\n\n"
        for skill, count in top5:
            pct_bar = round((count / len(all_opps())) * 10)
            bar = 'x' * pct_bar + '.' * (10 - pct_bar)
            r += f"**{skill}** [{bar}] → {count} more opportunities\n"
        r += f"\nYou have {len(skills)} skills. Adding these would immediately boost your rankings."
        return r, []

    if any(k in msg for k in ['hackathon','hack']):
        hacks = [x for x in ranked if x['opp']['typeKey']=='hackathon']
        r = f"Found **{len(hacks)} hackathons** for you:\n\n"
        for item in hacks[:5]:
            o, m = item['opp'], item['match']
            dl = days_left(o['deadline'])
            r += f"**{o['title']}** — {m['percentage']}% · {'URGENT '+str(dl)+'d' if dl<=3 else str(dl)+'d left'}\n"
            r += f"   {o['stipend']} · {o['mode']}\n\n"
        return r, [x['opp']['id'] for x in hacks[:5]]

    if any(k in msg for k in ['intern','internship','job']):
        interns = [x for x in ranked if x['opp']['typeKey']=='internship']
        r = f"**{len(interns)} internship opportunities** for you:\n\n"
        for item in interns:
            o, m = item['opp'], item['match']
            r += f"**{o['title']}** — {m['percentage']}% match · {o['stipend']}\n   {o['location']} · {o['mode']}\n\n"
        return r, [x['opp']['id'] for x in interns]

    if any(k in msg for k in ['urgent','deadline','closing','soon','expire']):
        urgent = [x for x in ranked if 0 <= days_left(x['opp']['deadline']) <= 7]
        if not urgent:
            return "No urgent deadlines right now!", []
        r = f"**{len(urgent)} opportunities closing within 7 days:**\n\n"
        for item in urgent:
            o, m = item['opp'], item['match']
            dl = days_left(o['deadline'])
            r += f"**{o['title']}** — {'TODAY' if dl==0 else str(dl)+' days'} left\n   {m['percentage']}% match · {o['stipend']}\n\n"
        return r, [x['opp']['id'] for x in urgent]

    if any(k in msg for k in ['eligible','qualify','can i','am i']):
        el = [x for x in ranked if x['match']['eligible']]
        r = f"You're **eligible for {len(el)} of {len(all_opps())} opportunities** (Year {student.get('year')}, {student.get('branch')}, CGPA {student.get('cgpa','N/A')})\n\n"
        if el:
            r += f"Your best eligible match: **{el[0]['opp']['title']}** at {el[0]['match']['percentage']}%"
        return r, [x['opp']['id'] for x in el[:3]]

    if any(k in msg for k in ['fellowship','research','gsoc','mlh']):
        fell = [x for x in ranked if x['opp']['typeKey'] in ['fellowship','research','opensource']]
        r = f"**{len(fell)} fellowship/research opportunities:**\n\n"
        for item in fell[:4]:
            o, m = item['opp'], item['match']
            r += f"**{o['title']}** — {m['percentage']}% · {o['stipend']}\n\n"
        return r, [x['opp']['id'] for x in fell[:4]]

    # Default
    el_count = len([x for x in ranked if x['match']['eligible']])
    strong = len([x for x in ranked if x['match']['percentage'] >= 70])
    urgent_c = len([x for x in ranked if 0 <= days_left(x['opp']['deadline']) <= 3])
    r = f"Hey **{name}**! Quick snapshot:\n\n"
    r += f"- Eligible opportunities: **{el_count}**\n"
    r += f"- Strong matches (70%+): **{strong}**\n"
    if urgent_c > 0:
        r += f"- URGENT — closing in 3 days: **{urgent_c}**\n"
    r += f"\nTry: 'What should I apply to?' / 'Show hackathons' / 'What skills am I missing?'"
    return r, []


# ══════════════════════════════════════════════
# STATIC FILES
# ══════════════════════════════════════════════
@app.route('/')
def root(): return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path): return send_from_directory('.', path)


# ══════════════════════════════════════════════
# API — PROFILE
# ══════════════════════════════════════════════
@app.route('/api/profile', methods=['POST'])
def save_profile():
    data = request.json
    pid = data.get('id') or str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db = get_db()
    ex = db.execute('SELECT id FROM profiles WHERE id=?', (pid,)).fetchone()
    if ex:
        db.execute('''UPDATE profiles SET name=?,email=?,year=?,branch=?,cgpa=?,
                      college=?,skills=?,interests=?,updated_at=? WHERE id=?''',
                   (data['name'], data.get('email',''), int(data['year']), data['branch'],
                    float(data.get('cgpa') or 0), data.get('college',''),
                    json.dumps(data.get('skills',[])), json.dumps(data.get('interests',[])), now, pid))
    else:
        db.execute('INSERT INTO profiles VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                   (pid, data['name'], data.get('email',''), int(data['year']), data['branch'],
                    float(data.get('cgpa') or 0), data.get('college',''),
                    json.dumps(data.get('skills',[])), json.dumps(data.get('interests',[])), now, now))
    db.commit(); db.close()
    return jsonify({'success': True, 'id': pid})

@app.route('/api/profile/<pid>', methods=['GET'])
def get_profile(pid):
    db = get_db()
    row = db.execute('SELECT * FROM profiles WHERE id=?', (pid,)).fetchone()
    db.close()
    if not row: return jsonify({'error': 'Not found'}), 404
    p = dict(row)
    p['skills'] = json.loads(p['skills'] or '[]')
    p['interests'] = json.loads(p['interests'] or '[]')
    return jsonify(p)


# ══════════════════════════════════════════════
# API — OPPORTUNITIES
# ══════════════════════════════════════════════
@app.route('/api/opportunities')
def get_opportunities():
    pid = request.args.get('profile_id')
    opp_type = request.args.get('type')
    search = request.args.get('search', '').lower()

    opps = all_opps()[:]
    if opp_type and opp_type != 'all':
        opps = [o for o in opps if o['typeKey'] == opp_type]
    if search:
        opps = [o for o in opps if search in (o['title']+o['org']+o.get('description','')+' '.join(o.get('tags',[]))).lower()]

    if pid:
        db = get_db()
        row = db.execute('SELECT * FROM profiles WHERE id=?', (pid,)).fetchone()
        db.close()
        if row:
            student = dict(row)
            student['skills'] = json.loads(student['skills'] or '[]')
            student['interests'] = json.loads(student['interests'] or '[]')
            result = [{'match': match_score(student, o), **o} for o in opps]
            result.sort(key=lambda x: (not x['match']['eligible'], -x['match']['percentage']))
            return jsonify(result)

    return jsonify(opps)


# ══════════════════════════════════════════════
# API — RESUME UPLOAD
# ══════════════════════════════════════════════
@app.route('/api/resume', methods=['POST'])
def parse_resume():
    """
    PDF upload -> extract skills using India Runs keyword extraction logic.
    Also extracts CGPA, year, branch hints.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    f = request.files['file']
    text = ''

    if f.filename.endswith('.pdf'):
        if not PDF_AVAILABLE:
            return jsonify({'error': 'pdfplumber not installed. Run: pip install pdfplumber'}), 500
        try:
            with pdfplumber.open(io.BytesIO(f.read())) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
        except Exception as e:
            return jsonify({'error': f'PDF parse error: {str(e)}'}), 500
    elif f.filename.endswith('.txt'):
        text = f.read().decode('utf-8', errors='replace')
    else:
        return jsonify({'error': 'Please upload PDF or TXT file'}), 400

    skills = extract_skills_from_text(text)
    meta = extract_resume_metadata(text)

    return jsonify({
        'skills': skills,
        'metadata': meta,
        'charCount': len(text),
        'rawSnippet': text[:300]
    })


# ══════════════════════════════════════════════
# API — INGEST (WhatsApp/Email Forward)
# ══════════════════════════════════════════════
@app.route('/api/ingest', methods=['POST'])
def ingest_opportunity():
    """
    Paste raw WhatsApp/email text -> LLM extracts structured opportunity ->
    Adds to live feed -> Re-runs match against all students.
    This is the flagship demo feature.
    """
    data = request.json
    raw_text = data.get('text', '').strip()
    if not raw_text:
        return jsonify({'error': 'No text provided'}), 400

    # Parse with LLM (or regex fallback)
    parsed, used_llm = parse_opportunity_with_llm(raw_text)

    # Add metadata
    new_id = max((o['id'] for o in all_opps()), default=100) + 1
    parsed['id'] = new_id
    parsed['orgInitials'] = ''.join(w[0] for w in parsed.get('org','??').split()[:2]).upper() or '??'
    parsed['orgColor'] = '#' + '%06x' % (hash(parsed.get('org','X')) & 0xFFFFFF)
    parsed['applicants'] = 0
    parsed['featured'] = False
    if not parsed.get('applyUrl'):
        parsed['applyUrl'] = ''

    # Save to DB
    db = get_db()
    db.execute('INSERT INTO ingested_opps (data, ingested_at, ingested_by) VALUES (?,?,?)',
               (json.dumps(parsed), datetime.utcnow().isoformat(), data.get('admin_id', 'admin')))
    db.commit()

    # Add to runtime
    RUNTIME_OPPS.append(parsed)

    # Re-run matching for all profiles (the magic moment)
    profiles_updated = 0
    rows = db.execute('SELECT id, skills, interests, year, branch, cgpa FROM profiles').fetchall()
    db.close()

    matched_students = []
    for row in rows:
        student = dict(row)
        student['skills'] = json.loads(student['skills'] or '[]')
        student['interests'] = json.loads(student['interests'] or '[]')
        m = match_score(student, parsed)
        if m['percentage'] >= 40:
            matched_students.append({'profile_id': student['id'], 'match': m})
        profiles_updated += 1

    return jsonify({
        'success': True,
        'opportunity': parsed,
        'usedLLM': used_llm,
        'profilesRescored': profiles_updated,
        'matchedStudents': len(matched_students),
        'matchDetails': matched_students[:5],
        'message': f"Listed! Matched {len(matched_students)}/{profiles_updated} students."
    })


# ══════════════════════════════════════════════
# API — APPLICATION DRAFT
# ══════════════════════════════════════════════
@app.route('/api/draft', methods=['POST'])
def get_draft():
    data = request.json
    pid = data.get('profile_id')
    opp_id = int(data.get('opp_id'))

    db = get_db()
    row = db.execute('SELECT * FROM profiles WHERE id=?', (pid,)).fetchone()
    db.close()
    if not row:
        return jsonify({'error': 'Profile not found'}), 404

    student = dict(row)
    student['skills'] = json.loads(student['skills'] or '[]')
    student['interests'] = json.loads(student['interests'] or '[]')

    opp = next((o for o in all_opps() if o['id'] == opp_id), None)
    if not opp:
        return jsonify({'error': 'Opportunity not found'}), 404

    draft, used_llm = generate_draft(student, opp)
    m = match_score(student, opp)

    return jsonify({
        'draft': draft,
        'usedLLM': used_llm,
        'matchScore': m['percentage'],
        'matchedSkills': m['matchedSkills'],
        'opportunity': opp['title']
    })


# ══════════════════════════════════════════════
# API — APPLY & BOOKMARKS
# ══════════════════════════════════════════════
@app.route('/api/apply', methods=['POST'])
def apply_opp():
    data = request.json
    pid, oid, status = data['profile_id'], int(data['opp_id']), data.get('status','applied')
    now = datetime.utcnow().isoformat()
    db = get_db()
    ex = db.execute('SELECT id FROM applications WHERE profile_id=? AND opp_id=?', (pid, oid)).fetchone()
    if ex:
        db.execute('UPDATE applications SET status=?,updated_at=? WHERE id=?', (status, now, ex['id']))
    else:
        db.execute('INSERT INTO applications (profile_id,opp_id,status,applied_at,updated_at) VALUES (?,?,?,?,?)',
                   (pid, oid, status, now, now))
    db.execute('INSERT OR IGNORE INTO bookmarks VALUES (?,?,?)', (pid, oid, now))
    db.commit(); db.close()
    return jsonify({'success': True, 'status': status})

@app.route('/api/bookmarks', methods=['GET'])
def get_bookmarks():
    pid = request.args.get('profile_id')
    db = get_db()
    rows = db.execute('SELECT opp_id FROM bookmarks WHERE profile_id=?', (pid,)).fetchall()
    db.close()
    return jsonify([r['opp_id'] for r in rows])

@app.route('/api/bookmarks', methods=['POST'])
def add_bookmark():
    data = request.json
    db = get_db()
    db.execute('INSERT OR IGNORE INTO bookmarks VALUES (?,?,?)',
               (data['profile_id'], int(data['opp_id']), datetime.utcnow().isoformat()))
    db.commit(); db.close()
    return jsonify({'success': True})

@app.route('/api/bookmarks', methods=['DELETE'])
def del_bookmark():
    data = request.json
    db = get_db()
    db.execute('DELETE FROM bookmarks WHERE profile_id=? AND opp_id=?',
               (data['profile_id'], int(data['opp_id'])))
    db.commit(); db.close()
    return jsonify({'success': True})

@app.route('/api/applications')
def get_applications():
    pid = request.args.get('profile_id')
    db = get_db()
    rows = db.execute(
        'SELECT opp_id, status, applied_at, updated_at FROM applications WHERE profile_id=? ORDER BY applied_at DESC',
        (pid,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# ══════════════════════════════════════════════
# API — CHAT (AI Agent)
# ══════════════════════════════════════════════
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message','')
    pid = data.get('profile_id')
    student = {}
    if pid:
        db = get_db()
        row = db.execute('SELECT * FROM profiles WHERE id=?', (pid,)).fetchone()
        db.close()
        if row:
            student = dict(row)
            student['skills'] = json.loads(student['skills'] or '[]')
            student['interests'] = json.loads(student['interests'] or '[]')

    response, opp_ids = ai_agent(message, student)
    return jsonify({'response': response, 'oppIds': opp_ids})


# ══════════════════════════════════════════════
# API — ADMIN ANALYTICS
# ══════════════════════════════════════════════
@app.route('/api/admin')
def admin_analytics():
    db = get_db()
    total_students = db.execute('SELECT COUNT(*) c FROM profiles').fetchone()['c']
    total_apps = db.execute('SELECT COUNT(*) c FROM applications').fetchone()['c']
    total_bm = db.execute('SELECT COUNT(*) c FROM bookmarks').fetchone()['c']
    total_ingested = db.execute('SELECT COUNT(*) c FROM ingested_opps').fetchone()['c']

    # Applications by opportunity
    by_opp = db.execute('''
        SELECT opp_id, COUNT(*) apps,
               SUM(CASE WHEN status='applied' THEN 1 ELSE 0 END) applied,
               SUM(CASE WHEN status='selected' THEN 1 ELSE 0 END) selected
        FROM applications GROUP BY opp_id ORDER BY apps DESC LIMIT 10
    ''').fetchall()

    # Recent applications (last 20)
    recent = db.execute('''
        SELECT a.applied_at, a.status, a.opp_id, p.name, p.branch, p.year
        FROM applications a JOIN profiles p ON a.profile_id = p.id
        ORDER BY a.applied_at DESC LIMIT 20
    ''').fetchall()

    # Status breakdown
    status_counts = db.execute('''
        SELECT status, COUNT(*) c FROM applications GROUP BY status
    ''').fetchall()

    # Student branches
    branch_counts = db.execute('''
        SELECT branch, COUNT(*) c FROM profiles GROUP BY branch ORDER BY c DESC
    ''').fetchall()

    db.close()

    # Enrich by_opp with opportunity titles
    opp_map = {o['id']: o['title'] for o in all_opps()}

    return jsonify({
        'stats': {
            'totalStudents': total_students,
            'totalApplications': total_apps,
            'totalBookmarks': total_bm,
            'ingestedOpps': total_ingested,
            'liveOpportunities': len(all_opps()),
        },
        'byOpportunity': [{
            'oppId': r['opp_id'],
            'title': opp_map.get(r['opp_id'], f'Opp #{r["opp_id"]}'),
            'apps': r['apps'],
            'applied': r['applied'],
            'selected': r['selected'],
        } for r in by_opp],
        'recentActivity': [{
            'at': r['applied_at'], 'status': r['status'], 'opp_id': r['opp_id'],
            'oppTitle': opp_map.get(r['opp_id'], f'Opp #{r["opp_id"]}'),
            'student': r['name'], 'branch': r['branch'], 'year': r['year'],
        } for r in recent],
        'statusBreakdown': {r['status']: r['c'] for r in status_counts},
        'branchBreakdown': {r['branch']: r['c'] for r in branch_counts},
        'hasGroqKey': bool(GROQ_KEY),
        'hasGeminiKey': bool(GEMINI_KEY),
    })

# ── Health check ──
@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'groq': bool(GROQ_KEY), 'gemini': bool(GEMINI_KEY), 'pdf': PDF_AVAILABLE})


if __name__ == '__main__':
    print("\nSkillMatch v2 running at http://localhost:5000")
    print(f"Groq Cloud API: {'CONFIGURED' if GROQ_KEY else 'NOT SET'}")
    print(f"Gemini API: {'CONFIGURED' if GEMINI_KEY else 'NOT SET'}")
    print(f"PDF parsing: {'available' if PDF_AVAILABLE else 'unavailable'}\n")
    app.run(debug=True, port=5000, host='0.0.0.0')


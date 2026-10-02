# SkillMatch — Student Skill-to-Opportunity Matching Platform (PS-09)

> **Intelligent Candidate & Opportunity Discovery Engine**  
> Built for PS-09: Connecting college students with hackathons, internships, fellowships, and research opportunities before deadlines expire.

---

## 📌 Problem & Solution Overview

### The Problem
Opportunities for engineering students are scattered across unorganized WhatsApp groups, Discord servers, buried emails, and physical notice boards. Critical deadlines (such as hackathons closing tomorrow or niche research fellowships) are missed simply because students never encounter them in time.

### The Solution
SkillMatch centralizes opportunity discovery and evaluates match compatibility using a **multi-signal algorithmic engine** adapted from candidate ranking principles. It extracts competencies from student resumes, ingests unformatted opportunity broadcasts from messaging channels, and calculates calibrated fit scores.

---

## ⚡ Core Platform Capabilities

1. **Multi-Signal Calibrated Match Engine (`engine.py`)**
   - **BM25 Lexical Term Frequency**: Extracts technical tokens from resumes and opportunities.
   - **Requirement Coverage**: Quantifies match ratio on mandatory vs. preferred skills.
   - **Academic Eligibility Gates**: Strict filtering on Year of Study, Discipline / Branch, and minimum CGPA.
   - **Sigmoid Score Normalization**: Re-scales fit index into a normalized [0, 100%] distribution.
   - **Explainable Signals**: Line-by-line verification breakdown detailing why a match score was assigned.

2. **Automated Resume Skill Ingestion (`/api/resume`)**
   - Upload PDF or TXT resumes in the Profile Wizard.
   - Automatically detects technical competencies, year hints, branch, and CGPA.

3. **Message Broadcast Ingestion (`admin.html` → `/api/ingest`)**
   - Paste raw, messy WhatsApp forwards or email blurbs.
   - Automatically extracts structured opportunity schema (title, organization, deadline, required skills, compensation, and apply links).
   - Instantly publishes to the live catalog and rescores all registered student profiles.

4. **Opportunity Deep Dive & Competency Radar (`opportunity.html`)**
   - Visual comparison between candidate competencies and opportunity requirements using Chart.js radar charts.
   - Missing skill-gap identification with actionable learning suggestions.
   - Direct redirection to real external registration portals.

5. **Tailored Application Pitch Note (`/api/draft`)**
   - Generates personalized, first-person application blurbs highlighting verified skill intersections.

6. **Application Tracking Pipeline (`bookmarks.html`)**
   - Monitor opportunities through structured funnel stages: *Saved → Applied → Shortlisted → Selected*.
   - Countdown alerts for listings closing within 3 days.

7. **Opportunity Copilot (`dashboard.html` / `agent.js`)**
   - Real-time interactive assistant capable of filtering highest fit hackathons, evaluating skill gaps, and answering student queries.

---

## 🏗️ Architecture

```
skillmatch_ui/
├── app.py              # Flask API backend & database orchestration
├── engine.py           # Multi-signal matching & BM25 extraction engine
├── index.html          # Landing page & 3-step onboarding wizard
├── dashboard.html      # Ranked match catalog, filters & copilot drawer
├── opportunity.html    # Opportunity analysis, skill radar & pitch generator
├── bookmarks.html      # Candidate tracking funnel & status manager
├── profile.html        # Academic credentials & resume sync
├── admin.html          # Message broadcast ingestion & platform analytics
├── css/
│   └── styles.css      # Design system tokens, layout & typography
├── js/
│   ├── icons.js        # Minimalist vector SVG icon library
│   ├── agent.js        # AI Copilot client logic
│   ├── data.js         # Fallback data definitions
│   ├── matcher.js      # Client-side validation helpers
│   └── storage.js      # Session cache management
├── START_HERE.bat      # One-click startup script
├── requirements.txt    # Python dependencies
└── README.md           # Documentation
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.8+
- Modern Web Browser

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start Application
```bash
python app.py
```
Or simply double-click `START_HERE.bat` on Windows.

### 4. Access Platform
Open [http://localhost:5000](http://localhost:5000) in your browser.

*(Optional)* To enable Gemini LLM extraction for broadcast messages:
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-gemini-api-key"
python app.py
```
*Note: If no API key is set, the system seamlessly uses the built-in lexical regex engine.*

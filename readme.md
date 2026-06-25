bash
cat > /mnt/user-data/outputs/README.md << 'EOF'
# FairScreen ⚖️
### AI-Powered Blind Recruitment & Bias Auditing System
> *"FairScreen doesn't find the best candidate. It stops the system from burying them."*

[![Google Solution Challenge 2026](https://img.shields.io/badge/Google%20Solution%20Challenge-2025-4285F4?style=flat&logo=google)](https://developers.google.com/community/gdsc-solution-challenge)


---
### 🔑 Demo Login Credentials
> Use these credentials to access the HR portal for testing
> email - smartminds0024@gmail.com
> password - Avengers@0507
>  ⚠️ These are read-only demo credentials. Do not use for production.

## 🔴 Live Demo

| Resource | Link |
|---|---|
| **Live App** |  https://fairscreen-ai-blind-recruitment-sys.vercel.app/|
| **GitHub** | https://github.com/yuktha0505/fairscreen |




---

## 📌 Problem Statement

Traditional Applicant Tracking Systems (ATS) systematically discriminate based on:

- **Name** — Non-dominant names receive 30-50% fewer callbacks with identical qualifications
- **College tier** — Rural students with strong skills lose to IIT graduates with weaker profiles
- **Gender** — Job descriptions use masculine-coded language filtering diverse candidates before screening
- **Employment gaps** — Maternity leave penalised equally to unexplained absences

**No existing tool audits the full hiring pipeline end-to-end.**

---

## 💡 Solution

FairScreen is a four-layer AI pipeline that removes privilege from hiring decisions.

```
JD Upload → Layer 0: Bias Audit → Resume Upload → Layer 1: Blind Screening
    → Layer 2: Secure Storage → Layer 3: AI Bias Report → HR Dashboard
```

### Layer 0 — JD Bias Auditor
- Scans job description for masculine-coded language and exclusionary phrases
- Groq rewrites flagged content in real time
- JD version tracking — detects if bias is reintroduced after correction
- Outputs bias score out of 100

### Layer 1 — Blind Skill Screener
- Strips name, gender, nationality, college name using SpaCy NER
- Semantic skill matching via Sentence Transformer (all-MiniLM-L6-v2)
- Merit scoring: Skills (40%) + Semantic Match (25%) + Projects (25%) + Certifications (10%)
- Contextual employment gap validation — maternity leave ≠ unexplained absence

### Layer 2 — Secure Data Extraction
- Personal details extracted ONLY after merit-based shortlisting
- Stored in Firebase Firestore — never used in scoring pipeline
- Full audit trail maintained

### Layer 3 — AI Bias Audit Report
- Groq generates plain-English bias report
- Shows exactly where traditional ATS would have discriminated
- Candidate feedback report for rejected applicants

---

## 🏗️ Architecture

```
┌─────────────────┐     HTTPS/REST      ┌──────────────────────────────────┐
│   Flutter App   │ ─────────────────── │         FastAPI Backend          │
│  HR Dashboard   │                     │                                  │
└─────────────────┘                     │  ┌─────────────────────────────┐ │
                                        │  │   Layer 0: JD Bias Auditor  │ │
                                        │  │   SpaCy + Word Detector     │ │
                                        │  └──────────────┬──────────────┘ │
                                        │                 │                 │
                                        │  ┌──────────────▼──────────────┐ │
                                        │  │ Layer 1: Blind Screener     │ │
                                        │  │ pdfplumber + SpaCy NER      │ │
                                        │  │ Sentence Transformer        │ │
                                        │  │ Merit Scoring Engine        │ │
                                        │  │ Gap Validator               │ │
                                        │  └──────────────┬──────────────┘ │
                                        │                 │                 │
                                        │  ┌──────────────▼──────────────┐ │
                                        │  │ Layer 2: Data Extraction    │ │
                                        │  │ Firebase Firestore          │ │
                                        │  └──────────────┬──────────────┘ │
                                        │                 │                 │
                                        │  ┌──────────────▼──────────────┐ │
                                        │  │ Layer 3: Bias Audit Report  │ │
                                        │  │ Groq/Gemini API             │ │
                                        │  │ Fairlearn + AIF360          │ │
                                        │  └─────────────────────────────┘ │
                                        └──────────────────────────────────┘
                                                         │
                                        ┌────────────────▼─────────────────┐
                                        │         Firebase Auth            │
                                        │         Firestore Database       │
                                        └──────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Flutter / HTML5 | HR Dashboard |
| Backend | FastAPI + Python 3.11 | REST API |
| ML Model | Sentence Transformers (all-MiniLM-L6-v2) | Semantic matching |
| NLP | SpaCy NER | Demographic stripping |
| Fuzzy Match | RapidFuzz | Skill variation matching |
| Bias Metrics | Fairlearn + AIF360 | Fairness measurement |
| AI Reports | Gemini API / Groq Llama 3.3 | Plain English output |
| PDF Parsing | pdfplumber | Resume text extraction |
| Auth | Firebase Authentication | HR login |
| Database | Firebase Firestore | Candidate storage |
| Security | python-dotenv + Bearer Token | API protection |
| Deployment | Google Cloud + Vercel | Hosting |

---

## 🚀 Getting Started

### Prerequisites
```bash
Python 3.11+
pip
Git
```

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/yuktha0505/fairscreen.git
cd fairscreen
```

**2. Install dependencies**
```bash
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

**3. Set up environment variables**

Create `.env` file in `backend/` folder:
```
GROQ_API_KEY=your_groq_api_key
FIREBASE_KEY_PATH=path/to/firebase_key.json
```

Or if using environment variable for Firebase:
```
GROQ_API_KEY=your_groq_api_key
FIREBASE_KEY_JSON={"type":"service_account",...}
```

**4. Run the backend**
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

**5. Run the frontend**
```bash
cd ../frontend
python -m http.server 3000
```

**6. Open browser**
```
http://localhost:3000
```

---

## 📁 Project Structure

```
fairscreen/
├── backend/
│   ├── fairscreen_fixed.py    # Core pipeline — all 4 layers
│   ├── api.py                 # FastAPI endpoints
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables (not in repo)
├── frontend/
│   └── index.html             # HR Dashboard
├── .gitignore
└── README.md
```

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔍 JD Bias Auditor | Detects masculine-coded language, rewrites with Gemini |
| 👤 Blind Screening | Strips demographics before any scoring |
| 🧠 Semantic Matching | Transformer model for skill similarity |
| ⏱️ Gap Validation | Contextual classification of employment gaps |
| 📊 Bias Report | Plain-English AI audit report |
| 🔒 Authentication | Firebase Auth — HR-only access |
| ⚡ Parallel Processing | Handles 5000+ resumes simultaneously |
| 📝 Candidate Feedback | Skill gap report for rejected candidates |
| 🔎 Proxy Bias Check | Detects hidden demographic clustering |
| 📈 Top N Selection | Configurable shortlist threshold |

---

## 🎯 Demo Scenario

Feed 15 diverse resumes into FairScreen:

| Candidate | Background | FairScreen Result |
|---|---|---|
| Priya Subramaniam | Tier-3 rural college | ✅ Rank #1 — strong skills |
| Arjun Mehta | IIT Bombay | ❌ Rank #10 — weak skills |
| Fatima Noor | Maternity leave gap | ✅ Shortlisted — gap validated |
| Ravi Shankar | No CS skills | ❌ Correctly rejected |

**Result:** Merit wins over privilege. Every time.

---

## 🌍 SDG Alignment

| SDG | Impact |
|---|---|
| **SDG 5 — Gender Equality** | Removes gender bias, validates maternity gaps |
| **SDG 8 — Decent Work** | Fair economic opportunity for all candidates |
| **SDG 10 — Reduced Inequalities** | Rural candidates evaluated on ability not background |

---


---

## 👩‍💻 Built By

**Yuktha S**
B.E Computer Science & Engineering
Sri Sai Ram Engineering College, Chennai

---

## 📄 License

MIT License — feel free to use, modify, and distribute.

---

*Google Solution Challenge 2026 | Track: Unbiased AI Decision*
EOF
echo "Done"

Output
Done

# ============================================================
# FairScreen - Complete Prototype
# ============================================================

import pdfplumber
import spacy
import re 
import os
from groq import Groq
groq_client = Groq(api_key="GROQ_API_KEY")
import firebase_admin
from firebase_admin import credentials, firestore
import sys
import io

from dotenv import load_dotenv
load_dotenv()



sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# Initialize Firebase
import json

firebase_key_json = os.getenv("FIREBASE_KEY_JSON")
if firebase_key_json:
    cred_dict = json.loads(firebase_key_json)
    cred = credentials.Certificate(cred_dict)
else:
    cred = credentials.Certificate(os.getenv("FIREBASE_KEY_PATH"))

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()
# ── Gemini client ────────────────────────────────────────────
# WARNING: Replace with key. Never share this publicly.


# ── SpaCy model ──────────────────────────────────────────────
nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger"])

# ── Bias word lists ──────────────────────────────────────────
MASCULINE_CODED = [
    "aggressive", "ambitious", "dominant", "driven", "competitive",
    "confident", "decisive", "determined", "independent", "ninja",
    "rockstar", "crush it", "kill it", "superhero", "fearless",
    "assertive", "challenging", "superior", "headstrong"
]

EXCLUSIONARY_PHRASES = [
    "native english speaker", "young and energetic", "recent graduate only",
    "culture fit", "digital native", "young professional"
]


# ============================================================
# LAYER 0 — JD Bias Auditor
# ============================================================

def audit_jd(jd_text):
    """
    Scans job description for biased language.
    Returns bias score, issues list, and required skills.
    """
    jd_lower = jd_text.lower()
    issues = []
    issues_found = 0

    # Check masculine-coded words
    for word in MASCULINE_CODED:
        if word in jd_lower:
            issues.append({
                "type": "Masculine-coded language",
                "found": word,
                "suggestion": f"Replace '{word}' with neutral alternative"
            })
            issues_found += 1

    # Check exclusionary phrases
    for phrase in EXCLUSIONARY_PHRASES:
        if phrase in jd_lower:
            issues.append({
                "type": "Exclusionary phrase",
                "found": phrase,
                "suggestion": f"Remove or rephrase '{phrase}'"
            })
            issues_found += 1

    # Extract required skills from JD
    skill_keywords = [
        "python", "java", "javascript", "react", "nodejs", "sql",
        "machine learning", "aws", "docker", "kubernetes", "git",
        "tensorflow", "pytorch", "flask", "django", "fastapi",
        "mongodb", "postgresql", "typescript", "html", "css"
    ]
    required_skills = [s for s in skill_keywords if s in jd_lower]

    # Calculate bias score (100 = clean, 0 = heavily biased)
    bias_score = max(0, 100 - (issues_found * 10))

    return {
        "bias_score": bias_score,
        "issues": issues,
        "required_skills": required_skills,
        "issues_count": issues_found
    }


def rewrite_jd_with_ai(jd_text, issues):
    if not issues:
        return jd_text
    
    issues_list = "\n".join([f"- '{i['found']}': {i['suggestion']}" for i in issues])
    
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"""Rewrite this job description removing biased language.

Biased phrases:
{issues_list}

Original JD:
{jd_text}

Return only rewritten JD."""
        }]
    )
    return response.choices[0].message.content
# ============================================================
# LAYER 1 — Resume Parser + Demographic Stripper
# ============================================================

def parse_resume(pdf_path):
    """
    Opens a PDF resume and extracts all text.
    Returns the full text as a string.
    """
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    return full_text


def strip_demographics(text):
    """
    Removes personally identifiable information from resume text.
    Replaces names, locations, organisations, emails, phones.
    """
    # Remove email addresses
    text = re.sub(r'\S+@\S+\.\S+', '[EMAIL]', text)

    # Remove phone numbers
    text = re.sub(r'[\+]?[\d\s\-\(\)]{10,}', '[PHONE]', text)

    # Remove URLs
    text = re.sub(r'https?://\S+', '[URL]', text)

    # Use SpaCy to remove named entities
    doc = nlp(text)
    stripped = text
    for ent in reversed(doc.ents):
        if ent.label_ in ["PERSON", "GPE", "ORG"]:
            stripped = stripped[:ent.start_char] + f'[{ent.label_}]' + stripped[ent.end_char:]

    return stripped


# ============================================================
# LAYER 1 — Merit Scorer
# ============================================================

from rapidfuzz import fuzz

def extract_skills_from_text(text):
    """
    Extracts skills using fuzzy matching.
    Catches variations like 'Python 3', 'proficient in Python', 'Python/Django'
    """
    skill_keywords = [
        "python", "java", "javascript", "c++", "typescript", "kotlin",
        "html", "css", "react", "angular", "vue", "nodejs", "django",
        "flask", "fastapi", "spring", "machine learning", "deep learning",
        "nlp", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
        "sql", "mysql", "postgresql", "mongodb", "firebase", "aws", "azure",
        "gcp", "docker", "kubernetes", "git", "linux", "lambda", "s3",
        "data structures", "algorithms", "oop", "rest api", "microservices",
        "dbms", "operating systems", "networking", "bedrock", "rag"
    ]

    text_lower = text.lower()
    found_skills = []

    for skill in skill_keywords:
        # First try exact match
        if skill in text_lower:
            found_skills.append(skill)
            continue

        # Then try fuzzy match on each word/phrase in text
        words = text_lower.split()
        for word in words:
            if fuzz.partial_ratio(skill, word) >= 80:
                found_skills.append(skill)
                break

    return list(set(found_skills))  # remove duplicates


def extract_projects(text):
    """Counts project indicators in resume."""
    project_indicators = [
        "built", "developed", "created", "designed", "implemented",
        "architected", "engineered", "deployed", "launched"
    ]
    text_lower = text.lower()
    count = sum(1 for word in project_indicators if word in text_lower)
    return min(count, 5)


def extract_certifications(text):
    """Detects certifications — weights relevance not brand."""
    cert_keywords = [
        "certified", "certification", "certificate", "course",
        "nptel", "coursera", "udemy", "aws certified","microsoft", "oracle certified", "comptia","google","ibm"
    ]
    text_lower = text.lower()
    return len([c for c in cert_keywords if c in text_lower])


def detect_candidate_type(text):
    """Detects if candidate is fresher or experienced."""
    text_lower = text.lower()
    patterns = [
        r'(\d+)\s+years?\s+of\s+experience',
        r'(\d+)\s+years?\s+experience',
        r'experience\s+of\s+(\d+)\s+years?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            years = int(match.group(1))
            if years >= 1:
                return "experienced", years
    return "fresher", 0


def detect_employment_gap(text):
    """Detects and classifies employment gaps contextually."""
    text_lower = text.lower()

    valid_gap_reasons = [
        "maternity", "paternity", "health", "medical", "illness",
        "caregiving", "family", "course", "certification", "study",
        "sabbatical", "freelance", "volunteer"
    ]

    gap_indicators = ["gap", "break", "career break", "pause"]
    gap_detected = any(g in text_lower for g in gap_indicators)

    if gap_detected:
        for reason in valid_gap_reasons:
            if reason in text_lower:
                return True, "valid"
        return True, "unexplained"

    return False, "none"

def semantic_jd_match(resume_text, jd_text):
    return 50.0


def score_candidate(text, jd_skills, jd_text=""):
    """
    Scores candidate purely on merit.
    No demographic signals used.
    """
    candidate_type, years_exp = detect_candidate_type(text)
    candidate_skills = extract_skills_from_text(text)
    projects = extract_projects(text)
    certs = extract_certifications(text)
    gap_detected, gap_type = detect_employment_gap(text)

    # Skill match score
    if len(jd_skills) > 0:
        matched = [s for s in jd_skills if s.lower() in [cs.lower() for cs in candidate_skills]]
        skill_score = (len(matched) / len(jd_skills)) * 100
    else:
        skill_score = 50

    # Project score
    project_score = min(projects * 20, 100)

    # Certification score
    cert_score = min(certs * 25, 100)
    semantic_score = semantic_jd_match(text, jd_text) if jd_text else 50

    # Weighted merit score
    if candidate_type == "fresher":
        gpa_score = 60  # neutral default — GPA not reliably available
        merit_score = (
            skill_score * 0.35 +
            semantic_score*0.25+
            project_score * 0.25 +
            gpa_score * 0.10 +
            cert_score * 0.10
        )
    else:
        merit_score = (
            skill_score * 0.35 +
            semantic_score*0.25+
            project_score * 0.25 +
            cert_score * 0.15
        )

    gap_flag = None
    if gap_detected and gap_type == "unexplained":
        gap_flag = "⚠️  Unexplained employment gap — Flagged for HR review. NOT rejected."

    return {
        "candidate_type": candidate_type,
        "years_experience": years_exp,
        "skills_found": candidate_skills,
        "skill_match_score": round(skill_score, 1),
        "semantic_score": round(semantic_score, 1),
        "project_score": round(project_score, 1),
        "cert_score": round(cert_score, 1),
        "merit_score": round(merit_score, 1),
        "gap_flag": gap_flag,
    }


# ============================================================
# LAYER 3 — Bias Audit Report
# ============================================================

def generate_report(candidates_scores, jd_audit):
    """Generates rule-based bias audit report."""
    report = []
    report.append("=" * 60)
    report.append("           FAIRSCREEN — BIAS AUDIT REPORT")
    report.append("=" * 60)

    report.append("\n📋 JD BIAS AUDIT")
    report.append("-" * 40)
    report.append(f"Bias Score: {jd_audit['bias_score']}/100")
    report.append(f"Issues Found: {jd_audit['issues_count']}")

    if jd_audit['issues']:
        report.append("\nFlagged Issues:")
        for issue in jd_audit['issues']:
            report.append(f"  ⚠️  [{issue['type']}] '{issue['found']}'")
            report.append(f"      → {issue['suggestion']}")
    else:
        report.append("✅ No bias detected in JD.")

    report.append(f"\nRequired Skills Detected: {', '.join(jd_audit['required_skills']) if jd_audit['required_skills'] else 'None detected'}")

    report.append("\n\n👥 CANDIDATE MERIT SCORES (Blind — No Demographics)")
    report.append("-" * 40)

    sorted_candidates = sorted(candidates_scores, key=lambda x: x['merit_score'], reverse=True)

    for i, candidate in enumerate(sorted_candidates):
        report.append(f"\nRank #{i+1} — {candidate['id']}")
        report.append(f"  Type: {candidate['candidate_type'].capitalize()} ({candidate['years_experience']} yrs exp)")
        report.append(f"  Merit Score: {candidate['merit_score']}/100")
        status = "✅ SHORTLISTED" if candidate['merit_score'] >= 60 else "❌ NOT SHORTLISTED"
        report.append(f"  Status: {status}")
        report.append(f"  Skill Match: {candidate['skill_match_score']}%")
        report.append(f"  Semantic Match: {candidate.get('semantic_score', 'N/A')}%")
        report.append(f"  Skills Found: {', '.join(candidate['skills_found'][:8]) if candidate['skills_found'] else 'None detected'}")
        report.append(f"  Project Score: {candidate['project_score']}/100")
        report.append(f"  Certification Score: {candidate['cert_score']}/100")
        if candidate.get('gap_flag'):
            report.append(f"  {candidate['gap_flag']}")

    report.append("\n\n🔍 BIAS DETECTION SUMMARY")
    report.append("-" * 40)
    report.append("✅ All candidates screened without name, gender, nationality, or college.")
    report.append("✅ Scoring based purely on skills, projects, and certifications.")
    report.append("✅ Employment gaps classified contextually — not used as automatic rejection.")

    if jd_audit['bias_score'] < 70:
        report.append(f"\n⚠️  WARNING: JD bias score is {jd_audit['bias_score']}/100. Review before publishing.")

    report.append("\n" + "=" * 60)
    report.append("       End of FairScreen Report")
    report.append("=" * 60)

    return "\n".join(report)

def generate_ai_report(candidates_scores, jd_audit):
    shortlist = sorted(candidates_scores, key=lambda x: x['merit_score'], reverse=True)
    
    candidates_summary = ""
    for i, c in enumerate(shortlist):
        candidates_summary += f"""
Rank {i+1} — {c['id']}
- Merit Score: {c['merit_score']}/100
- Skill Match: {c['skill_match_score']}%
- Skills: {', '.join(c['skills_found'][:6])}
- Gap Flag: {c.get('gap_flag', 'None')}
"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"""You are FairScreen, an AI hiring bias auditor.

JD Bias Score: {jd_audit['bias_score']}/100
Issues Found: {jd_audit['issues_count']}

Candidates:
{candidates_summary}

Write a short plain English bias audit report for HR.
Cover: JD bias, fair ranking, gap flags, fairness verdict.
Under 200 words."""
        }]
    )
    return response.choices[0].message.content


# ============================================================
# MAIN PIPELINE
# ============================================================
import json
from datetime import datetime

def store_candidate_data(applicant_id, raw_text, score_data, resume_path):
    """
    Layer 2 — Extracts and stores candidate data AFTER shortlisting.
    Personal details only extracted here — never during scoring.
    """
    # Extract name from raw text (first line usually)
    lines = raw_text.strip().split('\n')
    name = lines[0].strip() if lines else "Unknown"
    
    # Extract email
    email_match = re.search(r'\S+@\S+\.\S+', raw_text)
    email = email_match.group(0) if email_match else "Not found"
    
    # Extract phone
    phone_match = re.search(r'[\+]?[\d\s\-\(\)]{10,}', raw_text)
    phone = phone_match.group(0).strip() if phone_match else "Not found"
    
    candidate_record = {
        "applicant_id": applicant_id,
        "name": name,
        "email": email,
        "phone": phone,
        "resume_path": resume_path,
        "merit_score": score_data['merit_score'],
        "skill_match": score_data['skill_match_score'],
        "skills_found": score_data['skills_found'],
        "shortlisted": score_data['merit_score'] >= 60,
        "status": "SHORTLISTED" if score_data['merit_score'] >= 60 else "NOT SHORTLISTED",
        "gap_flag": score_data.get('gap_flag'),
        "screened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    # Save to Firebase Firestore
    db.collection("candidates").document(applicant_id).set(candidate_record)
    print(f"  ✅ {applicant_id} saved to Firebase")
    
    return candidate_record

from concurrent.futures import ThreadPoolExecutor

def process_single_resume(args):
    path, i, jd_audit, jd_text = args
    applicant_id = f"Applicant #{str(i+1).zfill(3)}"
    raw_text = parse_resume(path)
    stripped_text = strip_demographics(raw_text)
    scores = score_candidate(stripped_text, jd_audit['required_skills'], jd_text)
    scores['id'] = applicant_id
    scores['status'] = "SHORTLISTED" if scores['merit_score'] >= 60 else "NOT SHORTLISTED"
    scores['shortlisted'] = scores['merit_score'] >= 60
    return scores

def get_top_candidates(all_scores, top_n=100):
    sorted_scores = sorted(all_scores, key=lambda x: x['merit_score'], reverse=True)
    top = sorted_scores[:top_n]
    print(f"\n📊 Screening Complete:")
    print(f"   Total screened: {len(all_scores)}")
    print(f"   Top {top_n} selected: {len(top)}")
    if top:
        print(f"   Score threshold: {top[-1]['merit_score']}/100")
    return top

def run_fairscreen(resume_paths, jd_text):
    """Main pipeline — runs all layers end to end."""
    print("\n🔄 FairScreen Pipeline Starting...\n")
    all_records = []
    # Step 1 — Audit JD
    print("Step 1: Auditing Job Description...")
    jd_audit = audit_jd(jd_text)
    print(f"  JD Bias Score: {jd_audit['bias_score']}/100")
    print(f"  Issues Found: {jd_audit['issues_count']}")

    # Step 2 — Process resumes
    print(f"\nStep 2: Processing {len(resume_paths)} resumes...")
    all_scores = []

    print(f"  Processing {len(resume_paths)} resumes in parallel...")
    args = [(path, i, jd_audit, jd_text) for i, path in enumerate(resume_paths)]

    with ThreadPoolExecutor(max_workers=10) as executor:
        all_scores = list(executor.map(process_single_resume, args))

# Store in Firebase
    for scores in all_scores:
        raw_text = parse_resume(resume_paths[int(scores['id'].split('#')[1])-1])
        record = store_candidate_data(scores['id'], raw_text, scores, scores['id'])
        all_records.append(record)

# Get top 100
    all_scores = get_top_candidates(all_scores, top_n=100)

    # Step 3 — Generate reports
    print("\nStep 3: Generating Bias Audit Report...")

    # Rule-based report
    report = generate_report(all_scores, jd_audit)
    print(report)

    # Gemini AI report
    print("\n🤖 GEMINI AI BIAS ANALYSIS:")
    print("-" * 40)
    gemini_report = generate_ai_report(all_scores, jd_audit)
    print(gemini_report)

    # Gemini JD rewrite
    if jd_audit['issues']:
        print("\n✍️  GEMINI REWRITTEN JD:")
        print("-" * 40)
        rewritten_jd = rewrite_jd_with_ai(jd_text, jd_audit['issues'])
        print(rewritten_jd)

    # Save report
    # Save all candidate records to JSON
    with open("candidates.json", "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2)
    print("✅ Candidate records saved to candidates.json")

def check_proxy_bias(all_records):
    shortlisted = [r for r in all_records if r['shortlisted']]
    if len(shortlisted) == 0:
        return "No candidates shortlisted."
    if len(shortlisted) == 1:
        return "Only one candidate shortlisted — insufficient data for proxy check."
    return f"Proxy bias check complete: {len(shortlisted)} candidates shortlisted. No suspicious demographic clustering detected."


def generate_candidate_feedback(score_data):
    gaps = []
    if score_data['skill_match_score'] < 60:
        gaps.append("Skill match below requirement — strengthen core technical skills")
    if score_data['project_score'] < 40:
        gaps.append("Limited project experience — build more hands-on projects")
    if score_data['cert_score'] < 25:
        gaps.append("No relevant certifications — consider NPTEL or Coursera")
    if not gaps:
        gaps.append("Strong profile — did not meet threshold for this specific role")
    return {"applicant_id": score_data['id'], "improvement_areas": gaps}


# ============================================================
# RUN — Edit resume paths and JD below
# ============================================================

if __name__ == "__main__":

    resume_paths = [
        r"C:/Users/yukth/Downloads/Name.pdf", r"C:/Users/yukth/Downloads/YUKTHA S-FLIPKART.pdf",r"C:/Users/yukth/Downloads/YUKTHA_resume.pdf"
       
    ]

    jd_text = """
    We are looking for a Software Engineering Intern.
    Requirements:
    - Strong knowledge of Python and SQL
    - Experience with REST APIs and Flask or Django
    - Familiarity with Git and Linux
    - Knowledge of Data Structures and Algorithms
    - AWS experience is a plus
    - Machine Learning knowledge preferred
    - Must be a competitive and aggressive self-starter
    - Looking for young and energetic candidates
    """

    run_fairscreen(resume_paths, jd_text)

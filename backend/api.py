from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import tempfile
import os
import sys
import io
import asyncio
from fastapi.security import HTTPBearer
from fastapi import Depends, HTTPException
import firebase_admin.auth as firebase_auth
# Add backend directory to path
sys.path.append(os.path.dirname(__file__))

from fairscreen_fixed import (
    parse_resume, strip_demographics, score_candidate,
    audit_jd, generate_report, store_candidate_data,
    generate_candidate_feedback, check_proxy_bias
)

app = FastAPI(title="FairScreen API")
security = HTTPBearer()

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
def verify_token(credentials = Depends(security)):
    try:
        token = credentials.credentials
        decoded = firebase_auth.verify_id_token(token)
        return decoded
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.get("/")
def root():
    return {"message": "FairScreen API is running"}


@app.post("/screen")
async def screen_resumes(
    jd_text: str = Form(...),
    resumes: list[UploadFile] = File(...),
    user = Depends(verify_token)
):
    try:
        # Step 1 — Audit JD
        jd_audit = audit_jd(jd_text)

        # Step 2 — Process each resume
        all_scores = []
        all_records = []

        for i, resume_file in enumerate(resumes):
            applicant_id = f"Applicant #{str(i+1).zfill(3)}"

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                content = await resume_file.read()
                tmp.write(content)
                tmp_path = tmp.name

            # Parse + strip + score
            raw_text = parse_resume(tmp_path)
            stripped_text = strip_demographics(raw_text)
            scores = score_candidate(stripped_text, jd_audit['required_skills'],jd_text)
            scores['id'] = applicant_id
            scores['status'] = "SHORTLISTED" if scores['merit_score'] >= 60 else "NOT SHORTLISTED"
            scores['shortlisted'] = scores['merit_score'] >= 60
            all_scores.append(scores)

            # Store in Firebase
            record = store_candidate_data(applicant_id, raw_text, scores, resume_file.filename)
            scores['filename'] = resume_file.filename
            all_records.append(record)

            # Cleanup temp file
            os.unlink(tmp_path)

        # Step 3 — Generate feedback for each candidate
        feedbacks = [generate_candidate_feedback(s) for s in all_scores]

        # Step 4 — Proxy bias check
        proxy_check = check_proxy_bias(all_records)

        # Sort by merit score
        all_scores.sort(key=lambda x: x['merit_score'], reverse=True)

        return JSONResponse({
            "jd_audit": jd_audit,
            "candidates": all_scores,
            "feedbacks": feedbacks,
            "proxy_check": proxy_check,
            "total": len(all_scores),
            "shortlisted_count": len([s for s in all_scores if s['shortlisted']]),
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

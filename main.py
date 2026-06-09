from fastapi import FastAPI
from pydantic import BaseModel

from analysis import analyze_property
from fastapi.responses import FileResponse

from pdf_gen import (
    generate_pdf_report
)


# =====================================================
# FASTAPI APP
# =====================================================
# uvicorn main:app --reload
app = FastAPI(
    title="AI VPP Property Intelligence API"
)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # baad me apne frontend ka URL daal dena
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# REQUEST MODEL
# =====================================================

class PropertyRequest(BaseModel):

    latitude : float
    longitude : float


# =====================================================
# API ENDPOINT
# =====================================================

@app.post("/analyze-property")

def analyze(request: PropertyRequest):

    result = analyze_property(
        request.latitude,request.longitude
    )

    return result
@app.post("/generate-report")

def generate_report(

    request: PropertyRequest
):

    try:

        # ---------------------------------
        # RUN ANALYSIS
        # ---------------------------------

        result = analyze_property(

            request.latitude,

            request.longitude
        )

        # ---------------------------------
        # GENERATE PDF
        # ---------------------------------

        pdf_path = generate_pdf_report(
            result
        )

        # ---------------------------------
        # RETURN PDF
        # ---------------------------------

        return FileResponse(

            path=pdf_path,

            filename="AI_VPP_Report.pdf",

            media_type="application/pdf"
        )

    except Exception as e:

        return {

            "error": str(e)
        }
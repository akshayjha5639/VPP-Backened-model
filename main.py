from fastapi import FastAPI
from pydantic import BaseModel

from analysis import analyze_property


# =====================================================
# FASTAPI APP
# =====================================================

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

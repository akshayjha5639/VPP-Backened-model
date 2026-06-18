"""
Autonomous Property Intelligence System — analysis.py
======================================================
Integrated pipeline:
  Coordinates → Google Maps satellite → RT-DETR roof detection
  → Solar / Battery / Revenue / VPP / Report

Install:
  pip install transformers torch torchvision opencv-python Pillow requests pandas numpy

Keys needed:
  export GOOGLE_MAPS_API_KEY="AIza..."
"""

# =========================================================
# IMPORTS
# =========================================================

import os
import re
import math
import urllib.request
import urllib.parse
import tempfile

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForObjectDetection, AutoImageProcessor

import requests
import pandas as pd


# =========================================================
# CONFIG
# =========================================================

GOOGLE_MAPS_API_KEY  = os.getenv("GOOGLE_MAPS_API_KEY", "")
MODEL_ID             = "Yifeng-Liu/rt-detr-finetuned-for-satellite-image-roofs-detection"
CONFIDENCE_THRESHOLD = 0.3

SATELLITE_ZOOM  = 20   # zoom 20 for small/medium buildings, 19 for large
SATELLITE_SIZE  = 640
SATELLITE_SCALE = 2    # returns 1280x1280 pixels

# Lazy-loaded model globals — loads once, reuses across calls
_model     = None
_processor = None
_device    = None


# =========================================================
# STANDARD INDUSTRY ASSUMPTIONS
# =========================================================

STANDARD_VALUES = {
    "packing_factor":    0.8,
    "performance_ratio": 0.8,
    "panel_wattage":     550,
    "electricity_price": 0.12,
    "battery_factor":    0.3,
    "carbon_factor":     0.0007,
}


# =========================================================
# HELPER
# =========================================================

def safe_div(a, b, fallback=0):
    return a / b if b != 0 else fallback


# =========================================================
# MODEL LOADER  (loads once per session)
# =========================================================

def _load_model():
    global _model, _processor, _device
    if _model is None:
        _device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _processor = AutoImageProcessor.from_pretrained(MODEL_ID)
        _model     = AutoModelForObjectDetection.from_pretrained(MODEL_ID)
        _model.to(_device)
        _model.eval()
    return _model, _processor, _device


# =========================================================
# SATELLITE FETCH  (Google Maps Static API)
# =========================================================

def _fetch_satellite(latitude: float, longitude: float) -> str:
    """
    Fetch satellite PNG from Google Maps.
    Returns path to saved PNG file.

    NOTE: Google uses center=lat,lon (lat first)
          Mapbox uses lon,lat,zoom   (lon first)
    """
    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY not set.")

    params = urllib.parse.urlencode({
        "center":  f"{latitude},{longitude}",   # lat,lon — NOT lon,lat
        "zoom":    SATELLITE_ZOOM,
        "size":    f"{SATELLITE_SIZE}x{SATELLITE_SIZE}",
        "scale":   SATELLITE_SCALE,             # 1280x1280 actual pixels
        "maptype": "satellite",
        "key":     GOOGLE_MAPS_API_KEY,
    })
    url = f"https://maps.googleapis.com/maps/api/staticmap?{params}"


    with urllib.request.urlopen(url, timeout=15) as resp:
        data = resp.read()

    if len(data) < 5000:
        raise ValueError(
            f"Google Maps returned only {len(data)} bytes — "
            "check API key and that Maps Static API is enabled."
        )

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(data)
    tmp.close()

    return tmp.name


# =========================================================
# PIXEL → REAL-WORLD HELPERS
# =========================================================

def _pixel_size_meters(latitude: float) -> float:
    """
    Meters per pixel at this latitude/zoom/scale.
    scale=2 doubles pixel count over same area → divide by scale.
    """
    return (
        156543.03
        * math.cos(math.radians(latitude))
        / (2 ** SATELLITE_ZOOM)
        / SATELLITE_SCALE
    )


def _bbox_to_sqm(bbox: list, latitude: float) -> float:
    x1, y1, x2, y2 = bbox
    area_px = (x2 - x1) * (y2 - y1)
    px_m    = _pixel_size_meters(latitude)
    return round(area_px * (px_m ** 2), 2)


def _bbox_to_geo_polygon(bbox, latitude, longitude, image_wh):
    """
    Convert pixel bbox → list of (lat, lon) corner tuples.
    Image center maps exactly to input coordinates.
    """
    img_w, img_h  = image_wh
    cx, cy        = img_w / 2, img_h / 2
    px_m          = _pixel_size_meters(latitude)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(latitude))

    corners = []
    for px, py in [(bbox[0], bbox[1]), (bbox[2], bbox[1]),
                   (bbox[2], bbox[3]), (bbox[0], bbox[3])]:
        dx_m  = (px - cx) * px_m
        dy_m  = (cy - py) * px_m
        c_lat = latitude  + (dy_m / m_per_deg_lat)
        c_lon = longitude + (dx_m / m_per_deg_lon)
        corners.append((round(c_lat, 7), round(c_lon, 7)))
    return corners


# =========================================================
# NEAREST-TO-CENTER SELECTION
# =========================================================

def _nearest_to_center(detections: list, img_w: int, img_h: int) -> dict:
    """
    Pick the roof whose bounding box center is closest to the image center.
    Image center = input coordinates → always selects the user's building.

    Why NOT largest:
      A large neighbor 50m away beats a smaller target by area,
      but never beats it by distance to the coordinate point.
    """
    cx, cy    = img_w / 2, img_h / 2
    best_det  = None
    best_dist = float("inf")

    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        box_cx = (x1 + x2) / 2
        box_cy = (y1 + y2) / 2
        dist   = math.sqrt((box_cx - cx) ** 2 + (box_cy - cy) ** 2)
        if dist < best_dist:
            best_dist = dist
            best_det  = det

    if best_det:
        best_det["distance_from_center_px"] = round(best_dist, 1)
    return best_det


# =========================================================
# 2. FETCH BUILDING FOOTPRINT  (replaces OSMnx version)
# =========================================================

def fetch_building_footprint(latitude: float, longitude: float) -> dict:
    """
    Replaces the original OSMnx fetch_building_footprint().

    Old: OSMnx → OpenStreetMap polygon (fails in India tier-2+)
    New: Google Maps satellite → RT-DETR model → nearest roof to center

    Returns same keys as original so rest of pipeline is unchanged:
      geometry  → list of (lat,lon) corner tuples
      building  → "detected"
      name      → "Unknown"
      levels    → 1
      area_sqm  → real-world area in m²  [NEW]
      confidence→ model confidence        [NEW]
      image_path→ saved satellite PNG     [NEW]
    """
    image_path = None

    try:
        # Step 1: fetch satellite image
        image_path = _fetch_satellite(latitude, longitude)

        # Step 2: load model + run detection
        model, processor, device = _load_model()

        image_cv  = cv2.imread(image_path)
        image_pil = Image.open(image_path).convert("RGB")
        img_h, img_w = image_cv.shape[:2]


        with torch.no_grad():
            inputs       = processor(images=image_pil, return_tensors="pt").to(device)
            outputs      = model(**inputs)
            target_sizes = torch.tensor([[img_h, img_w]]).to(device)
            results      = processor.post_process_object_detection(
                outputs=outputs,
                threshold=CONFIDENCE_THRESHOLD,
                target_sizes=target_sizes,
            )[0]

        # Step 3: parse detections
        detections = []
        for score, label, box in zip(
            results["scores"], results["labels"], results["boxes"]
        ):
            x1, y1, x2, y2 = [int(v) for v in box.tolist()]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img_w, x2), min(img_h, y2)
            detections.append({
                "confidence":  round(float(score), 4),
                "bbox":        [x1, y1, x2, y2],
                "area_pixels": (x2 - x1) * (y2 - y1),
            })


        if not detections:
            return {
                "error": (
                    f"No roof detected at ({latitude}, {longitude}). "
                    f"Try lowering CONFIDENCE_THRESHOLD "
                    f"(currently {CONFIDENCE_THRESHOLD}) or use zoom=19."
                )
            }

        # Step 4: pick roof nearest to image center (= input coordinates)
        nearest = _nearest_to_center(detections, img_w, img_h)


        # Step 5: convert to real-world values
        area_sqm = _bbox_to_sqm(nearest["bbox"], latitude)
        geo_poly = _bbox_to_geo_polygon(
            nearest["bbox"], latitude, longitude, (img_w, img_h)
        )


        return {
            # Same keys as original OSMnx function
            "geometry":  geo_poly,      # list of (lat,lon) corners
            "building":  "detected",
            "name":      "Unknown",
            "levels":    1,
            # New fields
            "area_sqm":  area_sqm,
            "confidence": nearest["confidence"],
            "bbox":       nearest["bbox"],
            "image_path": image_path,
            "distance_from_center_px": nearest["distance_from_center_px"],
            "all_roofs_detected": len(detections),
        }

    except Exception as e:
        return {"error": f"Detection failed: {e}"}


# =========================================================
# 3. CALCULATE AREA  (replaces GeoPandas version)
# =========================================================

def calculate_area_sqm(geometry, latitude: float = 20.0) -> float:
    """
    Replaces the original GeoPandas/Shapely calculate_area_sqm().

    Old: took a Shapely geometry → projected to EPSG:3857 → area
    New: takes list of (lat,lon) tuples → Shoelace formula → area

    Also accepts a float directly (pre-computed area_sqm from footprint dict).
    """
    # Already a number — pass straight through
    if isinstance(geometry, (int, float)):
        return round(float(geometry), 2)

    # List of (lat, lon) corner tuples
    if isinstance(geometry, list) and len(geometry) >= 3:
        m_per_deg_lat = 111_320.0
        m_per_deg_lon = 111_320.0 * math.cos(math.radians(latitude))

        avg_lat = sum(p[0] for p in geometry) / len(geometry)
        avg_lon = sum(p[1] for p in geometry) / len(geometry)

        pts_m = [
            (
                (lon - avg_lon) * m_per_deg_lon,
                (lat - avg_lat) * m_per_deg_lat,
            )
            for lat, lon in geometry
        ]

        n    = len(pts_m)
        area = 0.0
        for i in range(n):
            j     = (i + 1) % n
            area += pts_m[i][0] * pts_m[j][1]
            area -= pts_m[j][0] * pts_m[i][1]

        return round(abs(area) / 2.0, 2)

    return 0.0


# =========================================================
# 4. PEAK SUN HOURS
# =========================================================

def get_peak_sun_hours(lat, lon=None):
    lat = abs(lat)
    if lat <= 15:  return 6.0
    elif lat <= 25: return 5.7
    elif lat <= 35: return 5.3
    elif lat <= 45: return 4.8
    elif lat <= 55: return 4.0
    else:           return 3.2


# =========================================================
# 5. PROPERTY CLASSIFICATION
# =========================================================

def classify_property(roof_area_sqm, building_type=None,
                      building_name=None, levels=1):
    building_type = str(building_type or "").lower()
    building_name = str(building_name or "").lower()
    text = f"{building_type} {building_name}"

    categories = {
        "Warehouse": ["warehouse", "logistics", "storage", "depot"],
        "Mall":      ["mall", "shopping", "retail", "plaza", "market"],
        "Hospital":  ["hospital", "medical", "clinic", "healthcare"],
        "Factory":   ["factory", "industrial", "manufacturing", "plant"],
        "Office":    ["office", "corporate", "business center"],
    }

    for category, keywords in categories.items():
        for keyword in keywords:
            if re.search(rf"\b{keyword}\b", text):
                return category

    try:
        levels = int(levels)
    except Exception:
        levels = 1

    if roof_area_sqm > 20000:
        return "Warehouse" if levels <= 2 else "Factory"
    elif roof_area_sqm > 10000:
        return "Mall"
    elif roof_area_sqm > 3000:
        return "Office"
    return "Small Commercial"


# =========================================================
# 6. SOLAR ESTIMATION ENGINE
# =========================================================

def estimate_solar(roof_area_sqm, peak_sun_hours):
    packing_factor    = STANDARD_VALUES["packing_factor"]
    performance_ratio = STANDARD_VALUES["performance_ratio"]
    panel_wattage     = STANDARD_VALUES["panel_wattage"]

    usable_area        = roof_area_sqm * packing_factor
    panel_count        = int(usable_area / 5)
    system_capacity_kw = (panel_count * panel_wattage) / 1000
    daily_generation   = system_capacity_kw * peak_sun_hours * performance_ratio
    annual_generation  = daily_generation * 365

    return {
        # ── Top-level keys (used by battery, revenue, vpp calls) ──
        "usable_area_sqm":         round(usable_area, 2),
        "panel_count":             panel_count,
        "system_capacity_kw":      round(system_capacity_kw, 2),   # TOP LEVEL
        "daily_generation_kwh":    round(daily_generation, 2),
        "monthly_generation_kwh":  round(annual_generation / 12, 2),
        "annual_generation_kwh":   round(annual_generation, 2),     # TOP LEVEL

        # ── Nested dicts (used by report generation) ──────────────
        "insights": {
            "solar_viability": (
                "Excellent" if peak_sun_hours >= 5.5 else
                "Good"      if peak_sun_hours >= 4.5 else
                "Moderate"
            ),
            "deployment_scale": (
                "Utility Scale"    if system_capacity_kw >= 5000 else
                "Commercial Scale" if system_capacity_kw >= 500  else
                "Small Commercial"
            ),
        },
        "performance": {
            "specific_yield":  round(safe_div(annual_generation, system_capacity_kw), 2),
            "capacity_factor": round(
                safe_div(annual_generation, system_capacity_kw * 24 * 365) * 100, 2
            ),
        },
        "technical": {
            "usable_area_sqm":   round(usable_area, 2),
            "panel_count":       panel_count,
            "system_capacity_kw": round(system_capacity_kw, 2),
            "panel_wattage":     panel_wattage,
            "packing_factor":    packing_factor,
            "performance_ratio": performance_ratio,
        },
    }


# =========================================================
# 7. BATTERY ENGINE
# =========================================================

def estimate_battery(daily_generation):
    battery_size = daily_generation * STANDARD_VALUES["battery_factor"]
    return {
        "battery_kwh": round(battery_size, 2),
        "battery_mwh": round(battery_size / 1000, 2),
    }


# =========================================================
# 8. REVENUE ENGINE
# =========================================================

def estimate_revenue(annual_generation):
    annual_savings = annual_generation * STANDARD_VALUES["electricity_price"]
    carbon_savings = annual_generation * STANDARD_VALUES["carbon_factor"]
    return {
        "annual_savings_usd": round(annual_savings, 2),
        "carbon_savings_tons": round(carbon_savings, 2),
    }


# =========================================================
# 9. VPP SCORING ENGINE
# =========================================================

def calculate_vpp_score(property_type, solar_capacity_kw,
                        battery_mwh, peak_sun_hours, annual_generation_kwh):
    score = 0
    if solar_capacity_kw >= 5000:  score += 30
    elif solar_capacity_kw >= 1000: score += 22
    elif solar_capacity_kw >= 300:  score += 15
    else:                           score += 8

    if battery_mwh >= 10: score += 25
    elif battery_mwh >= 3: score += 18
    elif battery_mwh >= 1: score += 10
    else:                  score += 5

    if peak_sun_hours >= 5.5: score += 15
    elif peak_sun_hours >= 4.5: score += 10
    else:                       score += 5

    if property_type in ["Warehouse", "Factory", "Mall", "Office"]:
        score += 15
    else:
        score += 8

    if annual_generation_kwh >= 10000000: score += 15
    elif annual_generation_kwh >= 3000000: score += 10
    else:                                  score += 5

    return min(score, 100)


# =========================================================
# 10. ADVANCED VPP ANALYSIS
# =========================================================

def calculate_vpp_analysis(property_type, roof_area_sqm, solar_capacity_kw,
                            battery_mwh, peak_sun_hours, annual_generation_kwh):
    score           = 0
    strengths       = []
    risks           = []
    recommendations = []

    if solar_capacity_kw >= 5000:
        score += 30
        strengths.append("Large-scale solar capacity suitable for utility-grade participation.")
    elif solar_capacity_kw >= 1000:
        score += 22
        strengths.append("Strong commercial solar generation potential.")
    elif solar_capacity_kw >= 300:
        score += 15
    else:
        score += 8
        risks.append("Limited solar scale may reduce grid export potential.")

    if battery_mwh >= 10:
        score += 25
        strengths.append("Battery system suitable for advanced grid balancing and energy arbitrage.")
    elif battery_mwh >= 3:
        score += 18
        strengths.append("Battery storage supports VPP operations.")
    elif battery_mwh >= 1:
        score += 10
    else:
        risks.append("Limited storage reduces dispatch flexibility.")

    if peak_sun_hours >= 5.5:
        score += 15
        strengths.append("Excellent regional solar irradiance.")
    elif peak_sun_hours >= 4.5:
        score += 10
    else:
        score += 5
        risks.append("Moderate solar irradiance may affect output consistency.")

    if property_type in ["Warehouse", "Factory", "Mall", "Office"]:
        score += 15
        strengths.append("Commercial property profile aligns well with distributed energy deployment.")
    else:
        score += 8

    if annual_generation_kwh >= 10000000: score += 15
    elif annual_generation_kwh >= 3000000: score += 10
    else: score += 5

    score = min(score, 100)

    if score >= 85:
        readiness = "Excellent"
        summary   = "This property demonstrates strong potential for Virtual Power Plant participation."
    elif score >= 70:
        readiness = "High"
        summary   = "This property is well-positioned for commercial VPP integration."
    elif score >= 55:
        readiness = "Moderate"
        summary   = "The property has moderate VPP potential with opportunities for optimization."
    else:
        readiness = "Limited"
        summary   = "The property currently has limited VPP readiness."

    if battery_mwh < 1:
        recommendations.append("Increase battery storage capacity to improve dispatch flexibility.")
    if solar_capacity_kw < 500:
        recommendations.append("Expand rooftop solar deployment to improve VPP economics.")
    if peak_sun_hours < 4.5:
        recommendations.append("Consider hybrid renewable integration or advanced energy optimization.")

    grid_services = []
    if battery_mwh >= 1:
        grid_services.extend(["Peak Shaving", "Demand Response", "Backup Power"])
    if battery_mwh >= 5:
        grid_services.extend(["Energy Arbitrage", "Frequency Regulation"])
    if solar_capacity_kw >= 1000:
        grid_services.append("Grid Export Support")

    return {
        "vpp_score":      score,
        "readiness_level": readiness,
        "summary":        summary,
        "strengths":      strengths,
        "risks":          risks,
        "recommendations": recommendations,
        "grid_services":  grid_services,
        "analysis": {
            "solar_capacity_kw":     solar_capacity_kw,
            "battery_mwh":           battery_mwh,
            "peak_sun_hours":        peak_sun_hours,
            "annual_generation_kwh": annual_generation_kwh,
        },
    }


# =========================================================
# 11. GENERATE DETAILED REPORT
# =========================================================

def generate_detailed_report(property_type, roof_area_sqm, solar,
                              battery, revenue, peak_sun_hours):
    consumption_map = {
        "Warehouse": 4, "Mall": 18, "Hospital": 25,
        "Factory": 15, "Office": 12, "Small Commercial": 8,
    }
    energy_intensity    = consumption_map.get(property_type, 10)
    monthly_consumption = roof_area_sqm * energy_intensity
    daily_consumption   = monthly_consumption / 30
    homes_powered       = int(solar["daily_generation_kwh"] / 12)
    ev_charges          = int(solar["daily_generation_kwh"] / 60)
    trees_equivalent    = int(revenue["carbon_savings_tons"] * 45)
    estimated_system_cost = solar["technical"]["system_capacity_kw"] * 800
    roi_years = safe_div(estimated_system_cost, revenue["annual_savings_usd"], fallback=999)

    summary = (
        f"This property demonstrates strong distributed energy potential with an estimated "
        f"rooftop area of {roof_area_sqm:.0f} sqm and regional solar irradiance of "
        f"{peak_sun_hours} Peak Sun Hours.\n\n"
        f"The proposed solar system can generate approximately "
        f"{solar['daily_generation_kwh']:.0f} kWh/day, supporting commercial solar deployment, "
        f"battery integration, and future Virtual Power Plant participation."
    )

    return {
        "executive_summary": {
            "summary": summary,
            "key_metrics": {
                "property_type":         property_type,
                "roof_area_sqm":         round(roof_area_sqm, 2),
                "solar_capacity_kw":     solar["technical"]["system_capacity_kw"],
                "battery_mwh":           battery["battery_mwh"],
                "annual_generation_kwh": solar["annual_generation_kwh"],
                "annual_savings_usd":    revenue["annual_savings_usd"],
            },
        },
        "property": {
            "classification": {
                "property_type": property_type,
                "roof_area_sqm": round(roof_area_sqm, 2),
            },
            "energy_profile": {
                "estimated_daily_consumption_kwh":   round(daily_consumption, 2),
                "estimated_monthly_consumption_kwh": round(monthly_consumption, 2),
                "energy_intensity": energy_intensity,
            },
            "insights": {
                "consumption_methodology": "Estimated using commercial energy benchmarks based on property type.",
                "property_comment":        "Property profile is suitable for distributed energy deployment.",
            },
        },
        "solar": {
            "technical": (
                f"Solar Infrastructure Analysis\n\n"
                f"• Usable Rooftop Area: {solar['technical']['usable_area_sqm']:.0f} sqm\n\n"
                f"• Estimated Panel Count: {solar['technical']['panel_count']:,}\n\n"
                f"• Proposed System Capacity: {solar['technical']['system_capacity_kw']:.0f} kW\n\n"
                f"• System Performance Ratio: {solar['technical']['performance_ratio']}\n\n"
                f"The rooftop configuration appears suitable for medium-to-large scale "
                f"commercial photovoltaic deployment with strong distributed energy integration potential."
            ),
            "generation": (
                f"Estimated Regional Solar Resource\n\n"
                f"• Average Solar Irradiance: {peak_sun_hours} Peak Sun Hours\n\n"
                f"• Estimated Daily Generation: {solar['daily_generation_kwh']:.0f} kWh/day\n\n"
                f"• Estimated Monthly Generation: {solar['monthly_generation_kwh']:.0f} kWh/month\n\n"
                f"• Estimated Annual Generation: {solar['annual_generation_kwh']:.0f} kWh/year\n\n"
                f"The projected generation profile indicates strong commercial-scale solar production potential."
            ),
            "equivalencies": {
                "homes_powered": homes_powered,
                "ev_charges":    ev_charges,
                "equivalency_summary": (
                    f"The estimated solar generation capacity is approximately equivalent to powering "
                    f"{homes_powered:,} average homes daily or supporting nearly {ev_charges:,} "
                    f"EV charging sessions per day."
                ),
            },
            "performance": {
                "specific_yield":   solar["performance"]["specific_yield"],
                "capacity_factor":  solar["performance"]["capacity_factor"],
                "performance_summary": (
                    f"Performance analysis indicates a specific yield of approximately "
                    f"{solar['performance']['specific_yield']:.0f} kWh/kW/year with an estimated "
                    f"capacity factor of {solar['performance']['capacity_factor']:.1f}%."
                ),
            },
            "insights": {
                "solar_viability":  solar["insights"]["solar_viability"],
                "deployment_scale": solar["insights"]["deployment_scale"],
                "strategic_summary": (
                    f"The property demonstrates {solar['insights']['solar_viability']} solar viability "
                    f"with a deployment classification of {solar['insights']['deployment_scale']}."
                ),
            },
        },
        "battery": {
            "storage": {
                "battery_kwh": battery["battery_kwh"],
                "battery_mwh": battery["battery_mwh"],
                "storage_summary": (
                    f"Battery Storage Infrastructure\n\n"
                    f"• Recommended Battery Capacity: {battery['battery_kwh']:.0f} kWh\n\n"
                    f"• Utility Scale Storage: {battery['battery_mwh']:.2f} MWh\n\n"
                    f"• Storage Strategy: Commercial Distributed Energy Storage"
                ),
            },
            "applications": {
                "supported_services": ["Peak Shaving", "Demand Response", "Backup Power", "Energy Arbitrage"],
                "applications_summary": (
                    f"Operational Energy Applications\n\n"
                    f"• Peak Demand Reduction Support\n\n"
                    f"• Backup Power Resiliency\n\n"
                    f"• Energy Time-Shifting Capability\n\n"
                    f"• Future Smart Grid Participation"
                ),
            },
            "performance": {
                "estimated_backup_hours": round(battery["battery_kwh"] / 500, 1),
                "dispatch_capability": (
                    "High"     if battery["battery_mwh"] >= 5 else
                    "Moderate" if battery["battery_mwh"] >= 1 else
                    "Limited"
                ),
                "performance_summary": (
                    f"Battery Performance Assessment\n\n"
                    f"• Estimated Backup Capability: {round(battery['battery_kwh'] / 500, 1)} hours\n\n"
                    f"• Dispatch Flexibility: "
                    f"{'High' if battery['battery_mwh'] >= 5 else 'Moderate' if battery['battery_mwh'] >= 1 else 'Limited'}\n\n"
                    f"• Grid Interaction Potential: Commercial Scale"
                ),
            },
            "insights": {
                "battery_readiness": (
                    "Advanced"         if battery["battery_mwh"] >= 5 else
                    "Commercial Ready" if battery["battery_mwh"] >= 1 else
                    "Basic"
                ),
                "vpp_compatibility": "Strong" if battery["battery_mwh"] >= 3 else "Moderate",
                "strategic_summary": (
                    f"Strategic Energy Storage Insights\n\n"
                    f"• Battery Readiness Level: "
                    f"{'Advanced' if battery['battery_mwh'] >= 5 else 'Commercial Ready' if battery['battery_mwh'] >= 1 else 'Basic'}\n\n"
                    f"• VPP Compatibility: {'Strong' if battery['battery_mwh'] >= 3 else 'Moderate'}"
                ),
            },
        },
        "financial": {
            "economics": {
                "estimated_system_cost_usd": round(estimated_system_cost, 2),
                "annual_savings_usd":        revenue["annual_savings_usd"],
                "estimated_roi_years":       round(roi_years, 1),
                "economics_summary": (
                    f"Financial Performance Assessment\n\n"
                    f"• Estimated System Investment: ${estimated_system_cost:,.0f} USD\n\n"
                    f"• Estimated Annual Savings: ${revenue['annual_savings_usd']:,.0f} USD/year\n\n"
                    f"• Estimated ROI Period: {roi_years:.1f} years"
                ),
            },
            "savings": {
                "monthly_savings_usd": round(revenue["annual_savings_usd"] / 12, 2),
                "daily_savings_usd":   round(revenue["annual_savings_usd"] / 365, 2),
                "savings_summary": (
                    f"Projected Energy Cost Savings\n\n"
                    f"• Estimated Daily Savings: ${revenue['annual_savings_usd']/365:,.0f} USD/day\n\n"
                    f"• Estimated Monthly Savings: ${revenue['annual_savings_usd']/12:,.0f} USD/month\n\n"
                    f"• Estimated Annual Savings: ${revenue['annual_savings_usd']:,.0f} USD/year"
                ),
            },
            "insights": {
                "financial_viability": (
                    "Excellent" if roi_years <= 4 else
                    "Good"      if roi_years <= 7 else
                    "Moderate"
                ),
                "investment_scale": (
                    "Utility Scale" if estimated_system_cost >= 5000000 else "Commercial Scale"
                ),
                "strategic_summary": (
                    f"Strategic Financial Insights\n\n"
                    f"• Financial Viability: "
                    f"{'Excellent' if roi_years <= 4 else 'Good' if roi_years <= 7 else 'Moderate'}\n\n"
                    f"• Investment Category: "
                    f"{'Utility Scale' if estimated_system_cost >= 5000000 else 'Commercial Scale'}"
                ),
            },
        },
        "environmental": {
            "impact": {
                "carbon_savings_tons": revenue["carbon_savings_tons"],
                "tree_equivalent":     trees_equivalent,
            },
            "insights": {
                "environment_comment": (
                    "The project can significantly reduce annual carbon emissions "
                    "and support sustainability goals."
                ),
            },
        },
    }


# =========================================================
# 12. RECOMMENDATIONS ENGINE
# =========================================================

def generate_recommendations(property_type, roof_area_sqm, solar,
                              battery, revenue, peak_sun_hours, vpp_analysis):
    recommendations = []
    cap_kw     = solar["system_capacity_kw"]       # use top-level key
    estimated_roi = safe_div(
        solar["technical"]["system_capacity_kw"] * 800,
        revenue["annual_savings_usd"],
        fallback=999,
    )

    if cap_kw < 500:
        recommendations.append({
            "category": "Solar Expansion", "priority": "Medium",
            "title": "Increase Solar Deployment Scale",
            "recommendation": (
                "The current estimated solar capacity remains relatively small. "
                "Expanding rooftop solar deployment could improve long-term economics "
                "and strengthen future VPP participation potential."
            ),
        })

    if battery["battery_mwh"] < 1:
        recommendations.append({
            "category": "Battery Storage", "priority": "High",
            "title": "Increase Energy Storage Capacity",
            "recommendation": (
                "The recommended battery storage capacity may limit dispatch flexibility. "
                "Increasing battery capacity could improve resiliency and VPP readiness."
            ),
        })

    if peak_sun_hours < 4.5:
        recommendations.append({
            "category": "Energy Optimization", "priority": "Medium",
            "title": "Consider Hybrid Energy Strategy",
            "recommendation": (
                "The site's estimated solar irradiance is moderate. A hybrid distributed "
                "energy strategy incorporating battery optimization may improve project economics."
            ),
        })

    if property_type in ["Warehouse", "Factory", "Mall"]:
        recommendations.append({
            "category": "VPP Integration", "priority": "High",
            "title": "Evaluate VPP Participation",
            "recommendation": (
                "The property's operational and energy characteristics appear well-suited "
                "for future Virtual Power Plant integration."
            ),
        })

    if estimated_roi > 8:
        recommendations.append({
            "category": "Financial Optimization", "priority": "Medium",
            "title": "Improve Project Financial Performance",
            "recommendation": (
                "The estimated project payback period is relatively long. Financial performance "
                "may be improved through capital incentives or optimized system sizing."
            ),
        })

    if vpp_analysis["vpp_score"] >= 80:
        recommendations.append({
            "category": "Grid Services", "priority": "High",
            "title": "Pursue Advanced Grid Service Integration",
            "recommendation": (
                "The property demonstrates strong technical potential for advanced distributed "
                "energy participation including frequency regulation and demand response aggregation."
            ),
        })

    if revenue["carbon_savings_tons"] > 500:
        recommendations.append({
            "category": "Sustainability", "priority": "Low",
            "title": "Leverage Sustainability Benefits",
            "recommendation": (
                "The projected carbon reduction potential may contribute meaningfully toward "
                "corporate ESG initiatives and sustainability targets."
            ),
        })

    if not recommendations:
        recommendations.append({
            "category": "General", "priority": "Low",
            "title": "Maintain Distributed Energy Evaluation",
            "recommendation": (
                "The property demonstrates balanced distributed energy characteristics. "
                "Further detailed engineering analysis may improve project accuracy."
            ),
        })

    return recommendations


# =========================================================
# MAIN PIPELINE
# =========================================================

def analyze_property(lat, lon):

    # ── 1. Building footprint (Google Maps + RT-DETR) ─────────
    building_data = fetch_building_footprint(lat, lon)

    if "error" in building_data:
        return building_data

    geometry      = building_data["geometry"]
    building_type = building_data["building"]
    building_name = building_data["name"]
    levels        = building_data["levels"]

    # ── 2. Area — use pre-computed value directly ─────────────
    #    No need to call calculate_area_sqm separately since
    #    fetch_building_footprint already computed it accurately.
    roof_area_sqm = building_data["area_sqm"]

    # ── 3. Solar irradiance ───────────────────────────────────
    peak_sun_hours = get_peak_sun_hours(lat, lon)

    # ── 4. Property classification ────────────────────────────
    property_type = classify_property(
        roof_area_sqm, building_type, building_name, levels
    )

    # ── 5. Solar estimation ───────────────────────────────────
    solar = estimate_solar(roof_area_sqm, peak_sun_hours)

    # ── 6. Battery estimation ─────────────────────────────────
    battery = estimate_battery(solar["daily_generation_kwh"])

    # ── 7. Revenue estimation ─────────────────────────────────
    revenue = estimate_revenue(solar["annual_generation_kwh"])

    # ── 8. VPP analysis ───────────────────────────────────────
    #    Use top-level solar keys (system_capacity_kw, annual_generation_kwh)
    vpp_analysis = calculate_vpp_analysis(
        property_type,
        roof_area_sqm,
        solar["system_capacity_kw"],        # top-level key
        battery["battery_mwh"],
        peak_sun_hours,
        solar["annual_generation_kwh"],     # top-level key
    )

    # ── 9. Detailed report ────────────────────────────────────
    report = generate_detailed_report(
        property_type, roof_area_sqm, solar, battery, revenue, peak_sun_hours
    )

    # ── 10. Recommendations ───────────────────────────────────
    recommendations = generate_recommendations(
        property_type, roof_area_sqm, solar, battery,
        revenue, peak_sun_hours, vpp_analysis
    )

    # ── Final response ────────────────────────────────────────
    return {
        "coordinates": {
            "latitude":  lat,
            "longitude": lon,
        },
        "detection": {
            "roof_area_sqm":           roof_area_sqm,
            "roof_area_sqft":          round(roof_area_sqm * 10.7639),
            "confidence":              building_data["confidence"],
            "all_roofs_detected":      building_data["all_roofs_detected"],
            "distance_from_center_px": building_data["distance_from_center_px"],
            "satellite_image":         building_data["image_path"],
        },
        "executive_summary": report["executive_summary"],
        "property":          report["property"],
        "solar":             report["solar"],
        "battery":           report["battery"],
        "financial":         report["financial"],
        "environmental":     report["environmental"],
        "vpp_analysis":      vpp_analysis,
        "recommendations":   recommendations,
    }


# =========================================================
# ENTRY POINT
# =========================================================

# if __name__ == "__main__":
#     import sys, json

#     if len(sys.argv) == 3:
#         lat = float(sys.argv[1])
#         lon = float(sys.argv[2])
#     else:
#         # Default: Jamshedpur industrial area
#         lat, lon = 22.772607326260346, 86.21329470844114

#     result = analyze_property(lat, lon)

#     if "error" in result:
#         print(f"\nERROR: {result['error']}")
#     else:
#         print(json.dumps(result, indent=2))
#         with open("result.json", "w") as f:
#             json.dump(result, f, indent=2)
#         print("\nSaved → result.json")
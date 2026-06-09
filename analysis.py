# =========================================================
# NON-AI AUTONOMOUS PROPERTY INTELLIGENCE SYSTEM
# USING:
# Mapbox + OpenStreetMap + GIS
# =========================================================

# INSTALL:
# pip install osmnx geopandas shapely geopy requests pandas


import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon
# from geopy.geocoders import Nominatim
import requests
import pandas as pd
import numpy as np


# =========================================================
# MAPBOX TOKEN
# =========================================================

MAPBOX_TOKEN = "YOUR_MAPBOX_TOKEN"


# =========================================================
# STANDARD INDUSTRY ASSUMPTIONS
# =========================================================

STANDARD_VALUES = {

    # Solar
    "packing_factor": 0.8,
    "performance_ratio": 0.8,

    "panel_wattage": 550,

    # Financials
    "electricity_price": 0.12,

    # Battery sizing
    "battery_factor": 0.3,

    # Carbon savings
    "carbon_factor": 0.0007
}


# =========================================================
# 1. GEOCODING ENGINE
# =========================================================

# def get_coordinates(address):

#     geolocator = Nominatim(
#         user_agent="vpp-platform"
#     )

#     location = geolocator.geocode(address)

#     if not location:

#         raise Exception(
#             "Address not found."
#         )

#     return (
#         location.latitude,
#         location.longitude
#     )


# =========================================================
# 2. FETCH BUILDING FOOTPRINT
# =========================================================

def fetch_building_footprint(
    latitude,
    longitude
):

    # Search around coordinate
    tags = {"building": True}

    

    try:

        gdf = ox.features_from_point(

            (latitude, longitude),

            tags=tags,

            dist=300
        )

    except Exception:

        return {"error" :"No building detected at this location."}

    # ------------------------------------
    # CHECK EMPTY
    # ------------------------------------


    
    if(gdf.empty):
        return {"error" :"No building detected at this location."}
    

    # Keep polygons only
    gdf = gdf[
        gdf.geometry.type.isin(
            ['Polygon', 'MultiPolygon']
        )
    ]

    if gdf.empty:

        raise Exception(
            "No building footprint found."
        )

    # Take largest building
    gdf_projected = gdf.to_crs(epsg=3857)

    gdf["area"] = gdf_projected.geometry.area

    largest = gdf.sort_values(
        by="area",
        ascending=False
    ).iloc[0]

    return {
    "geometry": largest.geometry,
    "building": largest.get("building", "unknown"),
    "name":
        (
            largest.get("name")
            if pd.notna(
                largest.get("name")
            )
            else "Unknown"
        ),

    "levels":
        (
            largest.get("building:levels")
            if pd.notna(
                largest.get(
                    "building:levels"
                )
            )
            else 1
        )
    }


# =========================================================
# 3. CALCULATE AREA
# =========================================================

def calculate_area_sqm(
    geometry
):

    # Convert CRS for accurate area
    gdf = gpd.GeoDataFrame(
        geometry=[geometry],
        crs="EPSG:4326"
    )

    gdf = gdf.to_crs(
        epsg=3857
    )

    area_sqm = gdf.geometry.area.iloc[0]

    return round(area_sqm, 2)


# =========================================================
# 4. FETCH PEAK SUN HOURS
# =========================================================

# def get_peak_sun_hours(lat, lon):

#     url = (
#         "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"
#         f"?lat={lat}"
#         f"&lon={lon}"
#         f"&outputformat=json"
#     )

#     response = requests.get(url)
#     data = response.json()

#     hourly = data["outputs"]["hourly"]

#     total = sum(h["G(i)"] for h in hourly)

#     days = len(set(h["time"][:8] for h in hourly))

#     avg_psh = total / days / 1000

#     return round(avg_psh, 2)
# def get_peak_sun_hours(lat, lon):

#     url = (
#         f"https://api.open-meteo.com/v1/forecast"
#         f"?latitude={lat}"
#         f"&longitude={lon}"
#         f"&hourly=shortwave_radiation"
#         f"&forecast_days=7"
#     )

#     response = requests.get(url)

#     data = response.json()
#     print(data)
#     times = data['hourly']['time']
#     radiation = data['hourly']['shortwave_radiation']

#     # Create dataframe
#     df = pd.DataFrame({
#         'time': pd.to_datetime(times),
#         'radiation': radiation
#     })

#     # Extract date
#     df['date'] = df['time'].dt.date

#     # Daily radiation sum
#     daily_radiation = df.groupby('date')['radiation'].sum()

#     # Convert Wh/m² → kWh/m²
#     daily_psh = daily_radiation / 1000

#     # Average PSH
#     avg_psh = daily_psh.mean()

#     return round(avg_psh, 2)



# def get_peak_sun_hours(lat, lon):

#     # -----------------------------
#     # 1. TRY OPEN-METEO FIRST
#     # -----------------------------
#     try:
#         url = (
#             f"https://api.open-meteo.com/v1/forecast"
#             f"?latitude={lat}"
#             f"&longitude={lon}"
#             f"&hourly=shortwave_radiation"
#             f"&forecast_days=7"
#         )

#         response = requests.get(url, timeout=20)

#         # Raise error if bad response
#         response.raise_for_status()

#         data = response.json()

#         # Validate response structure
#         if (
#             "hourly" not in data
#             or "time" not in data["hourly"]
#             or "shortwave_radiation" not in data["hourly"]
#         ):
#             raise ValueError("Invalid Open-Meteo response")

#         times = data["hourly"]["time"]
#         radiation = data["hourly"]["shortwave_radiation"]

#         # Create dataframe
#         df = pd.DataFrame({
#             "time": pd.to_datetime(times),
#             "radiation": radiation
#         })

#         # Extract date
#         df["date"] = df["time"].dt.date

#         # Daily radiation sum
#         daily_radiation = df.groupby("date")["radiation"].sum()

#         # Convert Wh/m² → kWh/m²
#         daily_psh = daily_radiation / 1000

#         # Average PSH
#         avg_psh = daily_psh.mean()

#         print("Using Open-Meteo API")

#         return round(avg_psh, 2)

#     except Exception as e:

#         print(f"Open-Meteo failed: {e}")
#         print("Switching to PVGIS API...")

#     # -----------------------------
#     # 2. FALLBACK TO PVGIS API
#     # -----------------------------
#     try:
#         url = (
#             "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"
#             f"?lat={lat}"
#             f"&lon={lon}"
#             f"&outputformat=json"
#         )

#         response = requests.get(url, timeout=20)

#         response.raise_for_status()

#         data = response.json()

#         hourly = data["outputs"]["hourly"]

#         total = sum(h["G(i)"] for h in hourly)

#         days = len(set(h["time"][:8] for h in hourly))

#         avg_psh = total / days / 1000

#         print("Using PVGIS API")

#         return round(avg_psh, 2)

#     except Exception as e:

#         print(f"PVGIS also failed: {e}")

#         return None
def get_peak_sun_hours(
    lat,
    lon=None
):

    lat = abs(lat)

    # =====================================
    # VERY HIGH SOLAR REGIONS
    # =====================================

    if lat <= 15:

        return 6.0

    # =====================================
    # HIGH SOLAR REGIONS
    # =====================================

    elif lat <= 25:

        return 5.7

    # =====================================
    # GOOD SOLAR REGIONS
    # =====================================

    elif lat <= 35:

        return 5.3

    # =====================================
    # MODERATE SOLAR REGIONS
    # =====================================

    elif lat <= 45:

        return 4.8

    # =====================================
    # LOW SOLAR REGIONS
    # =====================================

    elif lat <= 55:

        return 4.0

    # =====================================
    # VERY LOW SOLAR REGIONS
    # =====================================

    else:

        return 3.2
# =========================================================
# 5. PROPERTY CLASSIFICATION
# =========================================================

def classify_property(
    roof_area_sqm,
    building_type=None,
    building_name=None,
    levels=1
):

    building_type = str(building_type or "").lower()
    building_name = str(building_name or "").lower()

    text = f"{building_type} {building_name}"

    # -------------------------------
    # KEYWORD MAP
    # -------------------------------

    categories = {
        "Warehouse": [
            "warehouse",
            "logistics",
            "storage",
            "depot"
        ],

        "Mall": [
            "mall",
            "shopping",
            "retail",
            "plaza",
            "market"
        ],

        "Hospital": [
            "hospital",
            "medical",
            "clinic",
            "healthcare"
        ],

        "Factory": [
            "factory",
            "industrial",
            "manufacturing",
            "plant"
        ],

        "Office": [
            "office",
            "corporate",
            "business center"
        ]
    }

    # -------------------------------
    # KEYWORD MATCH
    # -------------------------------
    import re
    for category, keywords in categories.items():

        for keyword in keywords:

            if re.search(rf"\b{keyword}\b", text):

                return category

    # -------------------------------
    # AREA-BASED FALLBACK
    # -------------------------------

    try:
        levels = int(levels)
    except:
        levels = 1

    if roof_area_sqm > 20000:

        if levels <= 2:
            return "Warehouse"

        return "Factory"

    elif roof_area_sqm > 10000:

        return "Mall"

    elif roof_area_sqm > 3000:

        return "Office"

    return "Small Commercial"


# =========================================================
# 6. SOLAR ESTIMATION ENGINE
# =========================================================

def estimate_solar(
    roof_area_sqm,
    peak_sun_hours
):

    packing_factor = (
        STANDARD_VALUES[
            'packing_factor'
        ]
    )

    performance_ratio = (
        STANDARD_VALUES[
            'performance_ratio'
        ]
    )

    panel_wattage = (
        STANDARD_VALUES[
            'panel_wattage'
        ]
    )

    usable_area = (
        roof_area_sqm
        * packing_factor
    )

    # Approx 5 sqm per panel
    panel_count = int(
        usable_area / 5
    )

    system_capacity_kw = (
        panel_count
        * panel_wattage
    ) / 1000

    daily_generation = (
        system_capacity_kw
        * peak_sun_hours
        * performance_ratio
    )

    annual_generation = (
        daily_generation
        * 365
    )

    return {

        "usable_area_sqm":
            round(
                usable_area,
                2
            ),

        "panel_count":
            panel_count,

        "system_capacity_kw":
            round(
                system_capacity_kw,
                2
            ),

        "daily_generation_kwh":
            round(
                daily_generation,
                2
            ),
        "monthly_generation_kwh":
            round(
                annual_generation / 12, 2
                  
            ),
        "annual_generation_kwh":
            round(
                annual_generation,
                2
            ),
        "insights": 
            { "solar_viability":
                ( "Excellent" 
                 if peak_sun_hours >= 5.5 else "Good" 
                 if peak_sun_hours >= 4.5 else "Moderate" ),
                "deployment_scale":
                    ( "Utility Scale" 
                     if system_capacity_kw >= 5000 else "Commercial Scale" 
                     if system_capacity_kw >= 500 else "Small Commercial" )
            },
            "performance": 
                { 
                 "specific_yield":
                    round( annual_generation / system_capacity_kw, 2 ),
                 "capacity_factor":
                     round( ( annual_generation / ( system_capacity_kw * 24 * 365 ) ) * 100, 2 ) 
                },
            "technical":
                { 
                 "usable_area_sqm":
                     round(usable_area, 2), 
                 "panel_count":
                     panel_count, 
                 "system_capacity_kw":
                     round(system_capacity_kw, 2),
                 "panel_wattage":
                     panel_wattage,
                 "packing_factor":
                     packing_factor,
                 "performance_ratio":
                     performance_ratio 
                },
        }


# =========================================================
# 7. BATTERY ENGINE
# =========================================================

def estimate_battery(
    daily_generation
):

    battery_factor = (
        STANDARD_VALUES[
            'battery_factor'
        ]
    )

    battery_size = (
        daily_generation
        * battery_factor
    )

    return {

        "battery_kwh":
            round(
                battery_size,
                2
            ),

        "battery_mwh":
            round(
                battery_size / 1000,
                2
            )
    }


# =========================================================
# 8. REVENUE ENGINE
# =========================================================

def estimate_revenue(
    annual_generation
):

    electricity_price = (
        STANDARD_VALUES[
            'electricity_price'
        ]
    )

    carbon_factor = (
        STANDARD_VALUES[
            'carbon_factor'
        ]
    )

    annual_savings = (
        annual_generation
        * electricity_price
    )

    carbon_savings = (
        annual_generation
        * carbon_factor
    )

    return {

        "annual_savings_usd":
            round(
                annual_savings,
                2
            ),

        "carbon_savings_tons":
            round(
                carbon_savings,
                2
            )
    }


# =========================================================
# 9. VPP SCORING ENGINE
# =========================================================

def calculate_vpp_score(

    property_type,

    solar_capacity_kw,

    battery_mwh,

    peak_sun_hours,

    annual_generation_kwh
):

    score = 0

    # =====================================================
    # 1. SOLAR CAPACITY SCORE
    # =====================================================

    if solar_capacity_kw >= 5000:

        score += 30

    elif solar_capacity_kw >= 1000:

        score += 22

    elif solar_capacity_kw >= 300:

        score += 15

    else:

        score += 8

    # =====================================================
    # 2. BATTERY SCORE
    # =====================================================

    if battery_mwh >= 10:

        score += 25

    elif battery_mwh >= 3:

        score += 18

    elif battery_mwh >= 1:

        score += 10

    else:

        score += 5

    # =====================================================
    # 3. SOLAR RESOURCE SCORE
    # =====================================================

    if peak_sun_hours >= 5.5:

        score += 15

    elif peak_sun_hours >= 4.5:

        score += 10

    else:

        score += 5

    # =====================================================
    # 4. PROPERTY TYPE SCORE
    # =====================================================

    preferred_properties = [

        "Warehouse",

        "Factory",

        "Mall",

        "Office"
    ]

    if property_type in preferred_properties:

        score += 15

    else:

        score += 8

    # =====================================================
    # 5. ENERGY SCALE SCORE
    # =====================================================

    if annual_generation_kwh >= 10000000:

        score += 15

    elif annual_generation_kwh >= 3000000:

        score += 10

    else:

        score += 5

    # =====================================================
    # NORMALIZE SCORE
    # =====================================================

    return min(score, 100)


# =========================================================
# 10. MAIN PIPELINE
# =========================================================
# =========================================================
# 11. GENERATE INTELLIGENT REPORT
# =========================================================

def generate_detailed_report(

    property_type,
    roof_area_sqm,
    solar,
    battery,
    revenue,
    peak_sun_hours
):

    # =====================================================
    # ENERGY CONSUMPTION ESTIMATION
    # =====================================================

    consumption_map = {

        "Warehouse": 4,
        "Mall": 18,
        "Hospital": 25,
        "Factory": 15,
        "Office": 12,
        "Small Commercial": 8
    }

    energy_intensity = (
        consumption_map.get(
            property_type,
            10
        )
    )

    monthly_consumption = (
        roof_area_sqm
        * energy_intensity
    )

    daily_consumption = (
        monthly_consumption / 30
    )

    # =====================================================
    # EQUIVALENCY METRICS
    # =====================================================

    homes_powered = int(

        solar[
            "daily_generation_kwh"
        ] / 12
    )

    ev_charges = int(

        solar[
            "daily_generation_kwh"
        ] / 60
    )

    trees_equivalent = int(

        revenue[
            "carbon_savings_tons"
        ] * 45
    )

    # =====================================================
    # ROI ESTIMATION
    # =====================================================

    estimated_system_cost = (

        solar["technical"][
            "system_capacity_kw"
        ] * 800
    )

    roi_years = (

        estimated_system_cost
        / revenue[
            "annual_savings_usd"
        ]
    )

    # =====================================================
    # EXECUTIVE SUMMARY
    # =====================================================

    summary = f"""
This property demonstrates strong distributed energy potential with an estimated rooftop area of {roof_area_sqm:.0f} sqm and regional solar irradiance of {peak_sun_hours} Peak Sun Hours.

The proposed solar system can generate approximately {solar["daily_generation_kwh"]:.0f} kWh/day, supporting commercial solar deployment, battery integration, and future Virtual Power Plant participation.
"""

    # =====================================================
    # FINAL REPORT
    # =====================================================

    return {

        # =================================================
        # EXECUTIVE SUMMARY
        # =================================================

"executive_summary": {

            "summary":
                summary,

            "key_metrics": {

                "property_type":
                    property_type,

                "roof_area_sqm":
                    round(
                        roof_area_sqm,
                        2
                    ),

                "solar_capacity_kw":
                    solar["technical"][
                        "system_capacity_kw"
                    ],

                "battery_mwh":
                    battery[
                        "battery_mwh"
                    ],

                "annual_generation_kwh":
                    solar[
                        "annual_generation_kwh"
                    ],

                "annual_savings_usd":
                    revenue[
                        "annual_savings_usd"
                    ]
            }
        },

        # =================================================
        # PROPERTY ANALYSIS
        # =================================================

"property": {

            "classification": {

                "property_type":
                    property_type,

                "roof_area_sqm":
                    round(
                        roof_area_sqm,
                        2
                    )
            },

            "energy_profile": {

                "estimated_daily_consumption_kwh":
                    round(
                        daily_consumption,
                        2
                    ),

                "estimated_monthly_consumption_kwh":
                    round(
                        monthly_consumption,
                        2
                    ),

                "energy_intensity":
                    energy_intensity
            },

            "insights": {

                "consumption_methodology":
                    (
                        "Estimated using "
                        "commercial energy "
                        "benchmarks based "
                        "on property type."
                    ),

                "property_comment":
                    (
                        "Property profile is "
                        "suitable for distributed "
                        "energy deployment."
                    )
            }
        },

"solar":{
    
"technical":
    (
        f"Solar Infrastructure Analysis\n\n"

        f"• Usable Rooftop Area: "
        f"{solar['technical']['usable_area_sqm']:.0f} sqm\n\n"

        f"• Estimated Panel Count: "
        f"{solar['technical']['panel_count']:,}\n\n"

        f"• Proposed System Capacity: "
        f"{solar['technical']['system_capacity_kw']:.0f} kW\n\n"

        f"• System Performance Ratio: "
        f"{solar['technical']['performance_ratio']}\n\n"

        f"The rooftop configuration appears "
        f"suitable for medium-to-large scale "
        f"commercial photovoltaic deployment "
        f"with strong distributed energy "
        f"integration potential."
    )
,

    # =====================================================
    # GENERATION ANALYSIS
    # =====================================================

"generation":
    (
        f"Estimated Regional Solar Resource\n\n"

        f"• Average Solar Irradiance: "
        f"{peak_sun_hours} Peak Sun Hours\n\n"

        f"• Estimated Daily Generation: "
        f"{solar['daily_generation_kwh']:.0f} kWh/day\n\n"

        f"• Estimated Monthly Generation: "
        f"{solar['monthly_generation_kwh']:.0f} kWh/month\n\n"

        f"• Estimated Annual Generation: "
        f"{solar['annual_generation_kwh']:.0f} kWh/year\n\n"

        f"The projected generation profile "
        f"indicates strong commercial-scale "
        f"solar production potential capable "
        f"of significantly offsetting grid "
        f"electricity consumption and improving "
        f"long-term energy resilience."
    )
,

    # =====================================================
    # EQUIVALENCY ANALYSIS
    # =====================================================

    "equivalencies": {

        "homes_powered":
            homes_powered,

        "ev_charges":
            ev_charges,

        "equivalency_summary":
            (
                f"The estimated solar generation "
                f"capacity is approximately equivalent "
                f"to powering {homes_powered:,} average "
                f"homes daily or supporting nearly "
                f"{ev_charges:,} EV charging sessions "
                f"per day. These equivalency metrics "
                f"help contextualize the scale of the "
                f"proposed distributed energy system."
            )
    },

    # =====================================================
    # PERFORMANCE ANALYSIS
    # =====================================================

    "performance": {

        "specific_yield":
            solar["performance"][
                "specific_yield"
            ],

        "capacity_factor":
            solar["performance"][
                "capacity_factor"
            ],

        "performance_summary":
            (
                f"Performance analysis indicates a "
                f"specific yield of approximately "
                f"{solar['performance']['specific_yield']:.0f} "
                f"kWh/kW/year with an estimated "
                f"capacity factor of "
                f"{solar['performance']['capacity_factor']:.1f}%. "
                f"These metrics suggest commercially "
                f"viable solar generation performance "
                f"under current operating assumptions."
            )
    },

    # =====================================================
    # STRATEGIC INSIGHTS
    # =====================================================

    "insights": {

        "solar_viability":
            solar["insights"][
                "solar_viability"
            ],

        "deployment_scale":
            solar["insights"][
                "deployment_scale"
            ],

        "strategic_summary":
            (
                f"The property demonstrates "
                f"{solar['insights']['solar_viability']} "
                f"solar viability with a deployment "
                f"classification of "
                f"{solar['insights']['deployment_scale']}. "
                f"Based on estimated generation scale "
                f"and rooftop utilization characteristics, "
                f"the project appears suitable for "
                f"future distributed energy integration "
                f"including battery optimization and "
                f"Virtual Power Plant participation."
            )
    }

},

        # =================================================
        # BATTERY ANALYSIS
        # =================================================

"battery": {

    # =====================================================
    # STORAGE ANALYSIS
    # =====================================================

    "storage": {

        "battery_kwh":
            battery["battery_kwh"],

        "battery_mwh":
            battery["battery_mwh"],

        "storage_summary":
            (
                f"Battery Storage Infrastructure\n\n"

                f"• Recommended Battery Capacity: "
                f"{battery['battery_kwh']:.0f} kWh\n\n"

                f"• Utility Scale Storage: "
                f"{battery['battery_mwh']:.2f} MWh\n\n"

                f"• Storage Strategy: "
                f"Commercial Distributed Energy Storage\n\n"

                f"The proposed battery sizing is "
                f"designed to support commercial "
                f"energy optimization and improve "
                f"overall distributed energy flexibility."
            )
    },

    # =====================================================
    # GRID APPLICATIONS
    # =====================================================

    "applications": {

        "supported_services": [

            "Peak Shaving",

            "Demand Response",

            "Backup Power",

            "Energy Arbitrage"
        ],

        "applications_summary":
            (
                f"Operational Energy Applications\n\n"

                f"• Peak Demand Reduction Support\n\n"

                f"• Backup Power Resiliency\n\n"

                f"• Energy Time-Shifting Capability\n\n"

                f"• Future Smart Grid Participation\n\n"

                f"The battery infrastructure can "
                f"enhance operational resilience "
                f"while enabling future participation "
                f"in advanced distributed energy and "
                f"grid-balancing programs."
            )
    },

    # =====================================================
    # PERFORMANCE ANALYSIS
    # =====================================================

    "performance": {

        "estimated_backup_hours":
            round(
                battery["battery_kwh"] / 500,
                1
            ),

        "dispatch_capability":
            (
                "High"
                if battery["battery_mwh"] >= 5
                else
                "Moderate"
                if battery["battery_mwh"] >= 1
                else
                "Limited"
            ),

        "performance_summary":
            (
                f"Battery Performance Assessment\n\n"

                f"• Estimated Backup Capability: "
                f"{round(battery['battery_kwh'] / 500, 1)} hours\n\n"

                f"• Dispatch Flexibility: "
                f"{'High' if battery['battery_mwh'] >= 5 else 'Moderate' if battery['battery_mwh'] >= 1 else 'Limited'}\n\n"

                f"• Grid Interaction Potential: "
                f"Commercial Scale\n\n"

                f"The proposed battery configuration "
                f"provides operational flexibility "
                f"for commercial energy management "
                f"while supporting future scalable "
                f"energy storage expansion."
            )
    },

    # =====================================================
    # STRATEGIC INSIGHTS
    # =====================================================

    "insights": {

        "battery_readiness":
            (
                "Advanced"
                if battery["battery_mwh"] >= 5
                else
                "Commercial Ready"
                if battery["battery_mwh"] >= 1
                else
                "Basic"
            ),

        "vpp_compatibility":
            (
                "Strong"
                if battery["battery_mwh"] >= 3
                else
                "Moderate"
            ),

        "strategic_summary":
            (
                f"Strategic Energy Storage Insights\n\n"

                f"• Battery Readiness Level: "
                f"{'Advanced' if battery['battery_mwh'] >= 5 else 'Commercial Ready' if battery['battery_mwh'] >= 1 else 'Basic'}\n\n"

                f"• VPP Compatibility: "
                f"{'Strong' if battery['battery_mwh'] >= 3 else 'Moderate'}\n\n"

                f"• Energy Flexibility Potential: "
                f"Commercial Distributed Energy\n\n"

                f"The battery system architecture "
                f"appears suitable for future energy "
                f"optimization strategies including "
                f"distributed storage coordination, "
                f"demand response participation, and "
                f"Virtual Power Plant integration."
            )
    }
},


        # =================================================
        # ENVIRONMENTAL ANALYSIS
        # =================================================
# =================================================
# FINANCIAL ANALYSIS
# =================================================

"financial": {

    # =====================================================
    # ECONOMIC ANALYSIS
    # =====================================================

    "economics": {

        "estimated_system_cost_usd":
            round(
                estimated_system_cost,
                2
            ),

        "annual_savings_usd":
            revenue[
                "annual_savings_usd"
            ],

        "estimated_roi_years":
            round(
                roi_years,
                1
            ),

        "economics_summary":
            (
                f"Financial Performance Assessment\n\n"

                f"• Estimated System Investment: "
                f"${estimated_system_cost:,.0f} USD\n\n"

                f"• Estimated Annual Savings: "
                f"${revenue['annual_savings_usd']:,.0f} USD/year\n\n"

                f"• Estimated ROI Period: "
                f"{roi_years:.1f} years\n\n"

                f"The projected financial profile "
                f"indicates meaningful long-term "
                f"commercial electricity cost "
                f"reduction potential supported by "
                f"onsite renewable energy generation."
            )
    },

    # =====================================================
    # SAVINGS ANALYSIS
    # =====================================================

    "savings": {

        "monthly_savings_usd":
            round(
                revenue[
                    "annual_savings_usd"
                ] / 12,
                2
            ),

        "daily_savings_usd":
            round(
                revenue[
                    "annual_savings_usd"
                ] / 365,
                2
            ),

        "savings_summary":
            (
                f"Projected Energy Cost Savings\n\n"

                f"• Estimated Daily Savings: "
                f"${revenue['annual_savings_usd']/365:,.0f} USD/day\n\n"

                f"• Estimated Monthly Savings: "
                f"${revenue['annual_savings_usd']/12:,.0f} USD/month\n\n"

                f"• Estimated Annual Savings: "
                f"${revenue['annual_savings_usd']:,.0f} USD/year\n\n"

                f"The distributed energy deployment "
                f"can substantially reduce long-term "
                f"grid electricity dependence and "
                f"improve operational energy economics."
            )
    },

    # =====================================================
    # INVESTMENT INSIGHTS
    # =====================================================

    "insights": {

        "financial_viability":
            (
                "Excellent"
                if roi_years <= 4
                else
                "Good"
                if roi_years <= 7
                else
                "Moderate"
            ),

        "investment_scale":
            (
                "Utility Scale"
                if estimated_system_cost >= 5000000
                else
                "Commercial Scale"
            ),

        "strategic_summary":
            (
                f"Strategic Financial Insights\n\n"

                f"• Financial Viability: "
                f"{'Excellent' if roi_years <= 4 else 'Good' if roi_years <= 7 else 'Moderate'}\n\n"

                f"• Investment Category: "
                f"{'Utility Scale' if estimated_system_cost >= 5000000 else 'Commercial Scale'}\n\n"

                f"• Long-Term Energy Economics: "
                f"Positive\n\n"

                f"The proposed distributed energy "
                f"investment demonstrates strong "
                f"potential for long-term operational "
                f"savings while supporting future "
                f"energy resiliency and sustainability "
                f"objectives."
            )
    }
},

"environmental": {

            "impact": {

                "carbon_savings_tons":
                    revenue[
                        "carbon_savings_tons"
                    ],

                "tree_equivalent":
                    trees_equivalent
            },

            "insights": {

                "environment_comment":
                    (
                        "The project can significantly "
                        "reduce annual carbon emissions "
                        "and support sustainability goals."
                    )
            }
        }
    }


    # =========================================================
# ADVANCED VPP SCORING ENGINE
# =========================================================

def calculate_vpp_analysis(

    property_type,

    roof_area_sqm,

    solar_capacity_kw,

    battery_mwh,

    peak_sun_hours,

    annual_generation_kwh
):

    # =====================================================
    # INITIAL SCORE
    # =====================================================

    score = 0

    insights = []

    strengths = []

    risks = []

    recommendations = []

    # =====================================================
    # 1. SOLAR CAPACITY SCORE
    # =====================================================

    if solar_capacity_kw >= 5000:

        score += 30

        strengths.append(
            "Large-scale solar capacity suitable "
            "for utility-grade participation."
        )

    elif solar_capacity_kw >= 1000:

        score += 22

        strengths.append(
            "Strong commercial solar generation potential."
        )

    elif solar_capacity_kw >= 300:

        score += 15

    else:

        score += 8

        risks.append(
            "Limited solar scale may reduce "
            "grid export potential."
        )

    # =====================================================
    # 2. BATTERY SCORE
    # =====================================================

    if battery_mwh >= 10:

        score += 25

        strengths.append(
            "Battery system suitable for advanced "
            "grid balancing and energy arbitrage."
        )

    elif battery_mwh >= 3:

        score += 18

        strengths.append(
            "Battery storage supports VPP operations."
        )

    elif battery_mwh >= 1:

        score += 10

    else:

        risks.append(
            "Limited storage reduces dispatch flexibility."
        )

    # =====================================================
    # 3. SOLAR RESOURCE SCORE
    # =====================================================

    if peak_sun_hours >= 5.5:

        score += 15

        strengths.append(
            "Excellent regional solar irradiance."
        )

    elif peak_sun_hours >= 4.5:

        score += 10

    else:

        score += 5

        risks.append(
            "Moderate solar irradiance may affect output consistency."
        )

    # =====================================================
    # 4. PROPERTY TYPE SCORE
    # =====================================================

    preferred_properties = [

        "Warehouse",

        "Factory",

        "Mall",

        "Office"
    ]

    if property_type in preferred_properties:

        score += 15

        strengths.append(
            "Commercial property profile aligns "
            "well with distributed energy deployment."
        )

    else:

        score += 8

    # =====================================================
    # 5. ENERGY SCALE SCORE
    # =====================================================

    if annual_generation_kwh >= 10000000:

        score += 15

    elif annual_generation_kwh >= 3000000:

        score += 10

    else:

        score += 5

    # =====================================================
    # NORMALIZE SCORE
    # =====================================================

    score = min(score, 100)

    # =====================================================
    # VPP READINESS CATEGORY
    # =====================================================

    if score >= 85:

        readiness = "Excellent"

        summary = (
            "This property demonstrates strong "
            "potential for Virtual Power Plant "
            "participation with significant "
            "distributed energy capabilities."
        )

    elif score >= 70:

        readiness = "High"

        summary = (
            "This property is well-positioned "
            "for commercial VPP integration."
        )

    elif score >= 55:

        readiness = "Moderate"

        summary = (
            "The property has moderate VPP "
            "potential with opportunities "
            "for optimization."
        )

    else:

        readiness = "Limited"

        summary = (
            "The property currently has limited "
            "VPP readiness."
        )

    # =====================================================
    # RECOMMENDATIONS
    # =====================================================

    if battery_mwh < 1:

        recommendations.append(
            "Increase battery storage capacity "
            "to improve dispatch flexibility."
        )

    if solar_capacity_kw < 500:

        recommendations.append(
            "Expand rooftop solar deployment "
            "to improve VPP economics."
        )

    if peak_sun_hours < 4.5:

        recommendations.append(
            "Consider hybrid renewable integration "
            "or advanced energy optimization."
        )

    # =====================================================
    # GRID SERVICES
    # =====================================================

    grid_services = []

    if battery_mwh >= 1:

        grid_services.extend([

            "Peak Shaving",

            "Demand Response",

            "Backup Power"
        ])

    if battery_mwh >= 5:

        grid_services.extend([

            "Energy Arbitrage",

            "Frequency Regulation"
        ])

    if solar_capacity_kw >= 1000:

        grid_services.append(
            "Grid Export Support"
        )

    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    return {

        "vpp_score":
            score,

        "readiness_level":
            readiness,

        "summary":
            summary,

        "strengths":
            strengths,

        "risks":
            risks,

        "recommendations":
            recommendations,

        "grid_services":
            grid_services,

        "analysis": {

            "solar_capacity_kw":
                solar_capacity_kw,

            "battery_mwh":
                battery_mwh,

            "peak_sun_hours":
                peak_sun_hours,

            "annual_generation_kwh":
                annual_generation_kwh
        }
    }

# =========================================================
# RECOMMENDATION ENGINE
# =========================================================

def generate_recommendations(

    property_type,

    roof_area_sqm,

    solar,

    battery,

    revenue,

    peak_sun_hours,

    vpp_analysis
):

    recommendations = []

    # =====================================================
    # SOLAR RECOMMENDATIONS
    # =====================================================

    if solar["technical"]["system_capacity_kw"] < 500:

        recommendations.append({

            "category":
                "Solar Expansion",

            "priority":
                "Medium",

            "title":
                "Increase Solar Deployment Scale",

            "recommendation":
                (
                    "The current estimated solar "
                    "capacity remains relatively "
                    "small for advanced commercial "
                    "energy optimization. Expanding "
                    "rooftop solar deployment could "
                    "improve long-term economics, "
                    "increase grid export capability, "
                    "and strengthen future VPP "
                    "participation potential."
                )
        })

    # =====================================================
    # BATTERY RECOMMENDATIONS
    # =====================================================

    if battery["battery_mwh"] < 1:

        recommendations.append({

            "category":
                "Battery Storage",

            "priority":
                "High",

            "title":
                "Increase Energy Storage Capacity",

            "recommendation":
                (
                    "The recommended battery storage "
                    "capacity may limit dispatch "
                    "flexibility and reduce the "
                    "property's ability to participate "
                    "in advanced grid services such as "
                    "demand response, peak shaving, "
                    "and energy arbitrage. Increasing "
                    "battery capacity could improve "
                    "resiliency and VPP readiness."
                )
        })

    # =====================================================
    # IRRADIANCE RECOMMENDATIONS
    # =====================================================

    if peak_sun_hours < 4.5:

        recommendations.append({

            "category":
                "Energy Optimization",

            "priority":
                "Medium",

            "title":
                "Consider Hybrid Energy Strategy",

            "recommendation":
                (
                    "The site's estimated solar "
                    "irradiance is moderate relative "
                    "to high-performing solar regions. "
                    "A hybrid distributed energy "
                    "strategy incorporating battery "
                    "optimization, energy efficiency "
                    "measures, or supplemental "
                    "renewable generation may improve "
                    "overall project economics and "
                    "operational reliability."
                )
        })

    # =====================================================
    # PROPERTY-TYPE RECOMMENDATIONS
    # =====================================================

    if property_type in [

        "Warehouse",

        "Factory",

        "Mall"
    ]:

        recommendations.append({

            "category":
                "VPP Integration",

            "priority":
                "High",

            "title":
                "Evaluate VPP Participation",

            "recommendation":
                (
                    "The property's operational and "
                    "energy characteristics appear "
                    "well-suited for future Virtual "
                    "Power Plant integration. "
                    "Participation in distributed "
                    "energy aggregation programs may "
                    "unlock additional value streams "
                    "through demand response, grid "
                    "support services, and energy "
                    "market participation."
                )
        })

    # =====================================================
    # ROI RECOMMENDATIONS
    # =====================================================

    estimated_roi = (

        (
            solar["technical"]["system_capacity_kw"]
            * 800
        )

        /

        revenue["annual_savings_usd"]
    )

    if estimated_roi > 8:

        recommendations.append({

            "category":
                "Financial Optimization",

            "priority":
                "Medium",

            "title":
                "Improve Project Financial Performance",

            "recommendation":
                (
                    "The estimated project payback "
                    "period is relatively long under "
                    "current assumptions. Financial "
                    "performance may be improved "
                    "through capital incentives, "
                    "optimized system sizing, battery "
                    "integration, time-of-use tariff "
                    "optimization, or participation "
                    "in distributed energy programs."
                )
        })

    # =====================================================
    # VPP READINESS RECOMMENDATIONS
    # =====================================================

    if vpp_analysis["vpp_score"] >= 80:

        recommendations.append({

            "category":
                "Grid Services",

            "priority":
                "High",

            "title":
                "Pursue Advanced Grid Service Integration",

            "recommendation":
                (
                    "The property demonstrates strong "
                    "technical potential for advanced "
                    "distributed energy participation. "
                    "The site may be suitable for "
                    "future grid-balancing programs "
                    "including frequency regulation, "
                    "peak demand reduction, demand "
                    "response aggregation, and "
                    "commercial VPP participation."
                )
        })

    # =====================================================
    # SUSTAINABILITY RECOMMENDATIONS
    # =====================================================

    if revenue["carbon_savings_tons"] > 500:

        recommendations.append({

            "category":
                "Sustainability",

            "priority":
                "Low",

            "title":
                "Leverage Sustainability Benefits",

            "recommendation":
                (
                    "The projected carbon reduction "
                    "potential may contribute "
                    "meaningfully toward corporate "
                    "ESG initiatives and sustainability "
                    "targets. The organization may "
                    "benefit from incorporating this "
                    "project into broader environmental "
                    "reporting and decarbonization "
                    "strategies."
                )
        })

    # =====================================================
    # DEFAULT RECOMMENDATION
    # =====================================================

    if len(recommendations) == 0:

        recommendations.append({

            "category":
                "General",

            "priority":
                "Low",

            "title":
                "Maintain Distributed Energy Evaluation",

            "recommendation":
                (
                    "The property demonstrates balanced "
                    "distributed energy characteristics "
                    "under current assumptions. Further "
                    "detailed engineering analysis, "
                    "load profiling, and financial "
                    "optimization may improve project "
                    "accuracy and deployment planning."
                )
        })

    return recommendations


def analyze_property(
    lat,lon
):

    # =====================================================
    # 1. GEOCODING
    # =====================================================

    # lat, lon = get_coordinates(
    #     address
    # )

    # =====================================================
    # 2. BUILDING FOOTPRINT
    # =====================================================

    building_data = fetch_building_footprint(
        lat,
        lon
    )
    if("error" in building_data):
        return building_data
    geometry = building_data["geometry"]

    building_type = building_data["building"]

    building_name = building_data["name"]

    levels = building_data["levels"]

    # =====================================================
    # 3. AREA CALCULATION
    # =====================================================

    roof_area_sqm = calculate_area_sqm(
        geometry
    )

    # =====================================================
    # 4. SOLAR IRRADIANCE
    # =====================================================

    peak_sun_hours = get_peak_sun_hours(
        lat,
        lon
    )

    # =====================================================
    # 5. PROPERTY CLASSIFICATION
    # =====================================================

    property_type = classify_property(
        roof_area_sqm,
        building_type,
        building_name,
        levels
    )

    # =====================================================
    # 6. SOLAR ESTIMATION
    # =====================================================

    solar = estimate_solar(
        roof_area_sqm,
        peak_sun_hours
    )

    # =====================================================
    # 7. BATTERY ESTIMATION
    # =====================================================

    battery = estimate_battery(
        solar[
            'daily_generation_kwh'
        ]
    )

    # =====================================================
    # 8. REVENUE ESTIMATION
    # =====================================================

    revenue = estimate_revenue(
        solar[
            'annual_generation_kwh'
        ]
    )

    # =====================================================
    # 9. VPP SCORE
    # =====================================================

    # vpp_score = calculate_vpp_score(
    #     property_type,
    #     solar[
    #         'system_capacity_kw'
    #     ],
    #     battery[
    #         'battery_mwh'
    #     ],
    #     peak_sun_hours,
    #     solar[
    #         'annual_generation_kwh'
    #     ]
    # )
    vpp_analysis = calculate_vpp_analysis(

    property_type,

    roof_area_sqm,

    solar["system_capacity_kw"],

    battery["battery_mwh"],

    peak_sun_hours,

    solar["annual_generation_kwh"]
    )
    
    report = generate_detailed_report(

    property_type,

    roof_area_sqm,

    solar,

    battery,

    revenue,

    peak_sun_hours
)
    recommendations = generate_recommendations(
    property_type,
    roof_area_sqm,
    solar,
    battery,
    revenue,
    peak_sun_hours,
    vpp_analysis
)
    # =====================================================
    # FINAL JSON RESPONSE
    # =====================================================

    return {

        "coordinates": {

            "latitude":
                lat,

            "longitude":
                lon
        },
        "executive_summary": report["executive_summary"],
        
        "solar": report["solar"],

        "battery": report["battery"],

        "financial": report["financial"],

        "property": report["property"],
        
        "vpp_analysis":
            vpp_analysis,
        "recommendations":
            recommendations
    }


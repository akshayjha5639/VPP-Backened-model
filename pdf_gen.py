from reportlab.platypus import (

    SimpleDocTemplate,

    Paragraph,

    Spacer
)

from reportlab.lib.styles import (
    getSampleStyleSheet
)

from reportlab.lib.pagesizes import A4


def generate_pdf_report(

    analysis_result,

    filename="report.pdf"
):

    # =====================================================
    # DOCUMENT SETUP
    # =====================================================

    doc = SimpleDocTemplate(

        filename,

        pagesize=A4
    )

    styles = getSampleStyleSheet()

    elements = []

    # =====================================================
    # EXTRACT DATA
    # =====================================================

    property_data = (
        analysis_result["property"]
    )

    solar = (
        analysis_result["solar"]
    )

    battery = (
        analysis_result["battery"]
    )

    revenue = (
        analysis_result["revenue"]
    )

    vpp = (
        analysis_result["vpp_analysis"]
    )

    report = (
        analysis_result["Report"]
    )

    # =====================================================
    # TITLE
    # =====================================================

    title = Paragraph(

        "AI VPP Property Intelligence Report",

        styles['Title']
    )

    elements.append(title)

    elements.append(
        Spacer(1, 25)
    )

    # =====================================================
    # EXECUTIVE SUMMARY
    # =====================================================

    summary = Paragraph(

        f"""
        <b>Executive Summary</b>
        <br/><br/>

        {report['executive_summary']}
        """,

        styles['BodyText']
    )

    elements.append(summary)

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # PROPERTY SECTION
    # =====================================================

    property_text = f"""

    <b>Property Analysis</b>
    <br/><br/>

    <b>Property Type:</b>
    {property_data['property_type']}
    <br/><br/>

    <b>Roof Area:</b>
    {property_data['roof_area_sqm']} sqm
    <br/><br/>

    <b>Building Type:</b>
    {property_data['building_type']}
    <br/><br/>

    <b>Building Name:</b>
    {property_data['building_name']}
    <br/><br/>

    <b>Building Levels:</b>
    {property_data['levels']}
    <br/><br/>

    <b>Estimated Daily Consumption:</b>
    {
        report['property_insights']
        ['estimated_daily_consumption_kwh']
    } kWh
    <br/><br/>

    <b>Consumption Methodology:</b>
    {
        report['property_insights']
        ['consumption_methodology']
    }
    """

    elements.append(

        Paragraph(

            property_text,

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # SOLAR SECTION
    # =====================================================

    solar_text = f"""

    <b>Solar Feasibility Analysis</b>
    <br/><br/>

    <b>Peak Sun Hours:</b>
    {
        report['solar_insights']
        ['peak_sun_hours']
    }
    <br/><br/>

    <b>Usable Rooftop Area:</b>
    {solar['usable_area_sqm']} sqm
    <br/><br/>

    <b>Estimated Solar Capacity:</b>
    {solar['system_capacity_kw']} kW
    <br/><br/>

    <b>Estimated Panel Count:</b>
    {solar['panel_count']}
    <br/><br/>

    <b>Daily Energy Generation:</b>
    {solar['daily_generation_kwh']} kWh
    <br/><br/>

    <b>Annual Energy Generation:</b>
    {solar['annual_generation_kwh']} kWh
    <br/><br/>

    <b>Homes Powered Equivalent:</b>
    {
        report['solar_insights']
        ['homes_powered_equivalent']
    }
    <br/><br/>

    <b>EV Charging Equivalent:</b>
    {
        report['solar_insights']
        ['ev_charging_equivalent']
    }
    <br/><br/>

    <b>Solar Insights:</b>
    {
        report['solar_insights']
        ['solar_comment']
    }
    """

    elements.append(

        Paragraph(

            solar_text,

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # BATTERY SECTION
    # =====================================================

    battery_text = f"""

    <b>Battery Storage Analysis</b>
    <br/><br/>

    <b>Battery Capacity:</b>
    {battery['battery_mwh']} MWh
    <br/><br/>

    <b>Battery Size:</b>
    {battery['battery_kwh']} kWh
    <br/><br/>

    <b>Battery Insights:</b>
    {
        report['battery_insights']
        ['battery_comment']
    }
    """

    elements.append(

        Paragraph(

            battery_text,

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # FINANCIAL SECTION
    # =====================================================

    financial_text = f"""

    <b>Financial Analysis</b>
    <br/><br/>

    <b>Annual Savings:</b>
    ${revenue['annual_savings_usd']}
    <br/><br/>

    <b>Estimated ROI:</b>
    {
        report['financial_insights']
        ['estimated_roi_years']
    } years
    <br/><br/>

    <b>Financial Insights:</b>
    {
        report['financial_insights']
        ['financial_comment']
    }
    """

    elements.append(

        Paragraph(

            financial_text,

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # ENVIRONMENT SECTION
    # =====================================================

    environment_text = f"""

    <b>Environmental Impact</b>
    <br/><br/>

    <b>Carbon Savings:</b>
    {revenue['carbon_savings_tons']} tons/year
    <br/><br/>

    <b>Equivalent Trees Planted:</b>
    {
        report['environmental_insights']
        ['tree_equivalent']
    }
    <br/><br/>

    <b>Environmental Insights:</b>
    {
        report['environmental_insights']
        ['environment_comment']
    }
    """

    elements.append(

        Paragraph(

            environment_text,

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # VPP SECTION
    # =====================================================

    services = ", ".join(
        vpp["grid_services"]
    )

    strengths = "<br/>".join(
        vpp["strengths"]
    )

    recommendations = "<br/>".join(
        vpp["recommendations"]
    )

    vpp_text = f"""

    <b>Virtual Power Plant (VPP) Analysis</b>
    <br/><br/>

    <b>VPP Score:</b>
    {vpp['vpp_score']} / 100
    <br/><br/>

    <b>Readiness Level:</b>
    {vpp['readiness_level']}
    <br/><br/>

    <b>Summary:</b>
    {vpp['summary']}
    <br/><br/>

    <b>Supported Grid Services:</b>
    <br/>
    {services}
    <br/><br/>

    <b>Key Strengths:</b>
    <br/>
    {strengths}
    <br/><br/>

    <b>Recommendations:</b>
    <br/>
    {recommendations}
    """

    elements.append(

        Paragraph(

            vpp_text,

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # FINAL FOOTER
    # =====================================================

    footer = Paragraph(

        """
        This report was automatically generated
        using the AI VPP Property Intelligence Engine.
        """,

        styles['Italic']
    )

    elements.append(footer)

    # =====================================================
    # BUILD PDF
    # =====================================================

    doc.build(elements)

    return filename
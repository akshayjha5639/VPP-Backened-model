
from reportlab.platypus import (

    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak
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
    # EXTRACT REPORT
    # =====================================================

    report = analysis_result

    vpp = analysis_result["vpp_analysis"]

    recommendations = analysis_result[
        "recommendations"
    ]

    # =====================================================
    # TITLE
    # =====================================================

    title = Paragraph(

        "AI VPP Property Intelligence Report",

        styles["Title"]
    )

    elements.append(title)

    elements.append(
        Spacer(1, 25)
    )

    # =====================================================
    # EXECUTIVE SUMMARY
    # =====================================================

    executive = report[
        "executive_summary"
    ]["summary"]

    elements.append(

        Paragraph(

            f"""
            <b>Executive Summary</b>
            <br/><br/>

            {executive.replace(chr(10), "<br/>")}
            """,

            styles["BodyText"]
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # PROPERTY SECTION
    # =====================================================

    property_section = report["property"]

    property_text = f"""

    <b>Property Analysis</b>
    <br/><br/>

    {property_section['insights']['property_comment']}
    <br/><br/>

    <b>Property Type:</b>
    {property_section['classification']['property_type']}
    <br/><br/>

    <b>Roof Area:</b>
    {property_section['classification']['roof_area_sqm']} sqm
    <br/><br/>

    <b>Estimated Daily Consumption:</b>
    {property_section['energy_profile']['estimated_daily_consumption_kwh']} kWh
    <br/><br/>

    <b>Estimated Monthly Consumption:</b>
    {property_section['energy_profile']['estimated_monthly_consumption_kwh']} kWh
    """

    elements.append(

        Paragraph(

            property_text,

            styles["BodyText"]
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # SOLAR SECTION
    # =====================================================

    solar = report["solar"]

    solar_text = f"""

    <b>Solar Analysis</b>
    <br/><br/>

    {solar['technical'].replace(chr(10), "<br/>")}
    <br/><br/>

    {solar['generation'].replace(chr(10), "<br/>")}
    <br/><br/>

    {solar['performance']['performance_summary'].replace(chr(10), "<br/>")}
    <br/><br/>

    {solar['insights']['strategic_summary'].replace(chr(10), "<br/>")}
    """

    elements.append(

        Paragraph(

            solar_text,

            styles["BodyText"]
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # BATTERY SECTION
    # =====================================================

    battery = report["battery"]

    battery_text = f"""

    <b>Battery Analysis</b>
    <br/><br/>

    {battery['storage']['storage_summary'].replace(chr(10), "<br/>")}
    <br/><br/>

    {battery['applications']['applications_summary'].replace(chr(10), "<br/>")}
    <br/><br/>

    {battery['performance']['performance_summary'].replace(chr(10), "<br/>")}
    <br/><br/>

    {battery['insights']['strategic_summary'].replace(chr(10), "<br/>")}
    """

    elements.append(

        Paragraph(

            battery_text,

            styles["BodyText"]
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # FINANCIAL SECTION
    # =====================================================

    financial = report["financial"]

    financial_text = f"""

    <b>Financial Analysis</b>
    <br/><br/>

    {financial['economics']['economics_summary'].replace(chr(10), "<br/>")}
    <br/><br/>

    {financial['savings']['savings_summary'].replace(chr(10), "<br/>")}
    <br/><br/>

    {financial['insights']['strategic_summary'].replace(chr(10), "<br/>")}
    """

    elements.append(

        Paragraph(

            financial_text,

            styles["BodyText"]
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    
    # =====================================================
    # VPP SECTION
    # =====================================================

    services = "<br/>• ".join(
        vpp["grid_services"]
    )

    strengths = "<br/>• ".join(
        vpp["strengths"]
    )

    risks = "<br/>• ".join(
        vpp["risks"]
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

    <b>Supported Grid Services</b>
    <br/>
    • {services}
    <br/><br/>

    <b>Key Strengths</b>
    <br/>
    • {strengths}
    <br/><br/>

    <b>Potential Risks</b>
    <br/>
    • {risks}
    """

    elements.append(

        Paragraph(

            vpp_text,

            styles["BodyText"]
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =====================================================
    # RECOMMENDATIONS
    # =====================================================

    recommendation_text = """

    <b>Strategic Recommendations</b>
    <br/><br/>
    """

    for rec in recommendations:

        recommendation_text += f"""

        <b>{rec['title']}</b>
        <br/>

        Priority: {rec['priority']}
        <br/><br/>

        {rec['recommendation']}
        <br/><br/>
        """

    elements.append(

        Paragraph(

            recommendation_text,

            styles["BodyText"]
        )
    )

    elements.append(
        Spacer(1, 25)
    )

    # =====================================================
    # FOOTER
    # =====================================================

    footer = Paragraph(

        """
        This report was automatically generated
        using the AI VPP Property Intelligence Engine.
        """,

        styles["Italic"]
    )

    elements.append(footer)

    # =====================================================
    # BUILD PDF
    # =====================================================

    doc.build(elements)

    return filename

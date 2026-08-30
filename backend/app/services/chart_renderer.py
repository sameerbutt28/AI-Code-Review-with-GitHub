from collections import Counter

from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Circle, Drawing, String, Wedge
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import Flowable

from app.models.schemas import CodeReviewResult

SEVERITY_LABELS = ["Critical", "High", "Medium", "Low", "Info"]
SEVERITY_HEX = ["#ef4444", "#f97316", "#eab308", "#3b82f6", "#6b7280"]

CATEGORY_PALETTE = [
    "#6366f1", "#8b5cf6", "#06b6d4", "#22c55e",
    "#f97316", "#ec4899", "#14b8a6", "#a855f7",
]

CARD_BG = HexColor("#1e1e22")
TEXT_PRIMARY = HexColor("#fafafa")
TEXT_MUTED = HexColor("#a1a1aa")
GRID_COLOR = HexColor("#3f3f46")


def _risk_color(score: int) -> HexColor:
    if score >= 75:
        return HexColor("#ef4444")
    if score >= 50:
        return HexColor("#f97316")
    if score >= 25:
        return HexColor("#eab308")
    return HexColor("#22c55e")


def _category_data(result: CodeReviewResult) -> list[tuple[str, int]]:
    counts = Counter(f.category.value.replace("_", " ").title() for f in result.findings)
    return sorted(counts.items(), key=lambda x: -x[1])


class ChartFlowable(Flowable):
    def __init__(self, drawing: Drawing, width: float, height: float):
        super().__init__()
        self.drawing = drawing
        self.width = width
        self.height = height

    def draw(self):
        renderPDF.draw(self.drawing, self.canv, 0, 0)


def _card_frame(drawing: Drawing, title: str, subtitle: str) -> None:
    w, h = drawing.width, drawing.height
    drawing.add(
        String(12, h - 18, title, fontName="Helvetica-Bold", fontSize=9, fillColor=TEXT_PRIMARY)
    )
    drawing.add(
        String(12, h - 30, subtitle, fontName="Helvetica", fontSize=7, fillColor=TEXT_MUTED)
    )


def build_severity_bar_chart(result: CodeReviewResult, width: float = 170, height: float = 200) -> Drawing:
    drawing = Drawing(width, height)
    _card_frame(drawing, "Findings by Severity", "Breakdown across risk levels")

    summary = result.summary
    values = [
        summary.critical_count,
        summary.high_count,
        summary.medium_count,
        summary.low_count,
        summary.info_count,
    ]
    max_val = max(values) if values else 1
    y_max = max(max_val + 1, 4)

    chart = VerticalBarChart()
    chart.x = 28
    chart.y = 22
    chart.width = width - 48
    chart.height = height - 72
    chart.data = [values]
    chart.categoryAxis.categoryNames = SEVERITY_LABELS
    chart.categoryAxis.labels.boxAnchor = "n"
    chart.categoryAxis.labels.angle = 0
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.fillColor = TEXT_MUTED
    chart.categoryAxis.strokeColor = GRID_COLOR
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = y_max
    chart.valueAxis.valueStep = 1
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = TEXT_MUTED
    chart.valueAxis.strokeColor = GRID_COLOR
    chart.bars.strokeColor = None
    chart.bars.strokeWidth = 0

    for i, hex_color in enumerate(SEVERITY_HEX):
        chart.bars[(0, i)].fillColor = HexColor(hex_color)

    drawing.add(chart)
    return drawing


def build_category_pie_chart(result: CodeReviewResult, width: float = 170, height: float = 200) -> Drawing:
    drawing = Drawing(width, height)
    _card_frame(drawing, "Findings by Category", "Issue type distribution")

    categories = _category_data(result)
    if not categories:
        drawing.add(
            String(width / 2, height / 2 - 10, "No data", fontName="Helvetica", fontSize=8, fillColor=TEXT_MUTED, textAnchor="middle")
        )
        return drawing

    labels, values = zip(*categories)
    pie = Pie()
    pie.x = width / 2 - 42
    pie.y = height / 2 - 52
    pie.width = 84
    pie.height = 84
    pie.data = list(values)
    pie.labels = None
    pie.slices.strokeWidth = 1
    pie.slices.strokeColor = CARD_BG

    for i in range(len(values)):
        pie.slices[i].fillColor = HexColor(CATEGORY_PALETTE[i % len(CATEGORY_PALETTE)])

    drawing.add(pie)

    legend_y = 18
    for i, (label, value) in enumerate(categories):
        color = HexColor(CATEGORY_PALETTE[i % len(CATEGORY_PALETTE)])
        dot_x = 14
        drawing.add(Circle(dot_x, legend_y, 3, fillColor=color, strokeColor=None))
        drawing.add(String(dot_x + 8, legend_y - 3, label[:18], fontName="Helvetica", fontSize=6.5, fillColor=TEXT_MUTED))
        drawing.add(String(width - 14, legend_y - 3, str(value), fontName="Helvetica-Bold", fontSize=6.5, fillColor=TEXT_PRIMARY, textAnchor="end"))
        legend_y += 11

    return drawing


def build_risk_gauge_chart(result: CodeReviewResult, width: float = 170, height: float = 200) -> Drawing:
    drawing = Drawing(width, height)
    _card_frame(drawing, "Risk Score", "Overall security posture")

    score = result.summary.risk_score
    fill_color = _risk_color(score)
    cx = width / 2
    cy = height / 2 - 18
    radius = 52

    # Background arc (semi-circle, left to right along top)
    drawing.add(Wedge(cx, cy, radius, 0, 180, fillColor=GRID_COLOR, strokeColor=None))
    sweep = (score / 100) * 180
    if sweep > 0:
        drawing.add(Wedge(cx, cy, radius, 0, sweep, fillColor=fill_color, strokeColor=None))

    # Inner cutout for donut gauge look
    drawing.add(Circle(cx, cy, radius - 14, fillColor=CARD_BG, strokeColor=None))

    drawing.add(String(cx, cy + 6, str(score), fontName="Helvetica-Bold", fontSize=22, fillColor=fill_color, textAnchor="middle"))
    drawing.add(String(cx, cy - 10, "OUT OF 100", fontName="Helvetica", fontSize=6, fillColor=TEXT_MUTED, textAnchor="middle"))
    drawing.add(String(cx - radius + 4, cy - radius + 8, "LOW", fontName="Helvetica", fontSize=6, fillColor=TEXT_MUTED))
    drawing.add(String(cx + radius - 4, cy - radius + 8, "HIGH", fontName="Helvetica", fontSize=6, fillColor=TEXT_MUTED, textAnchor="end"))

    return drawing


def build_dashboard_flowables(result: CodeReviewResult, chart_width: float = 2.15 * 72) -> list[Flowable]:
    chart_h = 200
    charts = [
        ChartFlowable(build_severity_bar_chart(result, chart_width, chart_h), chart_width, chart_h),
        ChartFlowable(build_category_pie_chart(result, chart_width, chart_h), chart_width, chart_h),
        ChartFlowable(build_risk_gauge_chart(result, chart_width, chart_h), chart_width, chart_h),
    ]
    return charts

import json
import struct
import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.schemas import ReportAnalysis


@dataclass(frozen=True)
class DemoReport:
    report_id: str
    age_hours: int
    description: str
    latitude: float
    longitude: float
    analysis: ReportAnalysis
    urban_context: dict
    has_image: bool = False


@dataclass(frozen=True)
class DemoStatus:
    report_id: str
    status: str
    note: str
    hours_after_report: int


def analysis(
    category: str,
    severity: int,
    confidence: float,
    summary: str,
    recommendation: str,
    priority: str,
    impact: str,
    evidence: list[str],
    uncertainty: list[str],
) -> ReportAnalysis:
    return ReportAnalysis(
        category=category,
        severity=severity,
        confidence=confidence,
        summary=summary,
        recommendation=recommendation,
        priority=priority,
        estimated_impact=impact,
        evidence=evidence,
        uncertainty=uncertainty,
    )


HANOI_CONTEXT = {
    "weather": {
        "available": True,
        "condition": "Rain",
        "description": "light rain",
        "temperature_c": 28.0,
        "humidity": 88,
        "wind_speed": 2.7,
        "rain_1h": 1.4,
        "source": "synthetic_demo",
    },
    "place": {
        "available": True,
        "display_name": "Hoan Kiem District, Hanoi, Vietnam",
        "category": "place",
        "type": "district",
        "address": {"city": "Hanoi", "country": "Vietnam"},
        "source": "synthetic_demo",
    },
}


REPORTS = [
    DemoReport(
        "demo-001-pothole-school",
        2,
        "A deep pothole is forcing motorbikes into the opposite lane near a school gate.",
        21.0285,
        105.8542,
        analysis(
            "pothole", 3, 0.91,
            "A road defect near a school is disrupting traffic flow.",
            "Inspect within 24 hours, mark the hazard, and schedule a road repair.",
            "medium", "Students, motorbike riders, and local traffic may be affected.",
            ["The report identifies a deep pothole and lane deviation."],
            ["Pothole dimensions are not independently verified."],
        ),
        HANOI_CONTEXT,
    ),
    DemoReport(
        "demo-002-flooded-street",
        30,
        "Flood water is rising across a residential street after sustained rain.",
        21.0301,
        105.8499,
        analysis(
            "flooding", 5, 0.94,
            "Rising flood water may cut access to homes and create immediate danger.",
            "Dispatch drainage and safety teams, restrict access, and monitor water depth.",
            "critical", "Residents, homes, and emergency access are at risk.",
            ["The report states water is rising.", "Demo weather context records rain."],
            ["Exact water depth and flow speed are unknown."],
        ),
        HANOI_CONTEXT,
    ),
    DemoReport(
        "demo-003-traffic-signal",
        5,
        "The traffic signal is dark at a busy four-way intersection.",
        21.0277,
        105.8511,
        analysis(
            "other", 4, 0.89,
            "A failed traffic signal creates a collision risk at a busy junction.",
            "Send traffic control immediately and dispatch an electrical repair crew.",
            "high", "Drivers, cyclists, and pedestrians crossing the junction are exposed.",
            ["The signal is reported completely dark."],
            ["Traffic volume has not been measured."],
        ),
        HANOI_CONTEXT,
    ),
    DemoReport(
        "demo-004-market-waste",
        8,
        "Garbage bins are overflowing beside the public market entrance.",
        21.0312,
        105.8468,
        analysis(
            "waste", 2, 0.93,
            "Overflowing market waste is obstructing the public area.",
            "Schedule collection today and inspect whether more bins are needed.",
            "medium", "Market users may face odor, pests, and blocked access.",
            ["Overflowing bins are reported at a high-use entrance."],
            ["Waste volume and duration are unknown."],
        ),
        HANOI_CONTEXT,
    ),
    DemoReport(
        "demo-005-dark-walkway",
        12,
        "Two streetlights are broken along a dark pedestrian walkway.",
        21.0254,
        105.8581,
        analysis(
            "streetlight", 3, 0.88,
            "Multiple failed lights reduce visibility on a pedestrian route.",
            "Inspect the lighting circuit and repair the failed fixtures before nightfall.",
            "medium", "Pedestrians face reduced visibility and personal-safety concerns.",
            ["Two adjacent streetlights are reported broken."],
            ["Ambient lighting and pedestrian volume are unknown."],
        ),
        HANOI_CONTEXT,
    ),
    DemoReport(
        "demo-006-fallen-tree",
        16,
        "A fallen tree is blocking most of a narrow access road.",
        21.0222,
        105.8533,
        analysis(
            "obstruction", 4, 0.92,
            "A fallen tree is restricting road and possible emergency access.",
            "Secure the area and dispatch a tree-removal crew with traffic support.",
            "high", "Residents and emergency vehicles may lose reliable access.",
            ["The report states most of the road is blocked."],
            ["Tree stability and utility-line involvement are unknown."],
        ),
        HANOI_CONTEXT,
    ),
    DemoReport(
        "demo-007-river-dumping",
        22,
        "Several bags of construction waste were dumped near the river bank.",
        21.0199,
        105.8500,
        analysis(
            "waste", 2, 0.84,
            "Illegal construction waste is present near a sensitive water edge.",
            "Document the site, arrange removal, and refer evidence for enforcement review.",
            "low", "The site may create localized pollution and access problems.",
            ["Construction-waste bags are reported near the river."],
            ["Material contents and responsible party are unknown."],
        ),
        HANOI_CONTEXT,
    ),
    DemoReport(
        "demo-008-open-manhole",
        3,
        "An uncovered manhole is open in the motorbike lane after heavy rain.",
        21.0266,
        105.8555,
        analysis(
            "other", 5, 0.97,
            "An open manhole in an active lane presents immediate injury risk.",
            "Barricade the lane immediately and dispatch a utility crew to restore the cover.",
            "critical", "Motorbike riders and pedestrians face severe injury risk.",
            ["The opening is reported uncovered in the motorbike lane."],
            ["The manhole depth and ownership are not verified."],
        ),
        HANOI_CONTEXT,
        has_image=True,
    ),
    DemoReport(
        "demo-009-unsafe-crossing",
        26,
        "The zebra crossing paint has disappeared outside a community clinic.",
        21.0242,
        105.8475,
        analysis(
            "other", 3, 0.87,
            "A faded crossing reduces pedestrian visibility near a clinic.",
            "Inspect traffic conditions and schedule crossing repainting with warning signs.",
            "high", "Patients, older adults, and other pedestrians may be affected.",
            ["Crossing markings are reported no longer visible."],
            ["Vehicle speed and crossing demand are unknown."],
        ),
        HANOI_CONTEXT,
    ),
    DemoReport(
        "demo-010-blocked-drain",
        10,
        "A roadside drain is blocked and water is pooling into the traffic lane.",
        21.0293,
        105.8570,
        analysis(
            "flooding", 4, 0.90,
            "A blocked drain is causing active road flooding during rain.",
            "Clear the drain promptly and inspect the downstream drainage segment.",
            "high", "Road users and nearby properties may face worsening flooding.",
            ["Pooling water and a blocked drain are reported together.", "Demo context records rain."],
            ["Blockage material and downstream capacity are unknown."],
        ),
        HANOI_CONTEXT,
    ),
]


STATUS_EVENTS = [
    DemoStatus("demo-002-flooded-street", "reviewing", "Drainage team dispatched.", 1),
    DemoStatus("demo-002-flooded-street", "resolved", "Drain cleared; water receded.", 12),
    DemoStatus("demo-006-fallen-tree", "reviewing", "Removal crew assigned.", 2),
    DemoStatus("demo-008-open-manhole", "reviewing", "Temporary barrier installed.", 1),
]


def build_report_rows(
    now: datetime | None = None,
    image_uri: str | None = None,
) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    rows = []
    for report in REPORTS:
        rows.append(
            {
                "report_id": report.report_id,
                "created_at": (now - timedelta(hours=report.age_hours)).isoformat(),
                "description": report.description,
                "latitude": report.latitude,
                "longitude": report.longitude,
                "urban_context": json.dumps(report.urban_context, ensure_ascii=False),
                "image_gcs_uri": image_uri if report.has_image else None,
                **report.analysis.model_dump(mode="json"),
            }
        )
    return rows


def build_status_rows(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    ages = {report.report_id: report.age_hours for report in REPORTS}
    return [
        {
            "report_id": event.report_id,
            "status": event.status,
            "note": event.note,
            "created_at": (
                now
                - timedelta(hours=ages[event.report_id])
                + timedelta(hours=event.hours_after_report)
            ).isoformat(),
        }
        for event in STATUS_EVENTS
    ]


def demo_evidence_png(width: int = 320, height: int = 180) -> bytes:
    pixels = [bytearray((70, 80, 90) * width) for _ in range(height)]

    def rect(x1, y1, x2, y2, color):
        for y in range(max(0, y1), min(height, y2)):
            for x in range(max(0, x1), min(width, x2)):
                offset = x * 3
                pixels[y][offset : offset + 3] = bytes(color)

    rect(0, 0, width, 68, (145, 165, 175))
    rect(0, 68, width, height, (65, 70, 75))
    rect(0, 125, width, 132, (205, 190, 80))
    rect(35, 26, 108, 68, (195, 185, 165))
    rect(48, 38, 61, 68, (75, 95, 105))
    rect(80, 38, 94, 68, (75, 95, 105))
    for y in range(84, 145):
        for x in range(118, 206):
            dx = (x - 162) / 44
            dy = (y - 114) / 30
            if dx * dx + dy * dy <= 1:
                offset = x * 3
                pixels[y][offset : offset + 3] = b"\x16\x18\x1a"
    rect(105, 79, 219, 85, (225, 135, 35))
    rect(105, 145, 219, 151, (225, 135, 35))
    rect(105, 79, 111, 151, (225, 135, 35))
    rect(213, 79, 219, 151, (225, 135, 35))

    raw = b"".join(b"\x00" + bytes(row) for row in pixels)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def demo_summary() -> dict:
    priorities = {}
    severities = {}
    for report in REPORTS:
        priority = report.analysis.priority.value
        priorities[priority] = priorities.get(priority, 0) + 1
        severities[report.analysis.severity] = severities.get(report.analysis.severity, 0) + 1
    return {
        "reports": len(REPORTS),
        "status_events": len(STATUS_EVENTS),
        "images": sum(report.has_image for report in REPORTS),
        "urban_context_reports": sum(bool(report.urban_context) for report in REPORTS),
        "priorities": priorities,
        "severities": severities,
    }

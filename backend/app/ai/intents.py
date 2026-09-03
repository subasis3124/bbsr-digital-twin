import re
from typing import Tuple, List, Dict, Any, Optional
from backend.app.ai.schemas import AIIntentEnum


INTENT_PATTERNS: List[Tuple[AIIntentEnum, List[str]]] = [
    (
        AIIntentEnum.EXPLANATION_QUERY,
        [
            r"\bwhy\b", r"\bexplain\b", r"\bshap\b", r"\battribut(ion|ed)\b",
            r"\bcause\b", r"\breason\b"
        ]
    ),
    (
        AIIntentEnum.SIMULATION_QUERY,
        [
            r"\bsimulat(e|ion|ing)\b", r"\bheavy rainfall\b", r"\broad closure\b",
            r"\brainfall (increase|surge)\b", r"\bwhat happens if\b", r"\bscenario\b",
            r"\bclose (this|a|the) road\b", r"\bpollution surge\b"
        ]
    ),
    (
        AIIntentEnum.OPTIMIZATION_QUERY,
        [
            r"\boptimi(ze|zation)\b", r"\ballocat(e|ion)\b", r"\bnearest resource\b",
            r"\bdispatch\b", r"\bassign hospital\b", r"\bor-tools\b"
        ]
    ),
    (
        AIIntentEnum.FLOOD_RISK_QUERY,
        [
            r"\bflood\b", r"\bflood-risk\b", r"\binundat(ion|ed)\b", r"\bwaterlogg(ed|ing)\b",
            r"\bhigh risk\b", r"\brisk level\b", r"\bcell\b"
        ]
    ),
    (
        AIIntentEnum.TRAFFIC_QUERY,
        [
            r"\btraffic\b", r"\bcongest(ion|ed)?\b", r"\bspeed\b", r"\bgnn\b",
            r"\bvehicle\b", r"\broad segment\b", r"\bjam\b", r"\bforecast traffic\b"
        ]
    ),
    (
        AIIntentEnum.AIR_QUALITY_QUERY,
        [
            r"\bair quality\b", r"\baqi\b", r"\bpm2\.?5\b", r"\bpm10\b",
            r"\bpollut(ion|ant)\b", r"\bno2\b", r"\bso2\b", r"\bco\b", r"\bo3\b"
        ]
    ),
    (
        AIIntentEnum.RESOURCE_QUERY,
        [
            r"\bhospital\b", r"\bpolice\b", r"\bfire station\b", r"\bbed capacity\b",
            r"\bemergency resource\b", r"\bambulance\b"
        ]
    ),
    (
        AIIntentEnum.INFRASTRUCTURE_QUERY,
        [
            r"\broad\b", r"\bward\b", r"\bbus stop\b", r"\bbus route\b",
            r"\bwater bod(y|ies)\b", r"\bbuilding\b", r"\bschool\b"
        ]
    ),
    (
        AIIntentEnum.CITY_STATE_QUERY,
        [
            r"\bcity state\b", r"\bstate engine\b", r"\bspatiotemporal\b",
            r"\boverall state\b", r"\bcanonical state\b"
        ]
    ),
    (
        AIIntentEnum.SYSTEM_STATUS_QUERY,
        [
            r"\bsystem status\b", r"\bhealth\b", r"\bkpi\b", r"\bdashboard summary\b",
            r"\boverview\b", r"\bstatus\b", r"\bhow many\b"
        ]
    ),
    (
        AIIntentEnum.COMPARISON_QUERY,
        [
            r"\bcompar(e|ison)\b", r"\bdifference\b", r"\bversus\b", r"\bvs\b",
            r"\bbefore and after\b"
        ]
    ),
    (
        AIIntentEnum.SPATIAL_QUERY,
        [
            r"\bwhere\b", r"\bnear\b", r"\baround\b", r"\bclose to\b",
            r"\bward \d+\b", r"\bkiit\b", r"\bairport\b"
        ]
    ),
    (
        AIIntentEnum.GENERAL_PROJECT_QUERY,
        [
            r"\bwhat is (this|bhubaneswar digital twin)\b", r"\bwho are you\b",
            r"\bhelp\b", r"\bcapabilities\b", r"\bwhat can you do\b"
        ]
    )
]


def classify_intent(query: str) -> AIIntentEnum:
    """
    Deterministically classifies query string into an AIIntentEnum.
    Returns AIIntentEnum.UNKNOWN if no intent pattern matches.
    """
    q_lower = query.lower().strip()
    
    for intent, patterns in INTENT_PATTERNS:
        for pat in patterns:
            if re.search(pat, q_lower):
                return intent

    return AIIntentEnum.UNKNOWN

"""QTI 3.0 namespace vocabulary shared by the Exam.net item builders.

Purpose:
    Own the namespace identifiers, schema locations and element-name helpers so
    the declaration builder and the inline prompt renderer share one vocabulary
    without importing each other.

Relationships:
    - Imported by `examnet_qti_xml` and `examnet_qti_inline_prompt`.
    - Re-exported by `examnet_qti_xml` for its existing callers.
"""

from __future__ import annotations

QTI_NAMESPACE = "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
QTI_SCHEMA_LOCATION = (
    "http://www.imsglobal.org/xsd/imsqtiasi_v3p0 "
    "https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqti_asiv3p0p1_v1p0.xsd"
)
MAP_RESPONSE_TEMPLATE = "https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/map_response.xml"
MATCH_CORRECT_TEMPLATE = "https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"


def qti_tag(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def xsi_tag(local_name: str) -> str:
    return f"{{{XSI_NAMESPACE}}}{local_name}"

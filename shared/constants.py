"""Shared constants used by both API and MCP server."""

VALID_SECTION_TYPES = {
    "overview", "tech_spec", "data_model", "api_spec", "ui_design",
    "architecture", "deployment", "security", "testing", "timeline", "general",
}

SECTION_TYPE_ALIASES = {
    "requirement": "general",
    "requirements": "general",
    "functional_requirements": "tech_spec",
    "non_functional_requirements": "tech_spec",
    "api": "api_spec",
    "data": "data_model",
    "ui": "ui_design",
    "ux": "ui_design",
    "roadmap": "timeline",
}

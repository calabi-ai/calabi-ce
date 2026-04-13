# =============================================================================
# Calabi ExamIQ BI — Superset Configuration
# =============================================================================
# Branded configuration for Calabi Community Edition
# Mounted at /app/pythonpath/superset_config.py

import os

# ── Branding ──────────────────────────────────────────────────────────────────
APP_NAME = "Calabi Analytics"
APP_ICON = "/static/assets/calabi-icon.png"
APP_ICON_WIDTH = 32
FAVICONS = [{"href": "/static/assets/calabi-favicon.svg"}]

# Hide Superset branding
SHOW_STACKTRACE = False
MENU_HIDE_USER_INFO = False

# ── Theme ─────────────────────────────────────────────────────────────────────
THEME_OVERRIDES = {
    "borderRadius": 8,
    "colors": {
        "primary": {
            "base": "#7c3aed",
            "dark1": "#6d28d9",
            "dark2": "#5b21b6",
            "light1": "#8b5cf6",
            "light2": "#a78bfa",
            "light3": "#c4b5fd",
            "light4": "#ddd6fe",
            "light5": "#ede9fe",
        },
        "secondary": {
            "base": "#1e1b4b",
            "dark1": "#0f0e26",
            "dark2": "#070714",
            "dark3": "#030310",
            "light1": "#312e81",
            "light2": "#3730a3",
            "light3": "#4338ca",
            "light4": "#4f46e5",
            "light5": "#6366f1",
        },
    },
}

# ── Custom CSS (purple Calabi theme) ──────────────────────────────────────────
EXTRA_SEQUENTIAL_COLOR_SCHEMES = []
EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": "calabi",
        "description": "Calabi Platform Colors",
        "label": "Calabi",
        "isDefault": True,
        "colors": [
            "#7c3aed", "#2563eb", "#059669", "#d97706", "#db2777",
            "#4f46e5", "#0891b2", "#65a30d", "#c026d3", "#ea580c",
        ],
    }
]

# Custom CSS to inject Calabi branding
CUSTOM_CSS = """
/* ── Calabi Theme Override ──────────────────────── */
.navbar-brand {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}

/* Add "calabi" text after the logo icon */
.navbar-brand::after {
    content: "calabi";
    font-size: 20px !important;
    font-weight: 800 !important;
    color: #1e1b4b !important;
    letter-spacing: -0.5px !important;
    font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Login page branding */
.login-form .panel-heading {
    background: linear-gradient(135deg, #1e1b4b 0%, #7c3aed 100%) !important;
    color: white !important;
    text-align: center !important;
    padding: 24px !important;
    border-radius: 8px 8px 0 0 !important;
}

.login-form .panel-heading::after {
    content: "Calabi Analytics" !important;
    display: block !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    margin-top: 8px !important;
}

/* Sidebar */
.ant-layout-sider,
#app-menu {
    background: #1e1b4b !important;
}

/* Top navigation */
.navbar-default,
.ant-layout-header {
    background: linear-gradient(135deg, #1e1b4b, #4c1d95) !important;
}

/* Primary buttons */
.ant-btn-primary,
.btn-primary {
    background: #7c3aed !important;
    border-color: #7c3aed !important;
}

.ant-btn-primary:hover,
.btn-primary:hover {
    background: #6d28d9 !important;
    border-color: #6d28d9 !important;
}

/* Links */
a {
    color: #7c3aed;
}

a:hover {
    color: #6d28d9;
}

/* Tab active */
.ant-tabs-tab-active .ant-tabs-tab-btn {
    color: #7c3aed !important;
}

.ant-tabs-ink-bar {
    background: #7c3aed !important;
}

/* Hide "Powered by Apache Superset" footer text */
.footer,
[class*="powered"],
[class*="Powered"] {
    display: none !important;
}
"""

# ── Database ──────────────────────────────────────────────────────────────────
# Use Superset's built-in env var handling (avoids psycopg2 import issues)
# Connection is configured via DATABASE_* env vars in docker-compose

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "calabi-ce-secret-change-me-in-prod")

# ── Feature flags ─────────────────────────────────────────────────────────────
FEATURE_FLAGS = {
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    "ENABLE_EXPLORE_DRAG_AND_DROP": True,
    "EMBEDDED_SUPERSET": False,
}

# ── CE Auth: Auto-login via FLASK_APP_MUTATOR ────────────────────────────────
# For CE, auto-login as admin on every request using a before_request hook.
# This is the simplest and most reliable approach — no login page needed.

from flask_appbuilder.security.manager import AUTH_DB
from flask_login import login_user

AUTH_TYPE = AUTH_DB

# Disable CSRF and CSP for CE
WTF_CSRF_ENABLED = False
CONTENT_SECURITY_POLICY_WARNING = False
TALISMAN_ENABLED = False

# Public role fallback
PUBLIC_ROLE_LIKE = "Admin"

def FLASK_APP_MUTATOR(app):
    """Auto-login as admin on every request for CE."""
    @app.before_request
    def auto_login():
        from flask_login import current_user
        if not current_user.is_authenticated:
            from superset.extensions import security_manager
            admin_user = security_manager.find_user(username="admin")
            if admin_user:
                login_user(admin_user, remember=True)

# ── CE Edition marker ────────────────────────────────────────────────────────
CALABI_EDITION = os.environ.get("CALABI_EDITION", "community")

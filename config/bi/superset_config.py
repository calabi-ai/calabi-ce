# =============================================================================
# CalabiIQ Analytics — Configuration
# =============================================================================

import os
from flask_appbuilder.security.manager import AUTH_DB
from flask_login import login_user

# ── Branding ──────────────────────────────────────────────────────────────────
APP_NAME = "CalabiIQ"
APP_ICON = "/static/assets/calabi-logo.svg"
APP_ICON_WIDTH = 160
FAVICONS = [{"href": "/static/assets/calabi-favicon.svg"}]
LOGO_TARGET_PATH = "/"
LOGO_TOOLTIP = "CalabiIQ Analytics"

# ── Theme (Calabi purple) ──────────────────────────────────────────────────────
THEME_OVERRIDES = {
    "borderRadius": 6,
    "colors": {
        "primary": {
            "base":   "#7c3aed",
            "dark1":  "#6d28d9",
            "dark2":  "#5b21b6",
            "light1": "#8b5cf6",
            "light2": "#a78bfa",
            "light3": "#c4b5fd",
            "light4": "#ddd6fe",
            "light5": "#ede9fe",
        },
        "secondary": {
            "base":   "#1e1b4b",
            "dark1":  "#0f0e26",
            "dark2":  "#070714",
            "dark3":  "#030310",
            "light1": "#312e81",
            "light2": "#3730a3",
            "light3": "#4338ca",
            "light4": "#4f46e5",
            "light5": "#6366f1",
        },
        "grayscale": {
            "base":   "#666666",
            "dark1":  "#323232",
            "dark2":  "#000000",
            "light1": "#b2b2b2",
            "light2": "#e0e0e0",
            "light3": "#f0f0f0",
            "light4": "#f7f7f7",
            "light5": "#ffffff",
        },
    },
    "typography": {
        "families": {
            "sansSerif": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            "serif": "Georgia, serif",
            "monospace": "'Fira Code', 'Cascadia Code', 'Courier New', monospace",
        },
        "weights": {
            "light": 300,
            "normal": 400,
            "bold": 600,
            "strongBold": 800,
        },
    },
}

# ── Color schemes ─────────────────────────────────────────────────────────────
EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": "calabi",
        "description": "Calabi Platform",
        "label": "Calabi",
        "isDefault": True,
        "colors": [
            "#7c3aed", "#2563eb", "#059669", "#d97706", "#db2777",
            "#4f46e5", "#0891b2", "#65a30d", "#c026d3", "#ea580c",
        ],
    }
]
EXTRA_SEQUENTIAL_COLOR_SCHEMES = []

# ── Custom CSS ────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
/* =====================================================================
   CalabiIQ Analytics — Superset 4.1.1 Theme
   Calabi brand: navy #1e1b4b · purple #7c3aed · Inter font
   ===================================================================== */

/* ── Global font ── */
*, *::before, *::after {
    font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* =================================================================
   TOP NAVBAR  — white background, full-color Calabi logo
   ================================================================= */
.navbar,
.navbar-default,
.navbar-fixed-top,
.navbar-static-top {
    background-color: #ffffff !important;
    background-image: none !important;
    border: none !important;
    border-bottom: 2px solid #ede9fe !important;
    box-shadow: 0 1px 6px rgba(124, 58, 237, 0.08) !important;
}

/* ── Logo / brand — show full-color logo, no invert ── */
.navbar-brand {
    padding: 8px 20px !important;
}
.navbar-brand img {
    height: 36px !important;
    width: auto !important;
    filter: none !important;
    opacity: 1 !important;
}
/* Hide text next to logo if it renders */
.navbar-brand span { display: none !important; }

/* ── Nav links ── */
.navbar-default .navbar-nav > li > a,
.navbar-default .navbar-nav > li > a:focus {
    color: #374151 !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 20px 16px !important;
    background: transparent !important;
}
.navbar-default .navbar-nav > li > a:hover {
    color: #7c3aed !important;
    background: rgba(124, 58, 237, 0.06) !important;
}
.navbar-default .navbar-nav > li.active > a,
.navbar-default .navbar-nav > li.active > a:focus,
.navbar-default .navbar-nav > li.active > a:hover {
    color: #7c3aed !important;
    background: transparent !important;
    border-bottom: 3px solid #7c3aed !important;
}
/* Ant Design menu inside navbar */
.navbar-default .ant-menu,
.navbar-default .ant-menu-horizontal {
    background: transparent !important;
    border-bottom: none !important;
    line-height: 60px !important;
}
.navbar-default .ant-menu-item,
.navbar-default .ant-menu-submenu-title {
    color: #374151 !important;
    font-weight: 500 !important;
}
.navbar-default .ant-menu-item:hover,
.navbar-default .ant-menu-submenu:hover > .ant-menu-submenu-title {
    color: #7c3aed !important;
}
.navbar-default .ant-menu-item-selected,
.navbar-default .ant-menu-item-active {
    color: #7c3aed !important;
    border-bottom: 3px solid #7c3aed !important;
}

/* Right-side icons */
.navbar-default .navbar-right a,
.navbar-default .navbar-right .ant-btn {
    color: #374151 !important;
}
.navbar-default .navbar-right a:hover,
.navbar-default .navbar-right .ant-btn:hover {
    color: #7c3aed !important;
}

/* =================================================================
   BUTTONS
   ================================================================= */
/* Primary */
.ant-btn-primary,
.btn-primary,
button[type="submit"] {
    background: #7c3aed !important;
    border-color: #7c3aed !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    box-shadow: 0 1px 4px rgba(124, 58, 237, 0.3) !important;
}
.ant-btn-primary:hover, .btn-primary:hover,
.ant-btn-primary:focus, .btn-primary:focus {
    background: #6d28d9 !important;
    border-color: #6d28d9 !important;
    color: #ffffff !important;
}

/* Toggle button groups — Home page Favourite / Mine / All */
.ant-radio-button-wrapper {
    border-color: #d8b4fe !important;
    color: #7c3aed !important;
    font-weight: 500 !important;
}
.ant-radio-button-wrapper:first-child { border-radius: 6px 0 0 6px !important; }
.ant-radio-button-wrapper:last-child  { border-radius: 0 6px 6px 0 !important; }
.ant-radio-button-wrapper-checked,
.ant-radio-button-wrapper-checked:not(.ant-radio-button-wrapper-disabled) {
    background: #7c3aed !important;
    border-color: #7c3aed !important;
    color: #ffffff !important;
    box-shadow: -1px 0 0 0 #7c3aed !important;
}
.ant-radio-button-wrapper-checked:not(.ant-radio-button-wrapper-disabled)::before {
    background: #7c3aed !important;
}
.ant-radio-button-wrapper:hover:not(.ant-radio-button-wrapper-checked) {
    color: #6d28d9 !important;
}

/* =================================================================
   LINKS & TABS
   ================================================================= */
a { color: #7c3aed !important; }
a:hover { color: #6d28d9 !important; }

.ant-tabs-tab-active .ant-tabs-tab-btn,
.ant-tabs-tab-active { color: #7c3aed !important; }
.ant-tabs-ink-bar { background: #7c3aed !important; }
.ant-tabs-tab:hover { color: #6d28d9 !important; }

/* =================================================================
   FORM CONTROLS
   ================================================================= */
.ant-select-focused .ant-select-selector,
.ant-select:hover .ant-select-selector,
.ant-input:focus, .ant-input-focused,
.ant-input:hover {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.12) !important;
}
.ant-checkbox-checked .ant-checkbox-inner,
.ant-radio-checked .ant-radio-inner {
    background: #7c3aed !important;
    border-color: #7c3aed !important;
}
.ant-switch-checked {
    background: #7c3aed !important;
}

/* =================================================================
   DASHBOARD & CHARTS
   ================================================================= */
[class*="dashboard-header"],
[class*="DashboardHeader"] {
    border-bottom: 2px solid #7c3aed !important;
}
.dashboard-component-chart-holder,
[class*="ChartHolder"],
[class*="chart-slice"] {
    border-radius: 8px !important;
    box-shadow: 0 1px 6px rgba(0,0,0,0.07) !important;
}

/* =================================================================
   SQL LAB
   ================================================================= */
.ace_editor { border-radius: 6px !important; font-size: 13px !important; }
.ace_gutter { background: #f4f4f8 !important; color: #888 !important; }

/* =================================================================
   TABLE ROW — selected / hover highlight (purple, not blue)
   ================================================================= */
.ant-table-tbody > tr.ant-table-row-selected > td,
.ant-table-tbody > tr.ant-table-row-selected:hover > td {
    background: rgba(124, 58, 237, 0.10) !important;
    border-color: rgba(124, 58, 237, 0.18) !important;
}
.ant-table-tbody > tr:hover > td {
    background: rgba(124, 58, 237, 0.06) !important;
}

/* =================================================================
   HIDE SUPERSET BRANDING
   ================================================================= */
.footer,
[class*="powered-by"],
[data-test="footer"] {
    display: none !important;
}
"""

# ── SQL Lab ───────────────────────────────────────────────────────────────────
SQLLAB_TIMEOUT = 300
SQLLAB_ASYNC_TIME_LIMIT_SEC = 60 * 60
SQL_MAX_ROW = 100000
SQL_QUERY_MUTATOR = None

# ── Database ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "calabi-ce-secret-change-me-in-prod")

# Use Postgres as metadata DB (more reliable than SQLite — fixes SQL Lab async issues)
_db_user = os.environ.get("DATABASE_USER", "calabi")
_db_pass = os.environ.get("DATABASE_PASSWORD", "calabi_ce_2025")
_db_host = os.environ.get("DATABASE_HOST", "postgres")
_db_port = os.environ.get("DATABASE_PORT", "5432")
_db_name = os.environ.get("DATABASE_DB", "calabi_bi")
SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{_db_user}:{_db_pass}@{_db_host}:{_db_port}/{_db_name}"

# ── Security ──────────────────────────────────────────────────────────────────
WTF_CSRF_ENABLED = False
CONTENT_SECURITY_POLICY_WARNING = False
TALISMAN_ENABLED = False
PUBLIC_ROLE_LIKE = "Admin"
SHOW_STACKTRACE = False

# ── Feature flags ─────────────────────────────────────────────────────────────
FEATURE_FLAGS = {
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    "ENABLE_EXPLORE_DRAG_AND_DROP": True,
    "EMBEDDED_SUPERSET": False,
    "SQLLAB_BACKEND_PERSISTENCE": True,
    "ENABLE_JAVASCRIPT_CONTROLS": False,
}

# ── Auth: Auto-login ──────────────────────────────────────────────────────────
AUTH_TYPE = AUTH_DB

def FLASK_APP_MUTATOR(app):
    @app.before_request
    def auto_login():
        from flask_login import current_user
        if not current_user.is_authenticated:
            from superset.extensions import security_manager
            admin_user = security_manager.find_user(username="admin")
            if admin_user:
                login_user(admin_user, remember=True)

CALABI_EDITION = os.environ.get("CALABI_EDITION", "community")

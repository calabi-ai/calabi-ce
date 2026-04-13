#!/bin/sh
# =============================================================================
# Calabi CE — Post-startup Setup
# =============================================================================
# Runs after catalogue is healthy. Creates CE admin user and loads sample data.
# Idempotent — safe to run multiple times.
# =============================================================================

CATALOGUE_URL="http://calabi-catalogue:8585"

echo "╔══════════════════════════════════════════════╗"
echo "║  Calabi CE — Setting up...                    ║"
echo "╚══════════════════════════════════════════════╝"

# Install curl (alpine comes with wget only)
apk add --no-cache curl > /dev/null 2>&1

# Wait for catalogue to be ready
echo "Waiting for Calabi Catalogue..."
for i in $(seq 1 120); do
  if wget -q --spider "$CATALOGUE_URL/api/v1/system/version" 2>/dev/null; then
    echo "  Catalogue ready."
    break
  fi
  sleep 5
done

# Get admin token
echo "Authenticating..."
TOKEN=$(curl -s "$CATALOGUE_URL/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@open-metadata.org","password":"YWRtaW4="}' 2>/dev/null \
  | sed -n 's/.*"accessToken":"\([^"]*\)".*/\1/p')

if [ -z "$TOKEN" ]; then
  echo "ERROR: Could not get admin token. Exiting."
  exit 1
fi
echo "  Authenticated."

# Helper function for API calls
api_post() {
  local path="$1"
  local data="$2"
  curl -s "$CATALOGUE_URL$path" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$data" 2>/dev/null
}

api_get() {
  local path="$1"
  curl -s "$CATALOGUE_URL$path" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null
}

# ── Create CE Admin User ─────────────────────────────────────────────
echo ""
echo "Creating CE admin user..."

EXISTING=$(api_get "/api/v1/users/name/ce-admin" | grep -o '"email"')

if [ -n "$EXISTING" ]; then
  echo "  CE admin already exists. Skipping."
else
  # OM signup API uses plain password field (RegistrationRequest schema)
  # Password must meet complexity: 8+ chars, upper, lower, digit, special
  SIGNUP_RESULT=$(curl -s "$CATALOGUE_URL/api/v1/users/signup" \
    -H "Content-Type: application/json" \
    -d '{"firstName":"Calabi","lastName":"Admin","email":"ce-admin@calabi.dev","password":"Calabi@CE2025!"}' \
    2>/dev/null)

  USERID=$(api_get "/api/v1/users/name/ce-admin" \
    | sed -n 's/.*"id":"\([^"]*\)".*/\1/p' | head -1)

  if [ -n "$USERID" ]; then
    curl -s "$CATALOGUE_URL/api/v1/users/$USERID" \
      -X PATCH \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json-patch+json" \
      -d '[{"op":"replace","path":"/isAdmin","value":true},{"op":"replace","path":"/displayName","value":"CalabiAdmin"}]' \
      2>/dev/null > /dev/null
    echo "  CE admin created: ce-admin@calabi.dev"
  else
    echo "  WARNING: Could not create CE admin user."
  fi
fi

# ── Re-authenticate as CE admin + hide default OM admin ──────────────
echo ""
echo "Securing admin accounts..."

# Re-auth as CE admin for remaining operations
CE_TOKEN=$(curl -s "$CATALOGUE_URL/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"ce-admin@calabi.dev","password":"Q2FsYWJpQENFMjAyNSE="}' 2>/dev/null \
  | sed -n 's/.*"accessToken":"\([^"]*\)".*/\1/p')

if [ -n "$CE_TOKEN" ]; then
  TOKEN="$CE_TOKEN"
  echo "  Switched to CE admin token."
fi

# Disable the default OM admin account (hide open-metadata.org branding)
OM_ADMIN_ID=$(api_get "/api/v1/users/name/admin" \
  | sed -n 's/.*"id":"\([^"]*\)".*/\1/p' | head -1)

if [ -n "$OM_ADMIN_ID" ]; then
  # Soft-delete (disable) the default admin — keeps it for bootstrap but hides from UI
  curl -s "$CATALOGUE_URL/api/v1/users/$OM_ADMIN_ID" \
    -X DELETE \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null > /dev/null
  echo "  Default admin account disabled (hidden from UI)."
else
  echo "  Default admin not found (already removed)."
fi

# ── Load Sample Data ─────────────────────────────────────────────────
echo ""
echo "Loading sample metadata..."

SERVICE_NAME="calabi_sample_db"

# Check if service exists
SVC_EXISTS=$(api_get "/api/v1/services/databaseServices/name/$SERVICE_NAME" | grep -o '"id"')

if [ -z "$SVC_EXISTS" ]; then
  echo "  Creating sample database service..."
  api_post "/api/v1/services/databaseServices" '{
    "name": "calabi_sample_db",
    "displayName": "Calabi Sample Database",
    "serviceType": "CustomDatabase",
    "description": "Sample data for Calabi CE evaluation. Connect your own data sources to see real metadata.",
    "connection": {
      "config": {
        "type": "CustomDatabase",
        "sourcePythonClass": "metadata.ingestion.source.database.sample_data.SampleDataSource"
      }
    }
  }' > /dev/null
  echo "  Service created."
else
  echo "  Service exists."
fi

# Check if tables already loaded
TABLE_COUNT=$(api_get "/api/v1/tables?limit=1" | sed -n 's/.*"total":\([0-9]*\).*/\1/p')

if [ "${TABLE_COUNT:-0}" -gt 0 ]; then
  echo "  Sample data already loaded ($TABLE_COUNT tables). Skipping."
else
  echo "  Creating databases..."

  # Create databases
  for DB_JSON in \
    '{"name":"ecommerce_db","displayName":"E-Commerce Database","description":"Sample e-commerce database with customer, order, and product data.","service":"calabi_sample_db"}' \
    '{"name":"analytics_db","displayName":"Analytics Database","description":"Aggregated analytics and reporting tables for business intelligence.","service":"calabi_sample_db"}' \
    '{"name":"hr_db","displayName":"Human Resources Database","description":"Employee, department, and payroll data.","service":"calabi_sample_db"}'
  do
    NAME=$(echo "$DB_JSON" | sed -n 's/.*"name":"\([^"]*\)".*/\1/p')
    RESULT=$(api_post "/api/v1/databases" "$DB_JSON")
    echo "$RESULT" | grep -q '"fullyQualifiedName"' && echo "    + $NAME" || echo "    = $NAME (exists)"
  done

  echo "  Creating schemas..."

  for SCHEMA_JSON in \
    '{"name":"shopify","displayName":"Shopify Schema","description":"Core e-commerce operational data.","database":"calabi_sample_db.ecommerce_db"}' \
    '{"name":"marketing","displayName":"Marketing Schema","description":"Campaign tracking and attribution.","database":"calabi_sample_db.ecommerce_db"}' \
    '{"name":"warehouse","displayName":"Data Warehouse","description":"Star-schema fact and dimension tables.","database":"calabi_sample_db.analytics_db"}' \
    '{"name":"staging","displayName":"Staging Area","description":"Intermediate ETL tables.","database":"calabi_sample_db.analytics_db"}' \
    '{"name":"core","displayName":"HR Core","description":"Core HR entities.","database":"calabi_sample_db.hr_db"}'
  do
    NAME=$(echo "$SCHEMA_JSON" | sed -n 's/.*"name":"\([^"]*\)".*/\1/p')
    RESULT=$(api_post "/api/v1/databaseSchemas" "$SCHEMA_JSON")
    echo "$RESULT" | grep -q '"fullyQualifiedName"' && echo "    + $NAME" || echo "    = $NAME (exists)"
  done

  echo "  Creating tables..."

  # dim_customer
  api_post "/api/v1/tables" '{"name":"dim_customer","displayName":"Customer Dimension","description":"Customer master data including demographics and account information.","tableType":"Regular","databaseSchema":"calabi_sample_db.ecommerce_db.shopify","columns":[{"name":"customer_id","dataType":"BIGINT","description":"Unique customer identifier","constraint":"PRIMARY_KEY"},{"name":"first_name","dataType":"VARCHAR","dataLength":100,"description":"Customer first name"},{"name":"last_name","dataType":"VARCHAR","dataLength":100,"description":"Customer last name"},{"name":"email","dataType":"VARCHAR","dataLength":255,"description":"Primary email address","constraint":"UNIQUE"},{"name":"phone","dataType":"VARCHAR","dataLength":20,"description":"Phone number"},{"name":"created_at","dataType":"TIMESTAMP","description":"Account creation timestamp"},{"name":"is_active","dataType":"BOOLEAN","description":"Whether the account is active"},{"name":"lifetime_value","dataType":"DECIMAL","description":"Total customer spend"},{"name":"segment","dataType":"VARCHAR","dataLength":50,"description":"Customer segment: VIP, Regular, or New"}]}' > /dev/null && echo "    + dim_customer"

  # dim_product
  api_post "/api/v1/tables" '{"name":"dim_product","displayName":"Product Dimension","description":"Product catalog with pricing and categories.","tableType":"Regular","databaseSchema":"calabi_sample_db.ecommerce_db.shopify","columns":[{"name":"product_id","dataType":"BIGINT","description":"Unique product identifier","constraint":"PRIMARY_KEY"},{"name":"sku","dataType":"VARCHAR","dataLength":50,"description":"Stock keeping unit code","constraint":"UNIQUE"},{"name":"product_name","dataType":"VARCHAR","dataLength":255,"description":"Product display name"},{"name":"category","dataType":"VARCHAR","dataLength":100,"description":"Product category"},{"name":"unit_price","dataType":"DECIMAL","description":"Current unit price in USD"},{"name":"is_active","dataType":"BOOLEAN","description":"Whether the product is currently listed"}]}' > /dev/null && echo "    + dim_product"

  # fact_orders
  api_post "/api/v1/tables" '{"name":"fact_orders","displayName":"Orders Fact Table","description":"Transactional order data. Core table for revenue reporting.","tableType":"Regular","databaseSchema":"calabi_sample_db.ecommerce_db.shopify","columns":[{"name":"order_id","dataType":"BIGINT","description":"Unique order identifier","constraint":"PRIMARY_KEY"},{"name":"customer_id","dataType":"BIGINT","description":"FK to dim_customer"},{"name":"product_id","dataType":"BIGINT","description":"FK to dim_product"},{"name":"order_date","dataType":"DATE","description":"Date the order was placed"},{"name":"quantity","dataType":"INT","description":"Number of units ordered"},{"name":"total_amount","dataType":"DECIMAL","description":"Final amount after discount"},{"name":"order_status","dataType":"VARCHAR","dataLength":30,"description":"Status: pending, shipped, delivered, returned"},{"name":"payment_method","dataType":"VARCHAR","dataLength":30,"description":"Payment method used"}]}' > /dev/null && echo "    + fact_orders"

  # fact_payments
  api_post "/api/v1/tables" '{"name":"fact_payments","displayName":"Payments Fact Table","description":"Payment transactions linked to orders.","tableType":"Regular","databaseSchema":"calabi_sample_db.ecommerce_db.shopify","columns":[{"name":"payment_id","dataType":"BIGINT","description":"Unique payment identifier","constraint":"PRIMARY_KEY"},{"name":"order_id","dataType":"BIGINT","description":"FK to fact_orders"},{"name":"payment_date","dataType":"TIMESTAMP","description":"Timestamp of payment processing"},{"name":"amount","dataType":"DECIMAL","description":"Payment amount in USD"},{"name":"payment_status","dataType":"VARCHAR","dataLength":20,"description":"completed, pending, failed, refunded"}]}' > /dev/null && echo "    + fact_payments"

  # dim_address
  api_post "/api/v1/tables" '{"name":"dim_address","displayName":"Address Dimension","description":"Customer shipping and billing addresses.","tableType":"Regular","databaseSchema":"calabi_sample_db.ecommerce_db.shopify","columns":[{"name":"address_id","dataType":"BIGINT","description":"Unique address identifier","constraint":"PRIMARY_KEY"},{"name":"customer_id","dataType":"BIGINT","description":"FK to dim_customer"},{"name":"city","dataType":"VARCHAR","dataLength":100,"description":"City name"},{"name":"state","dataType":"VARCHAR","dataLength":100,"description":"State or province"},{"name":"country","dataType":"VARCHAR","dataLength":2,"description":"ISO country code"}]}' > /dev/null && echo "    + dim_address"

  # campaigns
  api_post "/api/v1/tables" '{"name":"campaigns","displayName":"Marketing Campaigns","description":"Marketing campaign definitions with budget and targeting.","tableType":"Regular","databaseSchema":"calabi_sample_db.ecommerce_db.marketing","columns":[{"name":"campaign_id","dataType":"BIGINT","description":"Unique campaign identifier","constraint":"PRIMARY_KEY"},{"name":"campaign_name","dataType":"VARCHAR","dataLength":200,"description":"Campaign display name"},{"name":"channel","dataType":"VARCHAR","dataLength":50,"description":"Marketing channel"},{"name":"start_date","dataType":"DATE","description":"Campaign start date"},{"name":"budget","dataType":"DECIMAL","description":"Allocated budget in USD"},{"name":"status","dataType":"VARCHAR","dataLength":20,"description":"active, paused, completed"}]}' > /dev/null && echo "    + campaigns"

  # attribution_events
  api_post "/api/v1/tables" '{"name":"attribution_events","displayName":"Attribution Events","description":"Multi-touch attribution events linking campaigns to conversions.","tableType":"Regular","databaseSchema":"calabi_sample_db.ecommerce_db.marketing","columns":[{"name":"event_id","dataType":"BIGINT","description":"Unique event identifier","constraint":"PRIMARY_KEY"},{"name":"customer_id","dataType":"BIGINT","description":"FK to dim_customer"},{"name":"campaign_id","dataType":"BIGINT","description":"FK to campaigns"},{"name":"event_type","dataType":"VARCHAR","dataLength":30,"description":"impression, click, conversion"},{"name":"event_timestamp","dataType":"TIMESTAMP","description":"Event occurrence time"}]}' > /dev/null && echo "    + attribution_events"

  # fact_daily_revenue
  api_post "/api/v1/tables" '{"name":"fact_daily_revenue","displayName":"Daily Revenue","description":"Pre-aggregated daily revenue metrics by product category and region.","tableType":"Regular","databaseSchema":"calabi_sample_db.analytics_db.warehouse","columns":[{"name":"date_key","dataType":"DATE","description":"Reporting date","constraint":"PRIMARY_KEY"},{"name":"category","dataType":"VARCHAR","dataLength":100,"description":"Product category"},{"name":"region","dataType":"VARCHAR","dataLength":50,"description":"Geographic region"},{"name":"total_orders","dataType":"INT","description":"Number of orders"},{"name":"total_revenue","dataType":"DECIMAL","description":"Gross revenue in USD"},{"name":"net_revenue","dataType":"DECIMAL","description":"Revenue after discounts"}]}' > /dev/null && echo "    + fact_daily_revenue"

  # dim_date
  api_post "/api/v1/tables" '{"name":"dim_date","displayName":"Date Dimension","description":"Calendar dimension table for time-based analysis.","tableType":"Regular","databaseSchema":"calabi_sample_db.analytics_db.warehouse","columns":[{"name":"date_key","dataType":"DATE","description":"Calendar date","constraint":"PRIMARY_KEY"},{"name":"year","dataType":"INT","description":"Calendar year"},{"name":"quarter","dataType":"INT","description":"Quarter number"},{"name":"month","dataType":"INT","description":"Month number"},{"name":"month_name","dataType":"VARCHAR","dataLength":20,"description":"Month name"},{"name":"day_of_week","dataType":"INT","description":"Day of week"},{"name":"is_weekend","dataType":"BOOLEAN","description":"Whether the date is a weekend"}]}' > /dev/null && echo "    + dim_date"

  # fact_customer_360
  api_post "/api/v1/tables" '{"name":"fact_customer_360","displayName":"Customer 360 View","description":"Unified customer profile combining order history and engagement metrics.","tableType":"Regular","databaseSchema":"calabi_sample_db.analytics_db.warehouse","columns":[{"name":"customer_id","dataType":"BIGINT","description":"Unique customer identifier","constraint":"PRIMARY_KEY"},{"name":"total_orders","dataType":"INT","description":"Lifetime order count"},{"name":"total_spend","dataType":"DECIMAL","description":"Lifetime total spend"},{"name":"avg_order_value","dataType":"DECIMAL","description":"Average order value"},{"name":"churn_risk_score","dataType":"FLOAT","description":"ML-predicted churn probability"},{"name":"customer_segment","dataType":"VARCHAR","dataLength":30,"description":"RFM segment label"}]}' > /dev/null && echo "    + fact_customer_360"

  # stg_raw_events
  api_post "/api/v1/tables" '{"name":"stg_raw_events","displayName":"Staging: Raw Events","description":"Raw clickstream events before deduplication.","tableType":"Regular","databaseSchema":"calabi_sample_db.analytics_db.staging","columns":[{"name":"event_id","dataType":"VARCHAR","dataLength":36,"description":"UUID event identifier"},{"name":"session_id","dataType":"VARCHAR","dataLength":36,"description":"Session identifier"},{"name":"event_type","dataType":"VARCHAR","dataLength":50,"description":"page_view, add_to_cart, purchase"},{"name":"page_url","dataType":"VARCHAR","dataLength":500,"description":"Page URL"},{"name":"event_timestamp","dataType":"TIMESTAMP","description":"Event timestamp"},{"name":"ingested_at","dataType":"TIMESTAMP","description":"Ingestion timestamp"}]}' > /dev/null && echo "    + stg_raw_events"

  # stg_orders_cleaned
  api_post "/api/v1/tables" '{"name":"stg_orders_cleaned","displayName":"Staging: Orders Cleaned","description":"Cleaned and deduplicated orders ready for warehouse load.","tableType":"Regular","databaseSchema":"calabi_sample_db.analytics_db.staging","columns":[{"name":"order_id","dataType":"BIGINT","description":"Order identifier"},{"name":"customer_id","dataType":"BIGINT","description":"Customer identifier"},{"name":"order_date","dataType":"DATE","description":"Order date"},{"name":"total_amount","dataType":"DECIMAL","description":"Order total"},{"name":"is_valid","dataType":"BOOLEAN","description":"Data quality flag"},{"name":"processed_at","dataType":"TIMESTAMP","description":"ETL processing timestamp"}]}' > /dev/null && echo "    + stg_orders_cleaned"

  # employees
  api_post "/api/v1/tables" '{"name":"employees","displayName":"Employees","description":"Employee master data.","tableType":"Regular","databaseSchema":"calabi_sample_db.hr_db.core","columns":[{"name":"employee_id","dataType":"BIGINT","description":"Unique employee identifier","constraint":"PRIMARY_KEY"},{"name":"first_name","dataType":"VARCHAR","dataLength":100,"description":"First name"},{"name":"last_name","dataType":"VARCHAR","dataLength":100,"description":"Last name"},{"name":"email","dataType":"VARCHAR","dataLength":255,"description":"Corporate email","constraint":"UNIQUE"},{"name":"department_id","dataType":"BIGINT","description":"FK to departments"},{"name":"position_title","dataType":"VARCHAR","dataLength":200,"description":"Job title"},{"name":"hire_date","dataType":"DATE","description":"Date of hire"},{"name":"salary","dataType":"DECIMAL","description":"Annual base salary"},{"name":"is_active","dataType":"BOOLEAN","description":"Employment status flag"}]}' > /dev/null && echo "    + employees"

  # departments
  api_post "/api/v1/tables" '{"name":"departments","displayName":"Departments","description":"Organizational department hierarchy.","tableType":"Regular","databaseSchema":"calabi_sample_db.hr_db.core","columns":[{"name":"department_id","dataType":"BIGINT","description":"Unique department identifier","constraint":"PRIMARY_KEY"},{"name":"department_name","dataType":"VARCHAR","dataLength":100,"description":"Department name"},{"name":"head_count","dataType":"INT","description":"Current headcount"},{"name":"budget","dataType":"DECIMAL","description":"Annual department budget"},{"name":"location","dataType":"VARCHAR","dataLength":100,"description":"Primary office location"}]}' > /dev/null && echo "    + departments"

  # payroll
  api_post "/api/v1/tables" '{"name":"payroll","displayName":"Payroll Records","description":"Monthly payroll records.","tableType":"Regular","databaseSchema":"calabi_sample_db.hr_db.core","columns":[{"name":"payroll_id","dataType":"BIGINT","description":"Unique payroll record ID","constraint":"PRIMARY_KEY"},{"name":"employee_id","dataType":"BIGINT","description":"FK to employees"},{"name":"pay_period_start","dataType":"DATE","description":"Pay period start date"},{"name":"gross_pay","dataType":"DECIMAL","description":"Gross pay amount"},{"name":"net_pay","dataType":"DECIMAL","description":"Net pay after deductions"},{"name":"payment_date","dataType":"DATE","description":"Date payment was issued"}]}' > /dev/null && echo "    + payroll"

  echo "  Sample tables created."
fi

# ── Ingest Superset Dashboard Metadata into OpenMetadata ─────────────
echo ""
echo "Ingesting Superset dashboard metadata..."

SS_SERVICE_NAME="calabi_superset"
SS_SVC_EXISTS=$(api_get "/api/v1/services/dashboardServices/name/$SS_SERVICE_NAME" | grep -o '"id"')

if [ -z "$SS_SVC_EXISTS" ]; then
  echo "  Creating Superset dashboard service..."
  api_post "/api/v1/services/dashboardServices" '{
    "name": "calabi_superset",
    "displayName": "CalabiIQ (Superset)",
    "serviceType": "Superset",
    "description": "Superset BI dashboards powering CalabiIQ Analytics. Browse dashboards and charts as data assets.",
    "connection": {
      "config": {
        "type": "Superset",
        "hostPort": "http://calabi-bi:8088",
        "connection": {
          "username": "admin",
          "password": "admin",
          "provider": "db"
        }
      }
    }
  }' > /dev/null
  echo "  Superset service registered."
else
  echo "  Superset service exists."
fi

# Wait for Superset to be ready
echo "  Waiting for Superset..."
for i in $(seq 1 30); do
  SS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://calabi-bi:8088/health" 2>/dev/null)
  if [ "$SS_STATUS" = "200" ]; then
    echo "  Superset ready."
    break
  fi
  sleep 3
done

# Get Superset auth token
SS_TOKEN=$(curl -s "http://calabi-bi:8088/api/v1/security/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin","provider":"db","refresh":true}' 2>/dev/null \
  | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

if [ -n "$SS_TOKEN" ]; then
  # Fetch all dashboards from Superset
  SS_DASHBOARDS=$(curl -s "http://calabi-bi:8088/api/v1/dashboard/?q=(page_size:50,page:0)" \
    -H "Authorization: Bearer $SS_TOKEN" 2>/dev/null)

  DASH_COUNT=$(echo "$SS_DASHBOARDS" | sed -n 's/.*"count":\([0-9]*\).*/\1/p')
  echo "  Found $DASH_COUNT Superset dashboards."

  # Check if dashboards already ingested
  EXISTING_DASH=$(api_get "/api/v1/dashboards?service=calabi_superset&limit=1" | sed -n 's/.*"total":\([0-9]*\).*/\1/p')

  if [ "${EXISTING_DASH:-0}" -gt 0 ]; then
    echo "  Dashboards already ingested ($EXISTING_DASH). Skipping."
  else
    # Parse and register each dashboard
    # Extract dashboard IDs and titles using simple parsing
    echo "$SS_DASHBOARDS" | sed 's/},{/}\n{/g' | while IFS= read -r line; do
      DASH_ID=$(echo "$line" | sed -n 's/.*"id":\([0-9]*\).*/\1/p' | head -1)
      DASH_TITLE=$(echo "$line" | sed -n 's/.*"dashboard_title":"\([^"]*\)".*/\1/p' | head -1)
      DASH_SLUG=$(echo "$line" | sed -n 's/.*"slug":"\([^"]*\)".*/\1/p' | head -1)
      DASH_STATUS=$(echo "$line" | sed -n 's/.*"published":\([a-z]*\).*/\1/p' | head -1)

      if [ -n "$DASH_ID" ] && [ -n "$DASH_TITLE" ]; then
        # Create a URL-safe name from title
        DASH_NAME=$(echo "$DASH_TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_//;s/_$//')
        DASH_URL="http://localhost:8088/superset/dashboard/$DASH_ID/"

        api_post "/api/v1/dashboards" "{
          \"name\": \"$DASH_NAME\",
          \"displayName\": \"$DASH_TITLE\",
          \"description\": \"Superset dashboard: $DASH_TITLE. View at $DASH_URL\",
          \"sourceUrl\": \"$DASH_URL\",
          \"service\": \"calabi_superset\",
          \"dashboardType\": \"Superset\"
        }" > /dev/null 2>&1
        echo "    + $DASH_TITLE (ID: $DASH_ID)"
      fi
    done

    # Also fetch and register charts
    SS_CHARTS=$(curl -s "http://calabi-bi:8088/api/v1/chart/?q=(page_size:100,page:0)" \
      -H "Authorization: Bearer $SS_TOKEN" 2>/dev/null)
    CHART_COUNT=$(echo "$SS_CHARTS" | sed -n 's/.*"count":\([0-9]*\).*/\1/p')
    echo "  Found $CHART_COUNT Superset charts. Registering..."

    echo "$SS_CHARTS" | sed 's/},{/}\n{/g' | while IFS= read -r line; do
      CHART_ID=$(echo "$line" | sed -n 's/.*"id":\([0-9]*\).*/\1/p' | head -1)
      CHART_NAME=$(echo "$line" | sed -n 's/.*"slice_name":"\([^"]*\)".*/\1/p' | head -1)
      CHART_TYPE=$(echo "$line" | sed -n 's/.*"viz_type":"\([^"]*\)".*/\1/p' | head -1)

      if [ -n "$CHART_ID" ] && [ -n "$CHART_NAME" ]; then
        SAFE_NAME=$(echo "$CHART_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_//;s/_$//')

        api_post "/api/v1/charts" "{
          \"name\": \"$SAFE_NAME\",
          \"displayName\": \"$CHART_NAME\",
          \"description\": \"Superset chart ($CHART_TYPE)\",
          \"chartType\": \"Other\",
          \"service\": \"calabi_superset\"
        }" > /dev/null 2>&1
      fi
    done
    echo "  Charts registered."
  fi
else
  echo "  WARNING: Could not authenticate with Superset. Skipping dashboard ingestion."
fi

echo ""
echo "══════════════════════════════════════════════"
echo " CE setup complete."
echo " Login: ce-admin@calabi.dev / Calabi@CE2025!"
echo " URL:   http://localhost:8080"
echo " Data:  3 databases, 5 schemas, 15 tables"
echo "       + Superset dashboards & charts"
echo "══════════════════════════════════════════════"

"""
Calabi Metadata Refresh DAG
=============================
Keeps the Calabi Catalogue in sync with warehouse schema changes.
Triggers OpenMetadata metadata ingestion on a schedule (every 6 hours).

This ensures that new tables, columns, and schema changes in the customer's
warehouse are automatically reflected in the Calabi Catalogue.

Parameters (set via Airflow Variables):
  - calabi_om_url:              OpenMetadata URL (default: http://calabi-catalogue:8585)
  - calabi_om_service_name:     Database service name in OM (e.g., "my_redshift")
  - calabi_om_auth_token:       OM bot JWT token for API auth (optional)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

default_args = {
    "owner": "calabi",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def trigger_metadata_ingestion(**context):
    """Trigger OpenMetadata to run metadata ingestion for the configured database service."""
    import urllib.request
    import json

    om_url = Variable.get(
        "calabi_om_url", default_var="http://calabi-catalogue:8585"
    )
    service_name = Variable.get("calabi_om_service_name", default_var="")
    auth_token = Variable.get("calabi_om_auth_token", default_var="")

    if not service_name:
        print("[SKIP] No OM service name configured.")
        print("  Set 'calabi_om_service_name' in Airflow Variables to enable metadata refresh.")
        print("  The Setup Wizard will configure this automatically when you connect a warehouse.")
        return {"status": "skipped", "reason": "no_service_name"}

    # First, get the ingestion pipeline ID for this service
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    # List ingestion pipelines for the service
    list_url = (
        f"{om_url}/api/v1/services/ingestionPipelines?"
        f"service={service_name}&pipelineType=metadata&limit=1"
    )
    try:
        req = urllib.request.Request(list_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            pipelines = result.get("data", [])

            if not pipelines:
                print(f"[WARN] No metadata ingestion pipeline found for service '{service_name}'.")
                print("  Create one in Calabi Catalogue > Settings > Metadata Ingestion.")
                return {"status": "no_pipeline", "service": service_name}

            pipeline_id = pipelines[0].get("id")
            pipeline_name = pipelines[0].get("name", "unknown")
    except Exception as e:
        print(f"[ERROR] Failed to list ingestion pipelines: {e}")
        raise

    # Trigger the ingestion pipeline
    trigger_url = f"{om_url}/api/v1/services/ingestionPipelines/trigger/{pipeline_id}"
    try:
        req = urllib.request.Request(trigger_url, method="POST", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"[OK] Metadata ingestion triggered: {pipeline_name} (ID: {pipeline_id})")
            return {
                "status": "triggered",
                "pipeline": pipeline_name,
                "pipeline_id": str(pipeline_id),
                "service": service_name,
            }
    except Exception as e:
        print(f"[ERROR] Failed to trigger ingestion: {e}")
        raise


def trigger_search_reindex(**context):
    """Trigger OpenMetadata search reindex after metadata ingestion."""
    import urllib.request
    import json

    ti = context["ti"]
    ingestion_result = ti.xcom_pull(task_ids="trigger_metadata_ingestion")
    if not ingestion_result or ingestion_result.get("status") in ("skipped", "no_pipeline"):
        print("[SKIP] No ingestion was triggered, skipping reindex.")
        return {"status": "skipped"}

    om_url = Variable.get(
        "calabi_om_url", default_var="http://calabi-catalogue:8585"
    )
    auth_token = Variable.get("calabi_om_auth_token", default_var="")
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    # Trigger search reindex
    url = f"{om_url}/api/v1/search/reindex"
    payload = json.dumps({
        "recreateIndex": False,
        "runMode": "ON_DEMAND",
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, method="POST", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("[OK] Search reindex triggered")
            return {"status": "triggered"}
    except Exception as e:
        # Non-fatal — search will eventually catch up
        print(f"[WARN] Search reindex failed: {e}")
        return {"status": "warning", "error": str(e)}


def log_refresh_summary(**context):
    """Log a summary of what was refreshed."""
    ti = context["ti"]
    ingestion = ti.xcom_pull(task_ids="trigger_metadata_ingestion") or {}
    reindex = ti.xcom_pull(task_ids="trigger_search_reindex") or {}

    print("=" * 60)
    print("  Calabi Metadata Refresh Summary")
    print("=" * 60)
    print(f"  Ingestion: {ingestion.get('status', 'unknown')}")
    if ingestion.get("service"):
        print(f"  Service:   {ingestion['service']}")
    if ingestion.get("pipeline"):
        print(f"  Pipeline:  {ingestion['pipeline']}")
    print(f"  Reindex:   {reindex.get('status', 'unknown')}")
    print(f"  Time:      {context['execution_date'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)


with DAG(
    dag_id="calabi_metadata_refresh",
    default_args=default_args,
    description="Calabi Metadata Refresh: OM ingestion -> search reindex (every 6 hours)",
    schedule_interval="0 */6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["calabi", "metadata", "catalogue", "starter", "template"],
) as dag:

    ingest = PythonOperator(
        task_id="trigger_metadata_ingestion",
        python_callable=trigger_metadata_ingestion,
    )

    reindex = PythonOperator(
        task_id="trigger_search_reindex",
        python_callable=trigger_search_reindex,
    )

    summary = PythonOperator(
        task_id="log_refresh_summary",
        python_callable=log_refresh_summary,
    )

    ingest >> reindex >> summary

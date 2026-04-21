"""
Calabi ELT Pipeline DAG
========================
Full ELT workflow: Airbyte sync -> dbt run -> dbt test -> OM metadata ingestion.

This is the primary data pipeline template for Calabi Starter.
Customers clone and configure this for their use case via the Setup Wizard.

Parameters (set via Airflow Variables or DAG params):
  - calabi_airbyte_connection_id:  Airbyte connection UUID
  - calabi_dbt_project_dir:        Path to dbt project (default: /opt/airflow/dbt)
  - calabi_dbt_target:             dbt target/profile (default: default)
  - calabi_om_service_name:        OpenMetadata database service name
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


def trigger_airbyte_sync(**context):
    """Trigger an Airbyte sync job via Calabi Connect API."""
    import urllib.request
    import json

    connection_id = Variable.get(
        "calabi_airbyte_connection_id", default_var=""
    )
    if not connection_id:
        print("[SKIP] No Airbyte connection_id configured. Set 'calabi_airbyte_connection_id' in Airflow Variables.")
        return {"status": "skipped", "reason": "no_connection_id"}

    airbyte_url = Variable.get(
        "calabi_airbyte_api_url", default_var="http://calabi-connect:8006"
    )
    url = f"{airbyte_url}/api/v1/connections/sync"
    payload = json.dumps({"connectionId": connection_id}).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            job_id = result.get("job", {}).get("id", "unknown")
            print(f"[OK] Airbyte sync triggered. Job ID: {job_id}")
            return {"status": "triggered", "job_id": job_id}
    except Exception as e:
        print(f"[ERROR] Airbyte sync failed: {e}")
        raise


def wait_for_airbyte_sync(**context):
    """Poll Airbyte until the sync job completes."""
    import urllib.request
    import json
    import time

    ti = context["ti"]
    sync_result = ti.xcom_pull(task_ids="trigger_airbyte_sync")
    if not sync_result or sync_result.get("status") == "skipped":
        print("[SKIP] No sync was triggered.")
        return

    job_id = sync_result.get("job_id")
    airbyte_url = Variable.get(
        "calabi_airbyte_api_url", default_var="http://calabi-connect:8006"
    )
    url = f"{airbyte_url}/api/v1/jobs/get"
    max_wait = 3600  # 1 hour max
    elapsed = 0
    poll_interval = 15

    while elapsed < max_wait:
        payload = json.dumps({"id": job_id}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, method="POST",
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                status = result.get("job", {}).get("status", "unknown")
                print(f"  Airbyte job {job_id}: {status} ({elapsed}s)")
                if status == "succeeded":
                    print(f"[OK] Airbyte sync completed in {elapsed}s")
                    return {"status": "succeeded", "duration": elapsed}
                elif status in ("failed", "cancelled"):
                    raise Exception(f"Airbyte sync {status}: {result}")
        except urllib.error.URLError as e:
            print(f"  Poll error: {e}")

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise Exception(f"Airbyte sync timed out after {max_wait}s")


def run_dbt_command(command: str, **context):
    """Execute a dbt CLI command."""
    import subprocess
    import os

    project_dir = Variable.get(
        "calabi_dbt_project_dir", default_var="/opt/airflow/dbt"
    )
    target = Variable.get("calabi_dbt_target", default_var="default")
    profiles_dir = os.environ.get("DBT_PROFILES_DIR", "/opt/airflow/dbt")

    cmd = [
        "dbt", command,
        "--project-dir", project_dir,
        "--profiles-dir", profiles_dir,
        "--target", target,
    ]
    print(f"[RUN] {' '.join(cmd)}")

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=1800
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"[ERROR] dbt {command} failed:\n{result.stderr}")
        raise Exception(f"dbt {command} failed with exit code {result.returncode}")

    print(f"[OK] dbt {command} completed successfully")
    return {"status": "success", "command": command}


def trigger_om_metadata_ingestion(**context):
    """Trigger OpenMetadata to re-ingest warehouse metadata."""
    import urllib.request
    import json

    om_url = Variable.get(
        "calabi_om_url", default_var="http://calabi-catalogue:8585"
    )
    service_name = Variable.get(
        "calabi_om_service_name", default_var=""
    )
    if not service_name:
        print("[SKIP] No OM service name configured. Set 'calabi_om_service_name' in Airflow Variables.")
        return {"status": "skipped"}

    # Trigger metadata ingestion pipeline for the database service
    url = f"{om_url}/api/v1/services/ingestionPipelines/trigger/{service_name}"
    req = urllib.request.Request(url, method="POST", headers={
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"[OK] OM metadata ingestion triggered for service: {service_name}")
            return {"status": "triggered", "service": service_name}
    except Exception as e:
        print(f"[WARN] OM ingestion trigger failed: {e}")
        # Non-fatal — don't fail the whole pipeline
        return {"status": "warning", "error": str(e)}


with DAG(
    dag_id="calabi_elt_pipeline",
    default_args=default_args,
    description="Calabi ELT: Airbyte sync -> dbt run -> dbt test -> OM metadata refresh",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["calabi", "elt", "starter", "template"],
    params={
        "full_refresh": False,
    },
) as dag:

    sync_sources = PythonOperator(
        task_id="trigger_airbyte_sync",
        python_callable=trigger_airbyte_sync,
    )

    wait_sync = PythonOperator(
        task_id="wait_for_airbyte_sync",
        python_callable=wait_for_airbyte_sync,
    )

    dbt_run = PythonOperator(
        task_id="dbt_run",
        python_callable=run_dbt_command,
        op_kwargs={"command": "run"},
    )

    dbt_test = PythonOperator(
        task_id="dbt_test",
        python_callable=run_dbt_command,
        op_kwargs={"command": "test"},
    )

    refresh_metadata = PythonOperator(
        task_id="refresh_metadata",
        python_callable=trigger_om_metadata_ingestion,
    )

    sync_sources >> wait_sync >> dbt_run >> dbt_test >> refresh_metadata

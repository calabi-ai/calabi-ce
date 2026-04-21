"""
Calabi Data Quality DAG
========================
Runs after the ELT pipeline completes. Executes dbt tests, parses results,
pushes test outcomes to OpenMetadata quality API, and sends alerts on failures.

Trigger: ExternalTaskSensor waits for calabi_elt_pipeline.dbt_test to complete.
If run standalone, skips the sensor and runs tests directly.

Parameters (set via Airflow Variables):
  - calabi_dbt_project_dir:     Path to dbt project (default: /opt/airflow/dbt)
  - calabi_dbt_target:          dbt target/profile (default: default)
  - calabi_om_url:              OpenMetadata URL (default: http://calabi-catalogue:8585)
  - calabi_alert_on_failure:    "true"/"false" — send alerts on test failures
  - calabi_slack_webhook_url:   Slack webhook for failure alerts (optional)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.models import Variable

default_args = {
    "owner": "calabi",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}


def run_dbt_tests(**context):
    """Run all dbt tests and capture results as JSON."""
    import subprocess
    import os
    import json

    project_dir = Variable.get(
        "calabi_dbt_project_dir", default_var="/opt/airflow/dbt"
    )
    target = Variable.get("calabi_dbt_target", default_var="default")
    profiles_dir = os.environ.get("DBT_PROFILES_DIR", "/opt/airflow/dbt")

    cmd = [
        "dbt", "test",
        "--project-dir", project_dir,
        "--profiles-dir", profiles_dir,
        "--target", target,
    ]
    print(f"[RUN] {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    print(result.stdout)

    # Parse dbt test output for summary
    lines = result.stdout.strip().split("\n")
    passed = sum(1 for l in lines if "PASS" in l)
    failed = sum(1 for l in lines if "FAIL" in l)
    warned = sum(1 for l in lines if "WARN" in l)
    errored = sum(1 for l in lines if "ERROR" in l and "Compilation Error" not in l)

    summary = {
        "total": passed + failed + warned + errored,
        "passed": passed,
        "failed": failed,
        "warned": warned,
        "errored": errored,
        "exit_code": result.returncode,
        "has_failures": failed > 0 or errored > 0,
    }
    print(f"[SUMMARY] {json.dumps(summary)}")
    return summary


def push_quality_to_om(**context):
    """Push dbt test results to OpenMetadata quality API."""
    import urllib.request
    import json

    ti = context["ti"]
    summary = ti.xcom_pull(task_ids="run_dbt_tests")
    if not summary:
        print("[SKIP] No test results to push.")
        return

    om_url = Variable.get(
        "calabi_om_url", default_var="http://calabi-catalogue:8585"
    )

    # Push test summary as a custom metric / test report
    report = {
        "timestamp": context["execution_date"].isoformat(),
        "testSuite": "calabi_dbt_tests",
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "total": summary.get("total", 0),
    }

    # Try to create/update a test report via OM API
    url = f"{om_url}/api/v1/dataQuality/testCases/testCaseResult"
    try:
        payload = json.dumps(report).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, method="PUT",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[OK] Quality results pushed to OM: {summary['passed']} passed, {summary['failed']} failed")
    except Exception as e:
        print(f"[WARN] Could not push to OM quality API: {e}")
        # Non-fatal — OM API may not be fully configured yet

    return summary


def check_failures(**context):
    """Branch: if failures exist, go to alert task; otherwise skip."""
    ti = context["ti"]
    summary = ti.xcom_pull(task_ids="run_dbt_tests")

    alert_enabled = Variable.get("calabi_alert_on_failure", default_var="true")
    if summary and summary.get("has_failures") and alert_enabled.lower() == "true":
        return "send_failure_alert"
    return "skip_alert"


def send_failure_alert(**context):
    """Send alert on test failures via Slack webhook or log."""
    import urllib.request
    import json

    ti = context["ti"]
    summary = ti.xcom_pull(task_ids="run_dbt_tests")
    if not summary:
        return

    slack_url = Variable.get("calabi_slack_webhook_url", default_var="")

    message = (
        f":warning: *Calabi Data Quality Alert*\n"
        f"Run: {context['execution_date'].strftime('%Y-%m-%d %H:%M')}\n"
        f"Tests: {summary['total']} total | "
        f"{summary['passed']} passed | "
        f"{summary['failed']} failed | "
        f"{summary['errored']} errors\n"
        f"Action: Check Airflow logs for details."
    )

    if slack_url:
        try:
            payload = json.dumps({"text": message}).encode("utf-8")
            req = urllib.request.Request(
                slack_url, data=payload, method="POST",
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=10)
            print(f"[OK] Slack alert sent")
        except Exception as e:
            print(f"[WARN] Slack alert failed: {e}")
    else:
        print(f"[ALERT] {message}")
        print("[INFO] Configure 'calabi_slack_webhook_url' for Slack alerts.")


with DAG(
    dag_id="calabi_data_quality",
    default_args=default_args,
    description="Calabi Data Quality: dbt test -> parse results -> OM quality API -> alerts",
    schedule_interval=None,  # Triggered by ELT pipeline or manually
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["calabi", "data-quality", "starter", "template"],
) as dag:

    # Wait for ELT pipeline to finish (optional — skip if running standalone)
    wait_for_elt = ExternalTaskSensor(
        task_id="wait_for_elt_pipeline",
        external_dag_id="calabi_elt_pipeline",
        external_task_id="dbt_test",
        mode="reschedule",
        timeout=3600,
        poke_interval=30,
        soft_fail=True,  # Don't fail if ELT pipeline hasn't run
    )

    run_tests = PythonOperator(
        task_id="run_dbt_tests",
        python_callable=run_dbt_tests,
    )

    push_to_om = PythonOperator(
        task_id="push_quality_to_om",
        python_callable=push_quality_to_om,
    )

    branch = BranchPythonOperator(
        task_id="check_failures",
        python_callable=check_failures,
    )

    alert = PythonOperator(
        task_id="send_failure_alert",
        python_callable=send_failure_alert,
    )

    skip = EmptyOperator(task_id="skip_alert")

    done = EmptyOperator(task_id="done", trigger_rule="none_failed_min_one_success")

    wait_for_elt >> run_tests >> push_to_om >> branch
    branch >> [alert, skip] >> done

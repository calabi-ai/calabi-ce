"""
Calabi Health Check DAG
=======================
Runs every 30 minutes. Verifies all Calabi services are reachable
from the Airflow container. Useful for monitoring and debugging.

This DAG ships with every Calabi Pipelines instance (Starter+).
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "calabi",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def check_service(service_name: str, url: str):
    """Check if a Calabi service is reachable."""
    import urllib.request
    import json

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            print(f"[OK] {service_name}: HTTP {status}")
            return True
    except Exception as e:
        print(f"[WARN] {service_name}: {e}")
        return False


with DAG(
    dag_id="calabi_health_check",
    default_args=default_args,
    description="Check health of all Calabi services",
    schedule_interval="*/30 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["calabi", "monitoring", "starter"],
) as dag:

    check_catalogue = PythonOperator(
        task_id="check_catalogue",
        python_callable=check_service,
        op_kwargs={
            "service_name": "Calabi Catalogue",
            "url": "http://calabi-catalogue:8585/api/v1/system/version",
        },
    )

    check_bi = PythonOperator(
        task_id="check_bi",
        python_callable=check_service,
        op_kwargs={
            "service_name": "CalabiIQ BI",
            "url": "http://calabi-bi:8088/health",
        },
    )

    check_license = PythonOperator(
        task_id="check_license_proxy",
        python_callable=check_service,
        op_kwargs={
            "service_name": "License Proxy",
            "url": "http://calabi-license-proxy:8090/health",
        },
    )

    [check_catalogue, check_bi, check_license]

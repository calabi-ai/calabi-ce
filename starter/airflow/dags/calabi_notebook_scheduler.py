"""
Calabi Notebook Scheduler DAG
==============================
Runs Jupyter notebooks on a configurable schedule using Papermill.
Use this for scheduled reporting, recurring analyses, or automated data exports.

The notebook is executed inside the Calabi Pipelines container (which has
the same Python/dbt/warehouse stack as Calabi Notebooks).

Parameters (set via Airflow Variables):
  - calabi_notebook_path:       Path to notebook (default: /opt/airflow/notebooks/report.ipynb)
  - calabi_notebook_output_dir: Output dir for executed notebooks (default: /opt/airflow/notebooks/output)
  - calabi_notebook_params:     JSON string of parameters to inject (default: {})
  - calabi_notebook_schedule:   Cron expression (default: 0 8 * * 1 = Monday 8am)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

default_args = {
    "owner": "calabi",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def execute_notebook(**context):
    """Run a Jupyter notebook via Papermill."""
    import subprocess
    import json
    import os

    notebook_path = Variable.get(
        "calabi_notebook_path",
        default_var="/opt/airflow/notebooks/report.ipynb"
    )
    output_dir = Variable.get(
        "calabi_notebook_output_dir",
        default_var="/opt/airflow/notebooks/output"
    )
    params_json = Variable.get(
        "calabi_notebook_params",
        default_var="{}"
    )

    # Check notebook exists
    if not os.path.exists(notebook_path):
        print(f"[SKIP] Notebook not found: {notebook_path}")
        print("  Configure 'calabi_notebook_path' in Airflow Variables.")
        print("  Place notebooks in /opt/airflow/notebooks/ or mount a volume.")
        return {"status": "skipped", "reason": "notebook_not_found"}

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Build output filename with execution date
    exec_date = context["execution_date"].strftime("%Y%m%d_%H%M%S")
    nb_name = os.path.splitext(os.path.basename(notebook_path))[0]
    output_path = os.path.join(output_dir, f"{nb_name}_{exec_date}.ipynb")

    # Parse parameters
    try:
        params = json.loads(params_json)
    except json.JSONDecodeError:
        print(f"[WARN] Invalid JSON in calabi_notebook_params: {params_json}")
        params = {}

    # Add Calabi context parameters
    params["calabi_execution_date"] = exec_date
    params["calabi_dag_run_id"] = context.get("run_id", "manual")

    # Build papermill command
    cmd = [
        "papermill",
        notebook_path,
        output_path,
    ]
    for key, value in params.items():
        cmd.extend(["-p", str(key), str(value)])

    print(f"[RUN] Executing notebook: {notebook_path}")
    print(f"  Output: {output_path}")
    print(f"  Parameters: {json.dumps(params, indent=2)}")

    # First check if papermill is installed
    try:
        subprocess.run(
            ["pip", "install", "--quiet", "papermill"],
            capture_output=True, timeout=120
        )
    except Exception:
        pass  # Best effort install

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=3600
    )
    print(result.stdout)

    if result.returncode != 0:
        print(f"[ERROR] Notebook execution failed:\n{result.stderr}")
        raise Exception(f"Papermill failed with exit code {result.returncode}")

    print(f"[OK] Notebook executed successfully")
    print(f"  Output saved to: {output_path}")

    return {
        "status": "success",
        "input": notebook_path,
        "output": output_path,
        "params": params,
    }


def notify_completion(**context):
    """Log completion and optionally send notification."""
    import json

    ti = context["ti"]
    result = ti.xcom_pull(task_ids="execute_notebook")

    if not result or result.get("status") == "skipped":
        print("[INFO] Notebook execution was skipped.")
        return

    slack_url = Variable.get("calabi_slack_webhook_url", default_var="")

    message = (
        f"Calabi Notebook Scheduler\n"
        f"  Notebook: {result.get('input', 'unknown')}\n"
        f"  Status: {result.get('status', 'unknown')}\n"
        f"  Output: {result.get('output', 'N/A')}\n"
        f"  Time: {context['execution_date'].strftime('%Y-%m-%d %H:%M')}"
    )
    print(f"[COMPLETE] {message}")

    if slack_url:
        import urllib.request
        try:
            payload = json.dumps({
                "text": f":notebook: *{message}*"
            }).encode("utf-8")
            req = urllib.request.Request(
                slack_url, data=payload, method="POST",
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=10)
            print("[OK] Slack notification sent")
        except Exception as e:
            print(f"[WARN] Slack notification failed: {e}")


# Schedule — configurable via Airflow Variable, default: Monday 8am
schedule = Variable.get("calabi_notebook_schedule", default_var="0 8 * * 1")

with DAG(
    dag_id="calabi_notebook_scheduler",
    default_args=default_args,
    description="Calabi Notebook Scheduler: run Jupyter notebooks via Papermill on a schedule",
    schedule_interval=schedule,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["calabi", "notebooks", "reporting", "starter", "template"],
) as dag:

    run_notebook = PythonOperator(
        task_id="execute_notebook",
        python_callable=execute_notebook,
    )

    notify = PythonOperator(
        task_id="notify_completion",
        python_callable=notify_completion,
    )

    run_notebook >> notify

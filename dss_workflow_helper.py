import os
import sys
import json
import smtplib
from datetime import datetime, timezone
import dataikuapi
from email.message import EmailMessage
# Import the specific Project Deployer class for v14
from dataikuapi.dss.projectdeployer import DSSProjectDeployer

# --- CONFIGURATION ---
BASE_PROJECT_ID = "ASHISH_TEST5"
SCENARIO_ID = "PROJECT_QUALITY_CHECK"
DSS_DEFAULT_INFRA = os.environ.get("DSS_DEFAULT_INFRA", "ashish-automation")
DEPLOYMENT_ID = f"{BASE_PROJECT_ID}-on-{DSS_DEFAULT_INFRA}"

def get_notification_targets():
    scenario_path = os.path.join(os.path.dirname(__file__), "scenarios", f"{SCENARIO_ID}.json")
    with open(scenario_path, "r") as f:
        data = json.load(f)

    recipients = []
    cc_recipients = []

    for step in data.get("params", {}).get("steps", []):
        if step.get("type") != "send_report":
            continue

        config = step.get("params", {}).get("messaging", {}).get("configuration", {})
        recipient = config.get("recipient")
        cc_recipient = config.get("ccRecipient")

        if recipient and recipient not in recipients:
            recipients.append(recipient)
        if cc_recipient and cc_recipient not in cc_recipients:
            cc_recipients.append(cc_recipient)

    if not recipients:
        raise RuntimeError(f"No notification recipients found in {scenario_path}")

    return recipients, cc_recipients

def send_validation_email(status, bundle_id, details=""):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM", smtp_username)
    smtp_use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

    if not smtp_host or not smtp_from:
        print("WARNING: SMTP_HOST or SMTP_FROM is missing. Skipping email notification.")
        return

    to_recipients, cc_recipients = get_notification_targets()
    subject = f"[{status}] DSS deployment validation for {DEPLOYMENT_ID}"

    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = ", ".join(to_recipients)
    if cc_recipients:
        message["Cc"] = ", ".join(cc_recipients)
    message["Subject"] = subject

    body = [
        f"Deployment status: {status}",
        f"Deployment ID: {DEPLOYMENT_ID}",
        f"Bundle ID: {bundle_id}",
        f"Project: {BASE_PROJECT_ID}",
    ]
    if details:
        body.append(f"Details: {details}")
    message.set_content("\n".join(body))

    all_recipients = to_recipients + cc_recipients

    try:
        if smtp_use_tls:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)
                server.send_message(message, from_addr=smtp_from, to_addrs=all_recipients)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)
                server.send_message(message, from_addr=smtp_from, to_addrs=all_recipients)

        print(f"SUCCESS: Sent {status.lower()} deployment validation email to {', '.join(all_recipients)}")
    except Exception as exc:
        print(f"WARNING: Failed to send validation email: {exc}")

def run_workflow():
    print(f"--- DSS CI/CD WORKFLOW START (API Client: {getattr(dataikuapi, '__version__', '14.5.1')}) ---")
    
    dss_url = os.environ.get("DSS_URL")
    api_key = os.environ.get("DSS_API_KEY")
    event = os.environ.get("EVENT_NAME")
    is_merged = os.environ.get("PR_MERGED") == "true"

    if not dss_url or not api_key:
        print("ERROR: Missing DSS_URL or DSS_API_KEY.")
        sys.exit(1)

    client = dataikuapi.DSSClient(dss_url, api_key)

    if event == "push":
        branch = os.environ.get("PUSH_BRANCH")
        run_branch_scenario(client, branch)
    elif event == "pull_request":
        branch = os.environ.get("PR_HEAD_REF")
        if is_merged:
            print("--- ACTION: PR MERGED. Running scenario before deployment ---")
            run_branch_scenario(client, branch)
            print("--- ACTION: PR MERGED. Orchestrating Deployment ---")
            deploy_via_project_deployer(client)
        else:
            print("--- ACTION: PR CLOSED WITHOUT MERGE. No DSS action required. ---")
    else:
        print(f"DEBUG: Event {event} triggered no action.")

def run_branch_scenario(client, branch):
    if not branch:
        print("ERROR: Missing branch name for DSS scenario execution.")
        sys.exit(1)

    project_key = f"{BASE_PROJECT_ID}_{branch.upper().replace('/', '_')}"
    run_test_scenario(client, project_key)

def is_not_found_error(exc):
    status_code = getattr(exc, "http_status", None)
    if status_code == 404:
        return True

    message = str(exc).lower()
    return (
        "not found" in message
        or "does not exist" in message
        or "unknown deployment" in message
        or "notfoundexception" in message
    )

def get_or_create_deployment(deployer, bundle_id):
    try:
        deployment = deployer.get_deployment(DEPLOYMENT_ID)
        deployment.get_settings()
        print(f"DEBUG: Found existing deployment: {DEPLOYMENT_ID}")
        return deployment, False
    except Exception as exc:
        if not is_not_found_error(exc):
            raise

        print(f"DEBUG: Deployment '{DEPLOYMENT_ID}' not found. Creating new one...")
        deployment = deployer.create_deployment(DEPLOYMENT_ID, BASE_PROJECT_ID, DSS_DEFAULT_INFRA, bundle_id)
        print(f"SUCCESS: Created new deployment record: {DEPLOYMENT_ID}")
        return deployment, True

def build_bundle_id():
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return f"v-{sha[:7]}"

    run_id = os.environ.get("GITHUB_RUN_ID")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
    if run_id:
        attempt_suffix = f"-{run_attempt}" if run_attempt else ""
        return f"v-run-{run_id}{attempt_suffix}"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"v-manual-{timestamp}"

def update_setting_if_present(settings, attribute_name, value):
    if hasattr(settings, attribute_name):
        current_value = getattr(settings, attribute_name)
        if current_value != value:
            setattr(settings, attribute_name, value)
            return True
    return False

def format_deployment_status(status):
    parts = []
    for key in ("health", "state", "message", "error", "warnings", "details"):
        getter_name = f"get_{key}"
        value = None
        if hasattr(status, getter_name):
            try:
                value = getattr(status, getter_name)()
            except Exception:
                value = "<unavailable>"
        elif hasattr(status, key):
            value = getattr(status, key)
        if value not in (None, "", []):
            parts.append(f"{key}={value}")

    for attr_name in ("__dict__",):
        attr_value = getattr(status, attr_name, None)
        if isinstance(attr_value, dict) and attr_value:
            parts.append(f"{attr_name}={attr_value}")

    for serializer_name in ("to_json", "to_dict", "as_dict"):
        if hasattr(status, serializer_name):
            try:
                serialized = getattr(status, serializer_name)()
                if serialized not in (None, "", [], {}):
                    parts.append(f"{serializer_name}={serialized}")
            except Exception:
                parts.append(f"{serializer_name}=<unavailable>")

    if hasattr(status, "get_raw"):
        try:
            raw_value = status.get_raw()
            if raw_value not in (None, "", [], {}):
                parts.append(f"raw={raw_value}")
        except Exception:
            parts.append("raw=<unavailable>")

    if not parts:
        return str(status)
    return ", ".join(parts)

def log_deployment_status(status):
    summary = format_deployment_status(status)
    print(f"DEBUG: Deployment status: {summary}")

def sync_deployment_settings(target_deployment, bundle_id):
    settings = target_deployment.get_settings()
    changed = False

    changed = update_setting_if_present(settings, "bundle_id", bundle_id) or changed
    changed = update_setting_if_present(settings, "infra_id", DSS_DEFAULT_INFRA) or changed
    changed = update_setting_if_present(settings, "project_key", BASE_PROJECT_ID) or changed
    changed = update_setting_if_present(settings, "project_id", BASE_PROJECT_ID) or changed

    if changed:
        print(
            f"DEBUG: Saving deployment settings for bundle={bundle_id}, "
            f"infra={DSS_DEFAULT_INFRA}, project={BASE_PROJECT_ID}..."
        )
        settings.save(ignore_warnings=True)
    else:
        print("DEBUG: Deployment settings already match the expected bundle and infra.")

def ensure_update_succeeded(result):
    if not isinstance(result, dict):
        return

    state = str(result.get("state", "")).upper()
    if state in {"FAILED", "ERROR", "ABORTED", "CANCELED", "CANCELLED"}:
        raise RuntimeError(f"Project Deployer update finished in unexpected state: {state}")

    error = result.get("error")
    if isinstance(error, bool):
        if error:
            print(
                "DEBUG: Project Deployer returned error=True; "
                "continuing because deployment completion is verified separately."
            )
        return

    if error not in (None, False):
        raise RuntimeError(f"Project Deployer update returned an error: {result.get('error')}")

    if result.get("fatal"):
        raise RuntimeError(f"Project Deployer update reported a fatal condition: {result.get('fatal')}")

def wait_for_deployment_health(deployment, timeout_seconds=180, poll_seconds=5):
    import time

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status = deployment.get_status()
        health = status.get_health()
        print(f"DEBUG: Deployment health is {health}")
        if health == "ERROR":
            log_deployment_status(status)
            raise RuntimeError(f"Deployment entered ERROR health: {format_deployment_status(status)}")
        if health == "HEALTHY":
            return True
        time.sleep(poll_seconds)

    status = deployment.get_status()
    log_deployment_status(status)
    raise RuntimeError(
        f"Deployment did not become HEALTHY within {timeout_seconds}s. "
        f"Last status: {format_deployment_status(status)}"
    )

def wait_for_project_on_automation(client, project_key, timeout_seconds=180, poll_seconds=5):
    import time

    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            projects = client.list_projects()
            for project in projects:
                if isinstance(project, dict):
                    current_key = project.get("projectKey") or project.get("project_key")
                else:
                    current_key = getattr(project, "projectKey", None) or getattr(project, "project_key", None)

                if current_key == project_key:
                    return True
        except Exception as exc:
            if not is_not_found_error(exc):
                raise
            last_error = exc
            time.sleep(poll_seconds)

    if last_error:
        print(f"DEBUG: Automation project lookup still failing for {project_key}: {last_error}")
    return False

def deploy_via_project_deployer(client):
    bundle_id = build_bundle_id()
    try:
        auto_url = os.environ.get("DSS_AUTO_URL")
        auto_api_key = os.environ.get("DSS_AUTO_API_KEY")
        verify_automation_node = os.environ.get("VERIFY_AUTOMATION_NODE", "false").lower() == "true"
        automation_client = None
        if auto_url and verify_automation_node:
            if not auto_api_key:
                raise RuntimeError("Missing DSS_AUTO_API_KEY for automation-node validation.")
            automation_client = dataikuapi.DSSClient(auto_url, auto_api_key)
        project = client.get_project(BASE_PROJECT_ID)

        print(f"DEBUG: Creating bundle {bundle_id} on Design...")
        project.export_bundle(bundle_id)
        
        print(f"DEBUG: Publishing {bundle_id} to Project Deployer catalog...")
        project.publish_bundle(bundle_id)
        
        print(f"DEBUG: Initializing DSSProjectDeployer...")
        deployer = DSSProjectDeployer(client)
        
        # --- IDEMPOTENT DEPLOYMENT LOOKUP ---
        print(f"DEBUG: Checking if deployment '{DEPLOYMENT_ID}' already exists...")
        target_deployment, is_new_deployment = get_or_create_deployment(deployer, bundle_id)

        # --- UPDATE SETTINGS ---
        action = "Creating" if is_new_deployment else "Updating"
        print(f"DEBUG: {action} deployment settings to use bundle {bundle_id} on infra {DSS_DEFAULT_INFRA}...")
        sync_deployment_settings(target_deployment, bundle_id)

        # --- PUSH TO AUTOMATION ---
        print(f"DEBUG: Triggering Deployer update via start_update()...")
        # We use ignore_warnings=True to bypass the Govern timeout/warning
        try:
            update_execution = target_deployment.start_update(ignore_warnings=True)
        except TypeError:
            update_execution = target_deployment.start_update()

        print(f"DEBUG: Waiting for Automation node activation...")
        result = update_execution.wait_for_result()
        ensure_update_succeeded(result)

        if not wait_for_deployment_health(target_deployment):
            raise RuntimeError(
                f"Deployment {DEPLOYMENT_ID} did not reach HEALTHY state after update"
            )

        if automation_client:
            print(f"DEBUG: Verifying deployment directly on automation node at {auto_url}...")
            if not wait_for_project_on_automation(automation_client, BASE_PROJECT_ID):
                raise RuntimeError(
                    f"Project {BASE_PROJECT_ID} did not appear on automation node {auto_url} after deployer update"
                )
        
        # Log any warnings (like Govern being offline)
        warnings = result.get("warnings", [])
        for w in warnings:
            print(f"DSS WARNING: {w.get('message')}")

        send_validation_email("SUCCESS", bundle_id)
        print(f"SUCCESS: Deployment complete. {bundle_id} is ACTIVE.")

    except Exception as e:
        print(f"ERROR: Deployment orchestration failed: {str(e)}")
        if bundle_id:
            send_validation_email("FAILED", bundle_id, str(e))
        sys.exit(1)

def run_test_scenario(client, project_key):
    try:
        print(f"--- ACTION: TESTING FEATURE BRANCH: {project_key} ---")
        project = client.get_project(project_key)
        scenario = project.get_scenario(SCENARIO_ID)
        run = scenario.run_and_wait(no_fail=True)
        outcome = run.get_info().get('result', {}).get('outcome')
        print(f"--- RESULT: Scenario finished with outcome: {outcome} ---")
        if outcome in ['FAILED', 'ABORTED']:
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Feature branch test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()

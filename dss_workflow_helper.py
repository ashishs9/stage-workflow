import os
import sys
import dataikuapi
# Import the specific Project Deployer class for v14
from dataikuapi.dss.projectdeployer import DSSProjectDeployer

# --- CONFIGURATION ---
BASE_PROJECT_ID = "STRUCTUREDLEARNINGAGENTSAUTOMATION"
SCENARIO_ID = "PROJECT_QUALITY_CHECK"
DEPLOYMENT_ID = f"{BASE_PROJECT_ID}-on-ashish-automation" 

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

    if event == "pull_request" and is_merged:
        print(f"--- ACTION: PR MERGED. Orchestrating Deployment ---")
        deploy_via_project_deployer(client)
    elif event == "push" or (event == "pull_request" and not is_merged):
        branch = os.environ.get("PUSH_BRANCH") if event == "push" else os.environ.get("PR_HEAD_REF")
        project_key = f"{BASE_PROJECT_ID}_{branch.upper().replace('/', '_')}"
        run_test_scenario(client, project_key)
    else:
        print(f"DEBUG: Event {event} triggered no action.")

def deploy_via_project_deployer(client):
    try:
        project = client.get_project(BASE_PROJECT_ID)
        bundle_id = f"v-{os.environ.get('GITHUB_SHA', 'manual')[:7]}"
        
        print(f"DEBUG: Creating bundle {bundle_id} on Design...")
        project.export_bundle(bundle_id)
        
        print(f"DEBUG: Publishing {bundle_id} to Project Deployer catalog...")
        project.publish_bundle(bundle_id)
        
        print(f"DEBUG: Initializing DSSProjectDeployer...")
        deployer = DSSProjectDeployer(client)
        
        # --- IDEMPOTENT DEPLOYMENT LOOKUP ---
        infra_id = "ashish-automation"
        deployment_id = f"{BASE_PROJECT_ID}-on-{infra_id}"
        target_deployment = None

        print(f"DEBUG: Checking if deployment '{deployment_id}' already exists...")
        try:
            # Try to fetch the specific deployment by ID directly
            target_deployment = deployer.get_deployment(deployment_id)
            # Access a property to verify it actually exists on the server
            target_deployment.get_settings()
            print(f"DEBUG: Found existing deployment: {deployment_id}")
        except Exception:
            print(f"DEBUG: Deployment '{deployment_id}' not found. Creating new one...")
            # If fetch fails, we create it
            target_deployment = deployer.create_deployment(deployment_id, BASE_PROJECT_ID, infra_id, bundle_id)
            print(f"SUCCESS: Created new deployment record: {deployment_id}")

        # --- UPDATE SETTINGS ---
        print(f"DEBUG: Updating deployment settings to use bundle {bundle_id}...")
        settings = target_deployment.get_settings()
        settings.get_raw()['bundleId'] = bundle_id
        settings.save()

        # --- PUSH TO AUTOMATION ---
        print(f"DEBUG: Triggering Deployer update via start_update()...")
        # We use ignore_warnings=True to bypass the Govern timeout/warning
        try:
            update_execution = target_deployment.start_update(ignore_warnings=True)
        except TypeError:
            update_execution = target_deployment.start_update()

        print(f"DEBUG: Waiting for Automation node activation...")
        result = update_execution.wait_for_result()
        
        # Log any warnings (like Govern being offline)
        warnings = result.get("warnings", [])
        for w in warnings:
            print(f"DSS WARNING: {w.get('message')}")

        print(f"SUCCESS: Deployment complete. {bundle_id} is ACTIVE.")

    except Exception as e:
        print(f"ERROR: Deployment orchestration failed: {str(e)}")
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

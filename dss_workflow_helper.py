import os
import sys
import dataikuapi

BASE_PROJECT_ID = "STRUCTUREDLEARNINGAGENTSAUTOMATION"
SCENARIO_ID = "PROJECT_QUALITY_CHECK"

def run_workflow():
    client = dataikuapi.DSSClient(os.environ.get("DSS_URL"), os.environ.get("DSS_API_KEY"))
    event = os.environ.get("EVENT_NAME")
    
    # PATH A: Deployment (PR merged into master)
    if event == "pull_request" and os.environ.get("PR_MERGED") == "true":
        print("--- ACTION: PR MERGED. Deploying to Automation Node ---")
        deploy_to_automation(client)

    # PATH B: Testing (Push to feature branch OR open PR)
    elif event == "push" or (event == "pull_request" and os.environ.get("PR_MERGED") != "true"):
        # Determine branch name based on event type
        branch = os.environ.get("PUSH_BRANCH") if event == "push" else os.environ.get("PR_HEAD_REF")
        
        project_key = f"{BASE_PROJECT_ID}_{branch.upper().replace('/', '_')}"
        print(f"--- ACTION: TESTING FEATURE BRANCH: {project_key} ---")
        run_test_scenario(client, project_key)
        
    else:
        print(f"DEBUG: Event {event} (Merged: {os.environ.get('PR_MERGED')}) triggered no action.")

def run_test_scenario(client, project_key):
    try:
        project = client.get_project(project_key)
        scenario = project.get_scenario(SCENARIO_ID)
        run = scenario.run_and_wait(no_fail=True)
        outcome = run.get_info().get('result', {}).get('outcome')
        print(f"Test Result: {outcome}")
        if outcome in ['FAILED', 'ABORTED']:
            sys.exit(1)
    except Exception as e:
        print(f"Error testing {project_key}: {e}")
        sys.exit(1)

def deploy_to_automation(design_client):
    # (Insert the deploy_to_automation code from previous response here)
    pass

if __name__ == "__main__":
    run_workflow()

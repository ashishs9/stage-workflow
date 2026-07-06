import os
import subprocess
import shutil
import json


def run_command(command, cwd=None):
    """Executes shell commands and captures errors."""
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        return False, result.stderr
    return True, result.stdout


def update_scenario_notifications(scenario_path, recipient, cc_recipient):
    with open(scenario_path, "r") as f:
        data = json.load(f)

    steps = data.get("params", {}).get("steps", [])
    for step in steps:
        if step.get("type") != "send_report":
            continue

        config = (
            step.get("params", {})
            .get("messaging", {})
            .get("configuration", {})
        )
        if config:
            config["recipient"] = recipient
            if cc_recipient:
                config["ccRecipient"] = cc_recipient
            else:
                config.pop("ccRecipient", None)

    with open(scenario_path, "w") as f:
        json.dump(data, f, indent=4)


def setup_dss_repo():
    print("--- DSS CI/CD Project Initializer (v3) ---")

    # 1. Collect User Inputs
    project_id = input("Enter PROJECT_ID: ")
    new_repo_name = input("Enter name for NEW private repo: ")
    infra_id = input("Enter Target Automation Infrastructure ID (e.g., aut-node-01): ")
    email1 = input("Enter Recipient Email: ")
    email2 = input("Enter CC Email: ")

    source_repo = "git@github.com:ashishs9/stage-workflow.git"
    local_dir = os.path.abspath(f"./temp_setup_{project_id}")

    try:
        # 2. Create the Remote Repo via GitHub CLI
        print(f"\n> Creating private repository '{new_repo_name}'...")
        created, output = run_command(["gh", "repo", "create", new_repo_name, "--private"])

        if created:
            success, user_info = run_command(["gh", "api", "user", "--template", "{{.login}}"])
            if not success:
                print(f"❌ Could not determine authenticated GitHub user: {user_info}")
                return
            username = user_info.strip()
            dest_repo_url = f"git@github.com:{username}/{new_repo_name}.git"
            print(f"✅ Created: {dest_repo_url}")
        else:
            print("⚠️ Could not create repo via CLI. It may already exist.")
            dest_repo_url = input(f"Please enter the SSH URL for {new_repo_name}: ")

        # 3. Clone the Public Template
        print("> Cloning template...")
        if os.path.exists(local_dir):
            shutil.rmtree(local_dir)

        success, err = run_command(["git", "clone", source_repo, local_dir])
        if not success:
            print(f"❌ Clone failed: {err}")
            return

        # 4. Modify dss_workflow_helper.py
        helper_path = os.path.join(local_dir, "dss_workflow_helper.py")
        if os.path.exists(helper_path):
            print("> Injecting parameters into dss_workflow_helper.py...")
            with open(helper_path, "r") as f:
                lines = f.readlines()

            with open(helper_path, "w") as f:
                for line in lines:
                    if line.strip().startswith("BASE_PROJECT_ID"):
                        f.write(f'BASE_PROJECT_ID = "{project_id}"\n')
                    elif line.strip().startswith("DSS_DEFAULT_INFRA"):
                        f.write(f'DSS_DEFAULT_INFRA = "{infra_id}"\n')
                    else:
                        f.write(line)

        # 5. Modify scenarios/PROJECT_QUALITY_CHECK.json
        scenario_path = os.path.join(local_dir, "scenarios", "PROJECT_QUALITY_CHECK.json")
        if os.path.exists(scenario_path):
            print("> Updating scenario email configuration...")
            update_scenario_notifications(scenario_path, email1, email2)

        # 6. Push to New Private Repo (Master Branch)
        print("> Pushing finalized skeleton to remote master...")
        success, err = run_command(["git", "remote", "remove", "origin"], cwd=local_dir)
        if not success:
            print(f"❌ Could not remove template origin: {err}")
            return

        success, err = run_command(["git", "remote", "add", "origin", dest_repo_url], cwd=local_dir)
        if not success:
            print(f"❌ Could not add destination origin: {err}")
            return

        success, err = run_command(["git", "add", "."], cwd=local_dir)
        if not success:
            print(f"❌ Git add failed: {err}")
            return

        success, err = run_command(["git", "commit", "-m", f"Initial setup for {project_id} on infra {infra_id}"], cwd=local_dir)
        if not success:
            print(f"❌ Git commit failed: {err}")
            return

        success, err = run_command(["git", "branch", "-M", "master"], cwd=local_dir)
        if not success:
            print(f"❌ Could not set default branch to master: {err}")
            return

        success, err = run_command(["git", "push", "-u", "origin", "master"], cwd=local_dir)
        if success:
            print(f"\n🚀 SUCCESS! Project is ready at: {dest_repo_url}")
        else:
            print(f"\n❌ Push failed: {err}")

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

    finally:
        if os.path.exists(local_dir):
            print("> Cleaning up temporary files...")
            shutil.rmtree(local_dir)
            print("✨ Workspace clean.")


if __name__ == "__main__":
    setup_dss_repo()

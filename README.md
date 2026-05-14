# README: DSS CI/CD Workflow Guide

This document outlines the standardized process for creating, developing, and deploying Dataiku DSS projects using the `stage-workflow` template.

## 1. Initializing a New Repo
Before starting, ensure you have the GitHub CLI (`gh`) installed and authenticated.

1.  **Clone the Template:** Pull this repository to access the automation tools.
    ```bash
    git clone git@github.com:ashishs9/stage-workflow.git
    cd stage-workflow
    ```
2.  **Execute Setup Script:** Run the initialization script to generate your private project repository.
    ```bash
    python setup_dss_project.py
    ```
3.  **Provide Project Parameters:**
    * **PROJECT_ID:** Enter a unique ID (e.g., `MY_PROJECT_01`). **Note:** You must use this exact same ID when creating the project in DSS later.
    * **Repo Name:** Choose a name for your new private GitHub repository.
    * **Emails:** Provide the Recipient and CC addresses for automated quality reports.

---

## 2. Configuring Repository Secrets & Environments
Once the repository is created, you must configure the environment variables and secrets required for the automation scripts to communicate with your Dataiku DSS instance.

1.  **Navigate to GitHub Settings:** Go to your new repository on GitHub and select **Settings > Secrets and variables > Actions**.
2.  **Add Repository Secrets:** Create the following secrets to secure your credentials:
    * `DSS_API_KEY`: The API key generated from your DSS user profile or administration settings.
    * `DSS_URL`: The base URL of your Design node (e.g., `https://dss-design.yourcompany.com`).
    * `DSS_AUTO_URL`: The base URL of your Automation node (for deployment).
3.  **Add Environment Variables:** Under the "Variables" tab, add non-sensitive configuration:
    * `DSS_DEFAULT_INFRA`: The target infrastructure ID for deployment.

---

## 3. Initializing Project in DSS
Once your repository and secrets are ready, set up the corresponding project in Dataiku.

1.  **Create Blank Project:** In Dataiku DSS, create a new project and set the **Project Key** to the exact same `PROJECT_ID` used in the script.
2.  **Connect Git:** Go to **Settings > Version Control**. Link the project to your newly created private Git URL.
3.  **Sync Master:** Perform a **Pull** from the `master` branch to bring in the `dss_workflow_helper.py` and the `PROJECT_QUALITY_CHECK` scenario.
4.  **Create Feature Branch:**
    * From the DSS Git interface, create a new branch named `featurex`.
    * When prompted, choose to **duplicate the project** for this branch.
5.  **Develop & Push:** Make your changes in the `featurex` project. Once finished, use the DSS Git interface to **Push** changes to the `featurex` remote branch.
6.  **Automated Validation:** Pushing to the feature branch automatically triggers the `PROJECT_QUALITY_CHECK` scenario. On success, an email notification is sent to both the Recipient and CC users.

---

## 4. Merging Changes into Master Branch
After validation is complete, the changes must be promoted to the production-ready branch.

1.  **Open Merge Request (MR):** Navigate to the GitHub web interface for your private repo.
2.  **Create PR:** Create a Pull Request (or Merge Request) to merge `featurex` into `master`.
3.  **Review & Commit:** Once reviewed, perform the merge.
4.  **Deployment Trigger:** Committing to the `master` branch via the MR acts as the final trigger. This kicks off the CI/CD pipeline to:
    * Bundle the project.
    * Deploy the updated bundle to the **DSS Automation Node**.

---

### Workflow Summary

| Stage | Action | Outcome |
| :--- | :--- | :--- |
| **Setup** | Run Python Script | Private Repo created with Skeleton |
| **Config** | Set Secrets/Vars | Credentials secured for API calls |
| **Dev** | Push to `featurex` | Scenario runs & sends validation email |
| **Deploy** | Merge to `master` | Project bundled and pushed to Automation Node |

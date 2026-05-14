# README: DSS CI/CD Workflow Guide

This document outlines the automated process for creating, developing, and deploying Dataiku DSS projects using the `stage-workflow` template.

## 1. Initializing a New Repo
Before starting, ensure you have the GitHub CLI (`gh`) installed and authenticated.

1.  **Clone the Template:** Pull this repository to access the automation tools.
    ```bash
    git clone git@github.com:ashishs9/stage-workflow.git
    cd stage-workflow
    ```
2.  **Execute Setup Script:** Run the initialization script to generate your private project repository.
    ```bash
    python setup_script.py
    ```
3.  **Provide Project Parameters:**
    * **PROJECT_ID:** Enter a unique ID (e.g., `MY_PROJECT_01`). **Note:** You must use this exact same ID when creating the project in DSS later.
    * **Repo Name:** Choose a name for your new private GitHub repository. Hint: Use my-project-01 for consistency and traceability
    * **Emails:** Provide the Recipient and CC addresses for automated quality reports.
4.  **Automatic Cleanup:** The script will create the remote repo, push the skeleton files to the `master` branch, and clean up local temporary files automatically.

---

## 2. Initializing Project in DSS
Once your repository is ready, set up the corresponding project in Dataiku.

1.  **Create Blank Project:** In Dataiku DSS, create a new project and set the **Project Key** to the exact same `PROJECT_ID` used in the script.
2.  **Connect Git:** Go to **Settings > Version Control**. Link the project to your newly created private Git URL.
3.  **Sync Master:** Perform a **Pull** from the `master` branch to bring in the `dss_workflow_helper.py` and the `PROJECT_QUALITY_CHECK` scenario.
4.  **TODO:** Add starting datasets and other artifacts as needed to kick start the project
5.  **Create Feature Branch:**
    * From the DSS Git interface, create a new branch named `featurex`.
    * When prompted, choose to **duplicate the project** for this branch.
6.  **Develop & Push:** Make your changes in the `featurex` project. Once finished, use the DSS Git interface to **Push** changes to the `featurex` remote branch.
7.  **Automated Validation:** Pushing to the feature branch automatically triggers the `PROJECT_QUALITY_CHECK` scenario. On success, an email notification is sent to both the Recipient and CC users.

---

## 3. Merging Changes into Master Branch
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
| **Dev** | Push to `featurex` | Scenario runs & sends validation email |
| **Deploy** | Merge to `master` | Project bundled and pushed to Automation Node |

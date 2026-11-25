---
title: 5. Add the Workflow
parent: Chapters
nav_order: 5
---

# 5. Add the Workflow
{: .no_toc }

1. TOC
{:toc}

## Goal

Add the scheduled GitHub Actions workflow that backs up the previous UTC day as 24 hourly jobs.

## Steps

1. Save the workflow as `.github/workflows/backup-webserver-logs.yml` ([download it](files/backup-webserver-logs.yml)).
1. Set the four values in its `env` section: `LCP_PROJECT`, `LCP_SERVICE` (normally `webserver`), `S3_BUCKET` and
   `AWS_REGION`.

    {% raw %}
    ```yaml
    name: Backup Liferay Cloud webserver logs

    # Backs up the previous UTC day as 24 hourly files, fetched in parallel.
    # For a low-traffic environment, set the matrix to a single empty hour ("")
    # to fetch the whole day as one file instead.

    on:
      schedule:
        - cron: "30 1 * * *"          # 01:30 UTC daily (10:30 JST)
      workflow_dispatch:              # manual run; always backs up the previous UTC day

    permissions:
      id-token: write                 # required for AWS OIDC
      contents: read

    concurrency: backup-webserver-logs

    env:
      LCP_PROJECT: <PROJECT_ID>       # e.g. myproject-prd
      LCP_SERVICE: webserver
      S3_BUCKET: <BUCKET>
      AWS_REGION: <AWS_REGION>

    jobs:
      plan:
        # Fixes "yesterday" once for the whole run. Hourly jobs that start late,
        # and failed hours re-run later from GitHub, all use this same date.
        runs-on: ubuntu-latest
        timeout-minutes: 5
        outputs:
          date: ${{ steps.date.outputs.date }}
        steps:
          - id: date
            run: |
              d=$(date -u -d yesterday +%F)
              echo "date=$d" >> "$GITHUB_OUTPUT"
              echo "Backing up $d (UTC)"

      backup:
        needs: plan
        runs-on: ubuntu-latest
        timeout-minutes: 60
        strategy:
          fail-fast: false            # one failed hour must not cancel the others
          max-parallel: 4             # raise only after confirming with Liferay Cloud support
          matrix:
            hour: ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11",
                   "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"]
        name: backup ${{ needs.plan.outputs.date }}T${{ matrix.hour }}
        steps:
          - uses: actions/checkout@v4

          - name: Configure AWS credentials (OIDC)
            uses: aws-actions/configure-aws-credentials@v4
            with:
              role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
              aws-region: ${{ env.AWS_REGION }}

          - name: Install LCP CLI
            run: |
              # Install to a fixed folder: with no terminal attached, the installer
              # exits if its default folder is not writable.
              curl -fsSL https://cdn.liferay.cloud/lcp/stable/latest/install.sh \
                | bash -s stable latest "$HOME/.local/bin"
              echo "$HOME/.local/bin" >> "$GITHUB_PATH"
              "$HOME/.local/bin/lcp" version

          - name: Authenticate LCP CLI
            env:
              LCP_USER: ${{ secrets.LCP_USER }}
              LCP_PASSWORD: ${{ secrets.LCP_PASSWORD }}
            run: |
              # lcp 3.x has no token variable. With --no-browser and piped stdin,
              # it reads "<email> <password>" separated by a single space.
              # The account needs a Liferay Cloud password (SSO-only accounts
              # must set one first), and the password must not contain spaces.
              if [ -z "$LCP_USER" ] || [ -z "$LCP_PASSWORD" ]; then
                echo "::error::Secrets LCP_USER and LCP_PASSWORD must be set."; exit 1
              fi
              case "$LCP_PASSWORD" in
                *" "*) echo "::error::LCP_PASSWORD contains a space, which lcp login cannot read."; exit 1 ;;
              esac
              printf '%s %s' "$LCP_USER" "$LCP_PASSWORD" | lcp login --no-browser > /dev/null
              # Fail here, not later, if the account cannot see the environment.
              lcp list -p "$LCP_PROJECT" < /dev/null

          - name: Back up hour
            env:
              TARGET_DATE: ${{ needs.plan.outputs.date }}
              TARGET_HOUR: ${{ matrix.hour }}
            run: ./scripts/backup-webserver-logs.sh

          - name: Log out of LCP CLI
            if: always()
            run: lcp logout < /dev/null || true

      # Optional team alert when any hour failed. Replace with your Slack / Teams / email step.
      # notify:
      #   needs: [plan, backup]
      #   if: failure()
      #   runs-on: ubuntu-latest
      #   steps:
      #     - run: echo "Backup failed for $LCP_PROJECT ${{ needs.plan.outputs.date }}; re-run failed jobs."
    ```
    {% endraw %}

## How it's built

- **`plan` job:** works out "yesterday" once. Every hourly job uses that date, including one that starts late or is
  re-run later.
- **`backup` job:** a matrix of the 24 hours. `fail-fast: false` keeps the other hours running if one fails.
- **`max-parallel: 4`:** limits how many hours fetch at once. Each job signs in to Liferay Cloud and reads the log
  API separately, so raise it only after confirming with Liferay Cloud support that the extra load is acceptable.
- **Install LCP CLI:** installs into `~/.local/bin`. With no terminal attached, the installer exits if its default
  folder isn't writable, so the folder is given explicitly.
- **Low-traffic environments:** replace the hour list with a single empty value (`hour: [""]`) to fetch the whole day
  in one job and one file.

To back up more than one environment (for example UAT and production), copy the workflow once per environment, with
its own `concurrency` name, and make sure the service user can see every environment.

## Check

Commit the workflow to `main`. In GitHub, **Actions** lists **Backup Liferay Cloud webserver logs**, with a **Run
workflow** button.

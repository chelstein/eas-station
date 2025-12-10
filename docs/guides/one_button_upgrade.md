
The GitHub Actions workflow at [`.github/workflows/build.yml`](https://github.com/KR8MER/eas-station/blob/main/.github/workflows/build.yml) builds and publishes a fresh
`kr8mer/eas-station:latest` image whenever commits reach the `main` branch. You can treat the passing run as the guardrail that
unlocks a **one-button upgrade** experience for operators who maintain on-premises stations.

## 1. Make sure the pipeline stays green

1. Confirm the CI status badge at the top of the [README](https://github.com/KR8MER/eas-station/blob/main/README.md) is green before promoting a change.
2. If the workflow fails, inspect the run logs for container build issues, dependency errors, Hub authentication
   problems and fix them before shipping an upgrade.

workers. A single command can refresh the containers to the newest image that Actions just pushed:

Wrap those commands in a shell script or a systemd service unit so field operators can execute it with a single click, a kiosk
after the upgrade so operators can confirm the version change.

## 3. Gate upgrades on a passing workflow run

Pair the upgrade button with the status badge link. Before allowing an operator to execute the upgrade script, check the latest
workflow run using the GitHub REST API or the badge URL:

- Green badge → latest image built successfully and is safe to pull.
- Red badge → block the upgrade and direct the operator to contact the development team.

## 4. Optional: Publish versioned tags for rollback

The workflow currently ships only the `latest` tag. If you want the button to support rollbacks, extend the

```bash
TARGET_TAG=${1:-latest}
  --build app poller ipaws-poller
```

Exposing the tag as a parameter lets operators downgrade to the previous known-good build in one step while keeping the default
experience to pull the `latest` image.

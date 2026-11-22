# ImageBranch external uptime

Checks the public ImageBranch website and API readiness endpoint from GitHub-hosted Ubuntu runners. A five-minute schedule sends Feishu cards when an endpoint becomes unavailable or recovers. Three consecutive checks within each run reduce transient failures. Persistent failures generate a reminder at most once an hour.

The Feishu destination is stored exclusively in the repository Actions secret `FEISHU_ALERT_WEBHOOK`. No ImageBranch application source, user data, server credentials or webhook addresses belong in this repository.

Use **Actions → ImageBranch external uptime → Run workflow → test_notification** to send a labelled test. The normal workflow checks both endpoints and records only public availability state. Hourly check-ins keep repository activity current.

GitHub may delay scheduled jobs during heavy load. This monitor provides supplementary external coverage and does not guarantee an exact five-minute detection time.

Standard hosted runners in public repositories are free under GitHub's published billing terms. This workflow uses no paid runners, caches, uploaded artifacts or third-party subscriptions.

- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

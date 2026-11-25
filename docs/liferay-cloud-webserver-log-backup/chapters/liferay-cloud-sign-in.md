---
title: 3. Sign In to Liferay Cloud
parent: Chapters
nav_order: 3
---

# 3. Sign In to Liferay Cloud
{: .no_toc }

1. TOC
{:toc}

## Goal

Give the workflow a Liferay Cloud account it can sign in with when nobody is at the keyboard.

## How the CLI signs in without a browser

The Liferay Cloud CLI (`lcp`) has no token environment variable. With `lcp login --no-browser` and standard input
that isn't a terminal, which is always the case in GitHub Actions, it reads the email and password from standard
input, separated by a single space:

```bash
printf '%s %s' "$LCP_USER" "$LCP_PASSWORD" | lcp login --no-browser
```

The workflow in [chapter 5](workflow.html) does this in its *Authenticate LCP CLI* step.

## Steps

1. Create or choose a **dedicated Liferay Cloud service user** with view access to the target environment. Avoid a
   person's account.
1. Make sure the user has a **Liferay Cloud password**. Accounts created through SSO have none until one is set; the
   CLI shows a password-reset link for this.
1. Check that the password **contains no spaces**. The CLI splits its input on spaces, so it would be cut off. The
   workflow checks this and stops with a clear error.
1. In GitHub, under **Settings → Secrets and variables → Actions**, save the email as `LCP_USER` and the password as
   `LCP_PASSWORD`. Never commit them to the repository.

{: .important }
When the service user's password is changed or rotated, update `LCP_PASSWORD` at the same time, or every run fails
at the sign-in step.

{: .note }
A signed-in CLI stores an access token and a refresh token in `~/.lcp`. Copying that file into a secret works at
first, but each refreshed token is saved only on the throwaway runner, so the secret goes stale. Signing in with the
password on every run avoids that.

## Check

On a Linux or macOS machine, install the CLI if you don't have it, then sign in as the service user the same way the
workflow will:

```bash
curl -fsSL https://cdn.liferay.cloud/lcp/stable/latest/install.sh | bash
printf '%s %s' 'service-user@example.com' 'the-password' | lcp login --no-browser
lcp list -p <PROJECT_ID> < /dev/null
lcp logout
```

`lcp list` shows the environment's services, including `webserver`.

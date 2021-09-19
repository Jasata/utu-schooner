# GitHub API

Schooner expects each course to create a course-specific GitHub account, preferrably named after the course code (but can be chosen otherwise). It is also recommended that the email address used to create this account is the course-specific RT (Request Tracker) address, which in turn is supposed to be the course_code@domain.

## Rate Limit

(2021) GitHub gives each user account **5000 queries per hour**. This should be remembered, should this application ever see wider usage.

Source: [Rate limits for GitHub Apps](https://docs.github.com/en/developers/apps/building-github-apps/rate-limits-for-github-apps)

_Normal user-to-server rate limits  
User-to-server requests are rate limited at 5,000 requests per hour and per authenticated user. All OAuth applications authorized by that user, personal access tokens owned by that user, and requests authenticated with that user's username and password share the same quota of 5,000 requests per hour for that user._

## Authentication token format

As of March 31, 2021, the format of GitHub authentication tokens was updated. Different tokens are:

| Token type     | Token prefix    | Notes     |
|----------------|-----------------|-----------|
| [Personal Access Tokens](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token)  | `ghp_`  | **These are used to access collaborator repositories.**   |
| [OAuth Access Tokens](https://docs.github.com/en/developers/apps/authorizing-oauth-apps)  | `gho_` |     |
| [GitHub App User-to-Server Tokens](https://docs.github.com/en/developers/apps/identifying-and-authorizing-users-for-github-apps)  | `ghu_`  |   |
| [GitHub App Server-to-Server Tokens](https://docs.github.com/en/developers/apps/authenticating-with-github-apps#authenticating-as-an-installation)  | ?  |  |
| [Refresh Tokens](https://docs.github.com/en/developers/apps/refreshing-user-to-server-access-tokens) | `ghr_`  |    |


## Creating Personal Access Tokens

1. Login to GitHub (course account)
2. Enter "Settings" -> "Developer settings" -> "Personal access tokens"
3. Enter details:
    - **Note:** "schooner.utu.fi, DTEK0000", or similar descriptive note.
    - **Expiration:** `NEVER` for production use. (Consider using 30 or 90 days for development).
    - **Scopes:** `repo` ALL.
4. Click "Create" **and SAVE the token** (you cannot see if ever again).

## Testing Personal Access Tooken

**TODO:** Test by using authenticated access to query course's own account. Offering the accesstoken (for increased rate-limit) should return error status code if the token is expired / invalid.

## Checking Student GitHub Account

1. Does the account exist?  
   `https://api.github.com/users/variski` (appears to be public resource)  
   Simplest way is to just check the response status code: 200 for existing user and 404 for not found.  
   Source: [GitHub REST API Reference: Get a user](https://docs.github.com/en/rest/reference/users#get-a-user)  
   **IMPORTANT:** Unauthenticated users hav strict limit **60 queries per hour** (these are recorded in the response's HTTP header, `x-ratelimit-*` fields). Make sure authentication is used to have 5000 q/hr rate limit.
2. TBA

_Potentially interesting field in the GitHub user JSON is the `created_at`, if the student proclaims having done the required GitHub tasks and "that the system just doesn't work". A way to check when collaborator invitations are created, would be a good supplement._

## Secret Scanning

GitHub scans repositories for known types of secrets, to prevent fraudulent use of secrets that were committed accidentally. This, however (concerning GitHub generated tokens), works only with the updated tokens. Secret scanning will scan your entire Git history on all branches present in your GitHub repository for any secrets.

Secret scanning is automatically enabled on public repositories. When you push to a public repository, GitHub scans the content of the commits for secrets. If you switch a private repository to public, GitHub scans the entire repository for secrets.

The scanning detects large number of different secrets. See [About Secrets Scanning](https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning) for a complete list.

## Single File Downloads

`Git` does not support single file downloads, but most remote repositories do, as a HTTP download.

For binary files, "raw" version should work:
```
https://raw.githubusercontent.com/Jasata/pminstall/master/install.py
```

**But this different for PRIVATE repositories.** Raw links in GitHub get appended with a `token` that appear to allow access by unauthenticated parties:
```
https://raw.githubusercontent.com/Jasata/DTEK0000/master/E01-BlinkLed.X/main.c?token=AJAVMPU5HG4DT6FB6Y5R573BKADTI
```

**TODO:** Test if above-like raw link to a private repository can be used **without** the token, if the user is a collaborator in the file's repository and using `ghp_` personal access token. (Or in other words, are raw.githubusercontent.com links scripting friendly).

## Limiting cloning depth

A Git repository is a collection of "snapshots" (commits), which are all downloaded when the repository is cloned. For student submission evaluation, commits (or branches) are not usually important (unless, of course, running a Git course, I suppose).

- Submissions should be cloned only one commit deep.
- Only the primary branch should be cloned... _but how to know which one is it? Due to the dumb politically-correct virtue-signaling change, it may be `master` or `main` ...possibly even something else, instead of the defacto standard `master`. Now there obviously needs to be a way to find out what the name for the master is._

```python
import os
import git
import shutil
import tempfile

# Create temporary dir
t = tempfile.mkdtemp()
# Clone into temporary dir
git.Repo.clone_from('stack@127.0.1.7:/home2/git/stack.git', t, branch='master', depth=1)
# Copy desired file from temporary dir
shutil.move(os.path.join(t, 'setup.py'), '.')
# Remove temporary dir
shutil.rmtree(t)
```

# GitPython

_GitPython is a dependency for Schooner. It is worth keeping because its features outweight the appeal of sheding off one more dependency._

Requirements:
- **Python 3.7+**
- **Git 1.7.0+**
- GitDB
- typing_extensions

Installation:

    # pip3 install GitPython

## Resources

- [GitPython Docs.io](https://gitpython.readthedocs.io/en/stable/intro.html)

# Future Developments

## Creating an issues

Source: [GitHub REST API: Getting Started](https://docs.github.com/en/rest/guides/getting-started-with-the-rest-api#creating-an-issue)

Once basic testing gets implemented, it should be coupled with automated issue generation for errors detected in the test. Ideally, a student fixes issues identified by automated testing and closes the issues, triggering (how?) next fetch and test cycle ... until test has been satisfied and the submission is moved to human evaluation.


## Get familiar with CI

Source: [GitHub REST API Guide: Building a CI server](https://docs.github.com/en/rest/guides/building-a-ci-server)

Some concerns on just how "robust" this approach can be with erratically behaving and inexperienced students that have proven resourcefulness in inventing unimaginable things to do... We should nevertheless examine what CI has to offer, before evaluating which approach offers the least problems in stuent hands.

## GitHub Classrooms

Looks to be an organization-based approach where students join (are joined). Needs to be studied at some point.
# GitHub API

tumipo: Which type are we using? Add some basics on our usage.

## Authentication token format

As of March 31, 2021, the format of GitHub authentication tokens was updated. Different tokens are:

- [Personal Access Tokens](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token)
- [OAuth Access Tokens](https://docs.github.com/en/developers/apps/authorizing-oauth-apps)
- [GitHub App User-to-Server Tokens](https://docs.github.com/en/developers/apps/identifying-and-authorizing-users-for-github-apps)
- [GitHub App Server-to-Server Tokens](https://docs.github.com/en/developers/apps/authenticating-with-github-apps#authenticating-as-an-installation)
- [Refresh Tokens](https://docs.github.com/en/developers/apps/refreshing-user-to-server-access-tokens)

## Secret Scanning

GitHub scans repositories for known types of secrets, to prevent fraudulent use of secrets that were committed accidentally. This, however (concerning GitHub generated tokens), works only with the updated tokens. Secret scanning will scan your entire Git history on all branches present in your GitHub repository for any secrets.

Secret scanning is automatically enabled on public repositories. When you push to a public repository, GitHub scans the content of the commits for secrets. If you switch a private repository to public, GitHub scans the entire repository for secrets.

The scanning detects large number of different secrets. See [About Secrets Scanning](https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning) for a complete list.

# FTP Hash Deploy Action

> Deploy only changed files via FTP/FTPS — using server-side **Git-style hashing**.

No state files. No timestamp guesswork. The server tells you what it has. You upload only what changed.

## How it works

1. Uploads `hashme.php` to the server via FTPS
2. Fetches the server's file hashes via HTTP — computed as **Git blob hashes** (`SHA1(blob {len}\0{content})`)
3. Deletes `hashme.php`
4. Computes the same hashes locally
5. Uploads only files where hashes differ — deletes files no longer present locally

The hash algorithm is identical to Git's own object hashing. If a file has the same Git blob hash on server and locally, it is bit-for-bit identical and won't be re-uploaded.

## Usage

```yaml
- name: Deploy
  uses: Agundur-KDE/ftp-hash-deploy-action@v1
  with:
    ftp-host:     ${{ secrets.FTP_HOST }}
    ftp-user:     ${{ secrets.FTP_USER }}
    ftp-password: ${{ secrets.FTP_PASSWORD }}
    site-url:     https://example.com
    local-dir:    ./dist/
    server-dir:   /public_html/
```

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `ftp-host` | ✓ | — | FTP server hostname |
| `ftp-user` | ✓ | — | FTP username |
| `ftp-password` | ✓ | — | FTP password |
| `site-url` | ✓ | — | Public URL (for fetching hashes via `hashme.php`) |
| `ftp-port` | | `21` | FTP port |
| `ftps` | | `true` | Use FTPS explicit TLS |
| `local-dir` | | `./` | Local directory to deploy |
| `server-dir` | | `/` | Server directory (FTP path) |
| `dry-run` | | `false` | Show diff without uploading |

## Requirements

- Server must run **PHP** (for `hashme.php`)
- FTP or FTPS access
- Public HTTP access to the site URL during deploy

## vs. SamKirkland/FTP-Deploy-Action

| | FTP-Deploy-Action | ftp-hash-deploy-action |
|---|---|---|
| Change detection | Local state file | Server-side hash query |
| Hash algorithm | — | Git blob SHA1 |
| State drift | Possible (state file ≠ server) | Impossible (server is the source of truth) |
| PHP required | No | Yes |

Inspired by [SamKirkland/FTP-Deploy-Action](https://github.com/SamKirkland/FTP-Deploy-Action) (MIT).

## License

MIT © [Agundur-KDE](https://github.com/Agundur-KDE)

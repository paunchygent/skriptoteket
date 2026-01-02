---
type: reference
id: REF-home-server-cli-tools
title: "Reference: Home Server CLI Tools"
status: active
owners: "olof"
created: 2026-01-02
updated: 2026-01-02
topic: "Recommended CLI tools for Hemma"
---

Convenience tooling for server-side ops and troubleshooting.

## Install (hemma)

```bash
# Core helpers
ssh hemma "sudo apt-get update && sudo apt-get install -y ripgrep fd-find bat fzf jq tree"

# Make the commands match common expectations (Ubuntu names them batcat/fdfind)
ssh hemma "sudo ln -sf /usr/bin/batcat /usr/local/bin/bat && sudo ln -sf /usr/bin/fdfind /usr/local/bin/fd"

# Install mikefarah/yq v4 (apt 'yq' is not v4)
ssh hemma "sudo curl -fsSL https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -o /usr/local/bin/yq && sudo chmod +x /usr/local/bin/yq"
```

## Notes

- `ripgrep` provides `rg`
- `fd-find` provides `fdfind` (symlinked to `fd`)
- `bat` provides `batcat` (symlinked to `bat`)
- `yq` is installed to `/usr/local/bin/yq` so it wins over `/usr/bin/yq`

# Mnemo Sync — inspect or mirror the vault

## Show sync status

```bash
mnemo sync status
```

## Compare local and mirror health

```bash
mnemo sync health
```

## Mirror into a cloud-synced folder

```bash
mnemo sync mirror
```

Optional:

```bash
mnemo sync mirror --direction pull
mnemo sync mirror --direction both
```

If the mirror target is missing, set it with:

```bash
mnemo init ~/.mnemo/vault --mirror-dir "/path/to/cloud/folder"
```

---
type: runbook
id: RUN-script-bank-seeding
title: "Runbook: Script bank seeding (repo → DB)"
status: active
owners: "agents"
created: 2025-12-16
system: "skriptoteket"
---

Den här runbooken beskriver hur du seedar repo:ts “script bank” till databasen vid behov (t.ex. vid ny deploy eller
för att få upp realistiska exempelverktyg i Katalog).

Syftet är att kunna:

- Skapa exempelverktyg (metadata + scriptkod) i databasen på ett kontrollerat, idempotent sätt.
- Undvika att oavsiktligt skriva över admins manuella ändringar (sync är opt-in).

Script bank finns i:

- `src/skriptoteket/script_bank/`

CLI-kommando:

- `pdm run seed-script-bank`

## Förutsättningar

- Du har en **admin/superuser**-användare (för audit fields och behörighet).
- Du kör kommandot i samma miljö som appen (lokalt eller i web-containern).

## Säkerhetsprinciper (viktigt)

- Default-beteende är konservativt:
  - Om verktyget redan finns: ändra inte metadata eller kod utan `--sync-*`.
  - Se alltid först vad som sker med `--dry-run`.

## Körning (lokalt)

```bash
# Först: torrkörning
pdm run seed-script-bank --dry-run

# Seed allt (interaktiv prompt för admin/superuser credentials)
pdm run seed-script-bank

# Seed en specifik slug
pdm run seed-script-bank --slug ist-vh-mejl-bcc
```

### Opt-in sync (uppdatera redan existerande)

```bash
# Uppdatera tools.title/tools.summary till att matcha repo:t
pdm run seed-script-bank --sync-metadata

# Om ACTIVE-versionen skiljer sig: publicera en ny version från repo-scriptet
pdm run seed-script-bank --sync-code
```

### Kontroll av katalog-publicering

```bash
# Standard: publicerar tool om den har ACTIVE version
pdm run seed-script-bank

# Om du vill att verktyget inte ska synas i Katalog
pdm run seed-script-bank --no-publish
```

## Körning (produktion via Docker)

Kör i `skriptoteket-web`-containern (så att du får rätt `DATABASE_URL` och samma runtime deps som tjänsten):

```bash
sudo docker exec -it skriptoteket-web pdm run seed-script-bank --dry-run
sudo docker exec -it skriptoteket-web pdm run seed-script-bank
```

Tips: Kör `--slug ...` när du bara vill uppdatera ett specifikt verktyg.

## Verifiering

1. Gå till Katalog och kontrollera att verktyget syns (om `--publish`) och att titel/sammanfattning är rimliga.
2. Öppna admin-skripteditor för verktyget och kontrollera att:
   - Det finns en ACTIVE version (`tools.active_version_id` pekar på ACTIVE).
   - Koden i ACTIVE-versionen matchar repo-scriptet (om `--sync-code`).

## Felsökning

- “Insufficient permissions”: credentials måste vara admin/superuser.
- “Unknown profession/category slug”: script bank-entry refererar en slug som inte finns i taxonomy (migrations).
- Om `--publish` och du får fel: verktyget måste ha en ACTIVE version (`tools.active_version_id` + version.state=active).

## Rollback / ångra

- För att snabbt ta bort från Katalog: avpublicera verktyget i admin-vyn.
- För att backa kod:
  - Öppna skripteditor, välj en tidigare version, skapa ett nytt utkast baserat på den och publicera.
  - (Superuser-rollbackflöde är separat och kan byggas senare.)

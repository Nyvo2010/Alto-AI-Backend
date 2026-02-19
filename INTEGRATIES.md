# Functies per Integratie

| **Integratie** | **Functies** |
|----------------|--------------|
| **Discord** | → Verzenden van berichten<br>→ Reageren op mentions<br>→ Moderatie (verwijder spam)<br>→ Rollen herkennen en toepassen<br>→ Cooldowns respecteren |
| **Trello** | → Toon kaarten<br>→ Maak kaarten aan<br>→ Update kaarten (titel, beschrijving)<br>→ Verwijder kaarten (als toegestaan)<br>→ Labels/lijsten beheren |
| **Internet zoeken** | → Zoekopdrachten uitvoeren<br>→ Return URL’s/snippets<br>→ Filter blacklist/safety<br>→ Samenvattingen van gevonden inhoud |
| **Afbeeldingen genereren** | → Prompt verwerken<br>→ Genereer afbeelding<br>→ Return/opslaan output |
| **Eigen filesystem** | → Lees bestanden<br>→ Schrijf bestanden<br>→ Zoek binnen bestanden<br>→ Bestanden verwijderen (indien toegestaan) |
| **GitHub** | → Repo content lezen<br>→ Maak branches aan<br>→ Open PR’s<br>→ Lees issues<br>→ Plaats comments/issues |
| **Session summarize** | → Samenvat lopende sessie<br>→ Samenvat eerder chat history<br>→ Maak overzichtelijke bullet points |
| **GitLab** | → Lees projects<br>→ Issues/MRs maken<br>→ Comments toevoegen<br>→ Branch beheren |
| **Slack** | → Stuur berichten in channels<br>→ Reageer op mentions<br>→ DM users<br>→ Thread replies |
| **Linear** | → Toon issues/tickets<br>→ Maak issue aan<br>→ Update status/prio<br>→ Toepassen tags |
| **Asana** | → Taken tonen<br>→ Taken aanmaken<br>→ Taken toewijzen<br>→ Commentaar toevoegen |
| **Notion** | → Toon pagina’s<br>→ Lees properties<br>→ Update pagina’s<br>→ Maak subpagina’s/DB entries<br>→ Verwijder (indien toegestaan) |


# Integraties, Instellingen en Type (met ID keys)

| **Integratie** | **Instelling (Type) — ID (key)** |
|----------------|----------------------------------|
| **Discord (DC)** | → Toegestane servers — lijst — id: `dc.allowed_servers`<br>→ Toegestane channels — lijst — id: `dc.allowed_channels`<br>→ Wie mag praten — rollen/lijst users — id: `dc.allowed_speakers`<br>→ Geen @everyone — bool — id: `dc.forbid_everyone`<br>→ Wie mag er getagd worden met @ — rollen/lijst users — id: `dc.allowed_mentions`<br>→ Cooldown tussen berichten — tijd (sec) — id: `dc.message_cooldown_seconds`<br>→ Moderation filter (spam/invoer) — bool — id: `dc.moderation_filter_enabled` |
| **Trello kaarten** | → Welke borden — lijst — id: `trello.boards`<br>→ Welke lijsten (per bord) — lijst (object per board) — id: `trello.lists_by_board`<br>→ Mag kaarten verwijderen? — bool — id: `trello.allow_delete`<br>→ Mag kaarten aanpassen? — bool — id: `trello.allow_edit`<br>→ Mag kaarten aanmaken? — bool — id: `trello.allow_create`<br>→ Standaard labels toegestaan — lijst — id: `trello.default_labels` |
| **Internet zoeken / Web** | → Search providers (orded list) — lijst — id: `web.search_providers`<br>→ Max results — int — id: `web.max_results`<br>→ Blacklist domains/terms — lijst — id: `web.blacklist`<br>→ Summarization enabled — bool — id: `web.summarize_results` |
| **Afbeeldingen genereren** | → Default model — string — id: `img.model_default`<br>→ Max image size — string/int — id: `img.max_size`<br>→ Save outputs to storage — bool — id: `img.save_output`<br>→ Allowed styles/presets — lijst — id: `img.allowed_styles` |
| **Eigen filesystem** | → Read allowed paths — lijst — id: `fs.read_paths`<br>→ Write allowed paths — lijst — id: `fs.write_paths`<br>→ Search enabled — bool — id: `fs.search_enabled`<br>→ Allow delete — bool — id: `fs.allow_delete` |
| **GitHub** | → Allowed repos — lijst — id: `github.allowed_repos`<br>→ Allow create branches — bool — id: `github.allow_create_branches`<br>→ Allow open PRs — bool — id: `github.allow_open_prs`<br>→ Permissions scope — lijst/roles — id: `github.permissions` |
| **Session summarize** | → Enabled — bool — id: `session.summarize_enabled`<br>→ Max tokens / length — int — id: `session.summarize_max_tokens`<br>→ Auto-summarize interval (minutes) — int — id: `session.summarize_interval_minutes` |
| **GitLab** | → Allowed projects — lijst — id: `gitlab.allowed_projects`<br>→ Allow create MRs — bool — id: `gitlab.allow_create_mrs`<br>→ Comment as bot — bool — id: `gitlab.comment_as_bot` |
| **Slack** | → Allowed workspaces — lijst — id: `slack.allowed_workspaces`<br>→ Allowed channels — lijst — id: `slack.allowed_channels`<br>→ DM allowed — bool — id: `slack.allow_dm` |
| **Linear** | → Allowed teams — lijst — id: `linear.allowed_teams`<br>→ Default priority — string — id: `linear.default_priority` |
| **Asana** | → Allowed workspaces — lijst — id: `asana.allowed_workspaces`<br>→ Default assignee — string — id: `asana.default_assignee` |
| **Notion** | → Allowed pages/databases — lijst — id: `notion.allowed_pages`<br>→ Read properties — bool — id: `notion.read_properties`<br>→ Update allowed — bool — id: `notion.allow_update` |

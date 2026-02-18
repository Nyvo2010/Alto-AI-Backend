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


# Integraties, Instellingen en Type

| **Integratie** | **Instelling (Type)** |
|----------------|------------------------|
| **Discord (DC)** | → Toegestane servers — lijst<br>→ Toegestane channels — lijst<br>→ Wie mag praten — rollen/lijst users<br>→ Geen @everyone — bool<br>→ Wie mag er getagd worden met @ — rollen/lijst users<br>→ Cooldown tussen berichten — tijd (sec)<br>→ Moderation filter (spam/invoer) — bool |
| **Trello kaarten** | → Welke borden — lijst<br>→ Welke lijsten (per bord) — lijst<br>→ Mag kaarten verwijderen? — bool<br>→ Mag kaarten aanpassen? — bool<br>→ Mag kaarten aanmaken? — bool<br>→ Standaard labels toegestaan — lijst |
| **Internet zoeken** | → Zoekprovider — enum (Bing/Google/…)<br>→ Blacklist sites — lijst<br>→ Safety filter (NSFW/adult) — bool<br>→ Max links per zoekopdracht — int<br>→ Geen verdachte downloads — bool |
| **Afbeeldingen genereren** | → Model — enum<br>→ Max resolutie — int<br>→ Safe generation filter — bool |
| **Eigen filesystem** | → Root directory path — pad<br>→ Toegang alleen read/write? — enum<br>→ Max file grootte — int (MB) |
| **GitHub** | → Welke repos lezen — lijst<br>→ Welke repos schrijven — lijst<br>→ Branch/PR rechten? — bool<br>→ Issue aanmaken? — bool<br>→ Label/milestone updaten? — bool |
| **Summarize session history** | → Geen instellingen — — |
| **GitLab** | → Welke projects lezen — lijst<br>→ Welke projects schrijven — lijst<br>→ Issue/MR rechten? — bool<br>→ Wiki toegang? — bool |
| **Slack** | → Workspace ID — text<br>→ Toegestane channels — lijst<br>→ Wie mag praten — rollen/lijst<br>→ Cooldown tussen berichten — tijd (sec)<br>→ DMs toegestaan? — bool |
| **Linear** | → Org/Team — text<br>→ Welke projecten — lijst<br>→ Issue creatie? — bool<br>→ Issue updaten? — bool<br>→ Commentaar toevoegen? — bool |
| **Asana** | → Workspace/Team — text<br>→ Toegestane projects — lijst<br>→ Taken aanmaken? — bool<br>→ Taken aanpassen? — bool<br>→ Commentaar toevoegen? — bool |
| **Notion** | → Welk team — text<br>→ Welke pagina’s zien — lijst<br>→ Toevoegen toegestaan? — bool<br>→ Verwijderen mogelijk? — bool<br>→ Bewerken mogelijk? — bool<br>→ DB entries aanpassen? — bool |

# Overview asset provenance and usage limitations

## Yahoo first; NHL identity verification

The existing Yahoo parser intentionally excludes image/injury fields from public domain objects. The local compatibility tests explicitly cover ignored `headshot/url` and `status` fields. Nothing in Python, authentication, provider behavior, private snapshots or MCP was changed. No authenticated Yahoo requests or stored Yahoo data were used.

Yahoo's public developer/guide URLs could not be retrieved during this research. The [YFPY maintainer's model documentation](https://yfpy.uberfastman.com/models/) describes Yahoo `image_url`, `headshot.url`, player keys, status and selected position separately. This is schema evidence from the wrapper author, not a verified live Yahoo payload or a license. There is no approved Yahoo-to-NHL image identity crosswalk available here. Yahoo image URLs and NHL IDs must never be interchanged or synthesized from names.

The six NHL numeric IDs below were obtained from Wikidata property P3522, then independently checked against `https://api-web.nhle.com/v1/player/{id}/landing`, including exact numeric player ID and birth date. Wikidata P18 links that entity to its photograph. The selected photos and Commons attribution/license metadata were inspected individually. These are static identity/asset research observations from 2026-10-18, not a live fantasy-data source or current injury/availability feed.

## Authentic player photographs

All generated player portraits have been removed. Files in `public/assets/players/` are historical photographs, served locally. The same `PlayerHeadshot` component renders both roster and cinematic inspection views. It selects the curated asset by NHL ID and rejects a conflicting canonical name. Missing IDs, unavailable files and load errors show initials with an accessible explanation, never another player's photograph.

| Player           | NHL ID / Wikidata entity                                       | Photographer      | License                                                        | Original file record                                                                                                                   |
| ---------------- | -------------------------------------------------------------- | ----------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Cale Makar       | 8480069 / [Q29342308](https://www.wikidata.org/wiki/Q29342308) | Quintin Soloviev  | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | [File and attribution](<https://commons.wikimedia.org/wiki/File:Cale_Makar_playing_with_the_Avalanche_in_2020_(Quintin_Soloviev).jpg>) |
| Evan Bouchard    | 8480803 / [Q50347957](https://www.wikidata.org/wiki/Q50347957) | TheAHL            | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0)       | [File and attribution](https://commons.wikimedia.org/wiki/File:Evan_Bouchard.jpg)                                                      |
| Nathan MacKinnon | 8477492 / [Q1966594](https://www.wikidata.org/wiki/Q1966594)   | 5of7              | [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0) | [File and attribution](https://commons.wikimedia.org/wiki/File:Nathan_MacKinnon_Avalanche-2.jpg)                                       |
| Nikita Kucherov  | 8476453 / [Q1693680](https://www.wikidata.org/wiki/Q1693680)   | Resolute          | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) | [File and attribution](https://commons.wikimedia.org/wiki/File:Nikita_Kucherov_140103.png)                                             |
| Auston Matthews  | 8479318 / [Q20090644](https://www.wikidata.org/wiki/Q20090644) | Azadeh Kashani    | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | [File and attribution](https://commons.wikimedia.org/wiki/File:Auston_Matthews_9.jpg)                                                  |
| David Pastrnak   | 8477956 / [Q16224594](https://www.wikidata.org/wiki/Q16224594) | Bostonbruinsfan22 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | [File and attribution](<https://commons.wikimedia.org/wiki/File:David_pastrnak_2019_(cropped).jpg>)                                    |

The files retain their photographer's copyright and the licenses above; they are not relicensed under the application code license. Local `public/assets/players/NOTICE.txt` and the in-app Image credits panel carry attribution, source and license links. The UI crops photographs and applies dark gradient overlays; adaptations of BY-SA photos retain the same respective BY-SA license. No facial replacement or generated likeness is used. Photographer permission does not establish sponsorship, player endorsement or a blanket publicity/trademark clearance. The historical photos may show an older uniform or hairstyle and do not establish current team membership or health.

NHL's API supplied official mugshot URLs, but access to a URL does not establish a redistribution license. Those mugshots were not downloaded or substituted for the openly licensed photographs.

## Official NHL team logos

The user explicitly requested official logos after the usage limitation was explained. `src/media.ts` contains one centralized map for all 32 current clubs. Team IDs/names were matched exactly between [NHL team metadata](https://api.nhle.com/stats/rest/en/team) and [NHL standings](https://api-web.nhle.com/v1/standings/now). The returned official logo URLs identify each club; the corresponding verified `_dark.svg` variants suit the dark UI. Utah uses Mammoth ID 68 rather than historical Utah Hockey Club ID 59, despite their shared UTA abbreviation. Fictional/unknown teams receive text fallbacks.

The SVG files in `public/assets/teams/` are unchanged official NHL assets. They are checked for executable/event content and external resource references. `TeamMark` uses the same image-state handling in calendar, roster and inspection panels. CSS compensates for the official files' surrounding blank canvas without editing the logo artwork. Broken images use the club abbreviation.

**Rights limitation:** logos remain © NHL and the respective clubs. No redistribution or commercial-use license has been established for this project; the user's instruction to show them is not represented as a rights-holder grant. They are included for identification in this review prototype, without affiliation or endorsement. Before public/commercial distribution, resolve the use basis with the rights holder or replace them with the built-in fallbacks. See [NHL terms](https://www.nhl.com/info/terms-of-service), the [NHL published ownership notice](https://media.nhl.com/site/asset/public/ext/2023-24/2023-24Rulebook.pdf) and the distributed `public/assets/teams/NOTICE.txt`. Do not infer permission from public CDN access or the repository's code license.

## Other assets

`public/assets/arena.webp` is the original generated decorative arena, separate from all UI controls. Its original prompt: Create an original photographic background asset only, no UI/text, an indoor ice hockey arena viewed from high in the stands, rink in the lower third, roof trusses and spectators, electric-blue spotlights and deep midnight navy, no logos or watermarks.

Barlow/Barlow Condensed are bundled via Fontsource under SIL OFL (license text in `public/assets/font-licenses.txt`). Lucide UI icons retain their ISC package license. Fonts, photographs and logos are served locally; browser verification rejects external runtime requests. No scraper, paid image service, proxy or new dependency is introduced.

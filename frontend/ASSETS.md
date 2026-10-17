# Overview asset provenance

All sports data and artwork in this milestone are illustrative. No live provider data was used to produce or verify these images. The arena and portrait files were generated with Codex's built-in image generation tool, then resized/encoded as WebP for local delivery. They are discrete image assets, not UI screenshot composites. The generated images are not official NHL or player photographs and must not be used as factual evidence.

| File                                  | Purpose                               | Encoded size  |
| ------------------------------------- | ------------------------------------- | ------------- |
| `public/assets/arena.webp`            | Decorative arena background           | 281,730 bytes |
| `public/assets/player-feature.webp`   | Featured Cale Makar illustration      | 141,370 bytes |
| `public/assets/player-portraits.webp` | Six illustrated portraits, 3×2 sprite | 121,048 bytes |

The sprite is displayed through a reusable `PlayerAvatar`, with a full-name alternative and explicit synthetic-portrait label. The featured portrait is decorative behind an independently rendered full-name heading, jersey number, team and position. Typographic team shields are original simple UI marks, not official club logos.

Barlow and Barlow Condensed are bundled via `@fontsource`, under the SIL Open Font License; license texts are included in `public/assets/font-licenses.txt`. Lucide supplies code-native interface icons under its package's ISC license. No remote font, asset CDN or runtime image service is used. The repository's existing license is unchanged.

## Final generation prompts

**Arena:** Create an original photographic background asset ONLY, no UI and no text. Portrait 2:3 framing, an immense indoor ice hockey arena viewed from high in the stands, rink white ice in lower third, roof trusses and densely packed spectator tiers, icy electric blue spotlights, deep midnight navy and black palette. Photoreal, crisp sports editorial image, cinematic dark exposure with luminous blue rim lighting, diagonal rink boards. This is decorative backdrop for a narrow sidebar of a sophisticated hockey analytics application. No words, no logos, no graphics, no screens, no watermarks.

**Featured portrait:** Create a realistic sports editorial portrait asset, vertical 4:5. Cale Makar, adult Canadian professional hockey defenseman, in a dark navy hockey helmet with clear visor, burgundy and navy hockey uniform. Tight chest-up portrait, looking alert towards camera-left. Large portrait at right with dark blue icy arena texture and negative space on left. Cool blue rim lighting, detailed skin and uniform, high quality hockey editorial style. NO letters, no names, no words, no numbers, no team logos, no UI, no watermark. Original synthetic demonstration artwork for a hockey application, not a real news photograph.

**Portrait sprite:** Create a clean 3-column by 2-row contact sheet of SIX separate realistic male professional hockey player headshots, all identically cropped shoulder-up against solid very dark navy. No gaps or borders between the six equal square cells, canvas aspect ratio 3:2. Top row left to right: Cale Makar in navy/burgundy jersey, Evan Bouchard in navy/orange jersey, Nathan MacKinnon in navy/burgundy jersey. Bottom row left to right: Nikita Kucherov in blue jersey, Auston Matthews in blue jersey, David Pastrnak in black/gold jersey. Each is an adult athlete, recognizable editorial portrait style, consistent neutral cool light, visible face fills most of square. No helmets. No words, letters, number, labels, logos, UI or watermark. Original synthetic demo artwork, not actual photographs.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { players } from '../src/fixtures/overview';
import { playerPhotos, teamAssets } from '../src/media';

describe('Curated local asset registry', () => {
  it('has a licensed, correctly identified local photograph for every real fixture identity', () => {
    const notice = readFileSync('public/assets/players/NOTICE.txt', 'utf8');
    for (const player of players) {
      if (player.nhlId === undefined) continue;
      const photo = playerPhotos[player.nhlId];
      expect(photo?.name).toBe(player.name);
      expect(photo?.identitySource).toBe(
        `https://api-web.nhle.com/v1/player/${player.nhlId}/landing`,
      );
      expect(photo?.license).toMatch(/^CC BY/);
      expect(photo?.wikidata).toMatch(/^Q\d+$/);
      expect(notice).toContain(String(player.nhlId));
      expect(readFileSync(`public${photo?.src}`).byteLength).toBeGreaterThan(1000);
    }
  });

  it('covers every scheduled club with local official SVGs and disambiguates Utah', () => {
    expect(Object.keys(teamAssets)).toHaveLength(32);
    expect(teamAssets.UTA?.nhlId).toBe(68);
    expect(teamAssets.UTA?.name).toBe('Utah Mammoth');
    const source = readFileSync('src/fixtures/overview.ts', 'utf8');
    for (const code of source.matchAll(/\['([A-Z]{3})', '([A-Z]{3})'\]/g)) {
      expect(teamAssets[code[1]]).toBeDefined();
      expect(teamAssets[code[2]]).toBeDefined();
    }
    for (const [code, team] of Object.entries(teamAssets)) {
      expect(new URL(team.source).origin).toBe('https://assets.nhle.com');
      expect(new URL(team.source).pathname).toMatch(
        new RegExp(`/logos/nhl/svg/${code}_(?:secondary_)?dark\\.svg$`),
      );
      const svg = readFileSync(`public${team.logo}`, 'utf8');
      expect(svg).toContain('<svg');
      expect(svg).not.toMatch(/<script|<foreignObject|<image|<!DOCTYPE|<!ENTITY|\son\w+\s*=/i);
      expect(svg).not.toMatch(/(?:href|src)\s*=\s*["'](?:https?:|\/\/|data:)/i);
    }
  });
});

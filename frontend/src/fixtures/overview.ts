import type { Datum, Game, OverviewModel, Player } from '../view-model';
const known = <T>(value: T): Datum<T> => ({ state: 'verified', value });
const playerRows = [
  ['makar', 'Cale Makar', 8, 'COL', 'D', 'defense', 0, '@ STL · Mon 7:00', 48.6, 6.8],
  ['bouchard', 'Evan Bouchard', 2, 'EDM', 'D', 'defense', 1, '@ VGK · Tue 7:00', 43.2, 6.1],
  ['mackinnon', 'Nathan MacKinnon', 29, 'COL', 'C', 'forwards', 2, '@ STL · Mon 7:00', 52.1, 7.7],
  ['kucherov', 'Nikita Kucherov', 86, 'TBL', 'RW', 'forwards', 3, 'vs FLA · Tue 7:00', 48.9, 7.3],
  ['matthews', 'Auston Matthews', 34, 'TOR', 'C', 'forwards', 4, '@ BUF · Mon 7:00', 46.8, 6.9],
  ['pastrnak', 'David Pastrnak', 88, 'BOS', 'RW', 'forwards', 5, '@ DET · Mon 7:00', 44.2, 6.6],
] as const;
export const players: readonly Player[] = playerRows.map(
  ([id, name, number, team, position, group, avatar, nextGame, points, average], i) => ({
    id,
    name,
    number,
    team,
    position,
    group,
    avatar,
    nextGame,
    weeklyPoints: known(points),
    average: known(average),
    status:
      i === 5
        ? { state: 'unknown', reason: 'Player availability has not been supplied.' }
        : known('Active'),
    stats: [
      { label: 'GP', datum: known(17 + i) },
      {
        label: 'G',
        datum: known(4 + i),
      },
      { label: 'A', datum: known(15 + i) },
      { label: 'PTS', datum: known(19 + 2 * i) },
      { label: 'SOG', datum: known(52 + i * 3) },
      { label: 'BLK', datum: known(26 + i) },
    ],
  }),
);
const matchups = [
  [
    ['TOR', 'BUF'],
    ['BOS', 'DET'],
    ['NYR', 'CBJ'],
    ['COL', 'STL'],
    ['VGK', 'SJS'],
    ['ANA', 'LAK'],
  ],
  [
    ['FLA', 'TBL'],
    ['DAL', 'NSH'],
    ['WPG', 'MIN'],
    ['EDM', 'VGK'],
    ['CAR', 'SEA'],
    ['OTT', 'BOS'],
    ['NJD', 'MTL'],
    ['PIT', 'NYI'],
  ],
  [
    ['EDM', 'VAN'],
    ['COL', 'ANA'],
    ['VGK', 'SJS'],
    ['TOR', 'CBJ'],
    ['FLA', 'CAR'],
    ['LAK', 'DAL'],
    ['BOS', 'MTL'],
    ['DET', 'NYR'],
    ['WSH', 'PHI'],
    ['MIN', 'WPG'],
    ['SEA', 'CHI'],
  ],
  [
    ['CAR', 'WSH'],
    ['MIN', 'PIT'],
    ['NJD', 'SEA'],
    ['BOS', 'MTL'],
    ['BUF', 'OTT'],
    ['VAN', 'EDM'],
    ['ANA', 'LAK'],
    ['TOR', 'TBL'],
    ['NYR', 'NYI'],
  ],
  [
    ['TOR', 'MTL'],
    ['BOS', 'OTT'],
    ['LAK', 'CGY'],
    ['COL', 'CHI'],
    ['FLA', 'DAL'],
    ['MIN', 'WSH'],
    ['EDM', 'SEA'],
    ['NYR', 'PHI'],
    ['VAN', 'STL'],
    ['TBL', 'NSH'],
  ],
  [
    ['DAL', 'CHI'],
    ['COL', 'SEA'],
    ['EDM', 'ANA'],
    ['FLA', 'BUF'],
    ['MIN', 'NJD'],
    ['NYR', 'CAR'],
    ['PIT', 'LAK'],
    ['VGK', 'VAN'],
  ],
  [
    ['TBL', 'FLA'],
    ['MIN', 'WPG'],
    ['NSH', 'STL'],
    ['TOR', 'BUF'],
    ['BOS', 'DET'],
  ],
] as const;
export const overviewFixture: OverviewModel = {
  provenance: { kind: 'synthetic', label: 'DEMO · SYNTHETIC DATA' },
  weekStart: '2026-12-07',
  weekLabel: 'WEEK 14',
  season: '2026–27',
  players,
  days: matchups.map((pairs, index) => {
    const date = `2026-12-${String(7 + index).padStart(2, '0')}`;
    const games: readonly Game[] = pairs.map(([away, home], gameIndex) => ({
      id: `${date}-${away}-${home}`,
      away,
      home,
      time: gameIndex === 2 ? '10:30 PM' : gameIndex === 1 && index === 5 ? '10:00 PM' : '7:00 PM',
    }));
    return {
      date,
      games,
      count:
        index === 3
          ? {
              state: 'incomplete',
              value: games.length,
              reason: 'This fixture demonstrates partial coverage. The complete total is unknown.',
            }
          : known(games.length),
    };
  }),
};
export function daysForWeek(start: string) {
  if (start === overviewFixture.weekStart) return overviewFixture.days;
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(`${start}T12:00:00Z`);
    date.setUTCDate(date.getUTCDate() + index);
    return {
      date: date.toISOString().slice(0, 10),
      games: [],
      count: {
        state: 'unknown',
        reason: 'No synthetic schedule is loaded for this week.',
      } as const,
    };
  });
}
export const teamNames: Readonly<Record<string, string>> = {
  COL: 'Colorado Avalanche',
  EDM: 'Edmonton Oilers',
  TBL: 'Tampa Bay Lightning',
  TOR: 'Toronto Maple Leafs',
  BOS: 'Boston Bruins',
  NYR: 'New York Rangers',
};

import { ArrowDownWideNarrow, MoreVertical, Users } from 'lucide-react';
import { useState } from 'react';
import type { Player, PositionGroup } from '../view-model';
import { Button, DataValue, Panel, PlayerAvatar, TeamMark } from './primitives';
import { Tabs } from './Tabs';

const groups = [
  ['all', 'All Players'],
  ['forwards', 'Forwards'],
  ['defense', 'Defense'],
  ['goalies', 'Goalies'],
] as const;

export function RosterTable({
  players,
  allPlayers,
  group,
  onGroup,
  selectedId,
  onSelect,
  onNotice,
  referenceWeek,
}: {
  players: readonly Player[];
  allPlayers: readonly Player[];
  group: PositionGroup;
  onGroup: (group: PositionGroup) => void;
  selectedId?: string;
  onSelect: (id: string) => void;
  onNotice: (message: string) => void;
  referenceWeek: boolean;
}) {
  const [sortByPoints, setSortByPoints] = useState(false);
  const sorted = sortByPoints
    ? [...players].sort(
        (a, b) =>
          (b.weeklyPoints.state === 'verified' ? b.weeklyPoints.value : -Infinity) -
          (a.weeklyPoints.state === 'verified' ? a.weeklyPoints.value : -Infinity),
      )
    : players;
  return (
    <Panel className="roster-panel">
      <div className="roster-heading">
        <h2>
          <Users aria-hidden="true" /> My Roster
        </h2>
        <div className="roster-actions">
          <Button onClick={() => setSortByPoints(!sortByPoints)} aria-pressed={sortByPoints}>
            <ArrowDownWideNarrow size={13} /> Fantasy Points
          </Button>
          <span className="button period-label">{referenceWeek ? 'This Week' : 'Demo Period'}</span>
          <Button
            className="primary"
            aria-label="Compare players"
            onClick={() => onNotice('Player Comparison is planned for a later milestone.')}
          >
            Compare
          </Button>
        </div>
      </div>
      <Tabs
        className="roster-tabs"
        label="Roster position groups"
        value={group}
        onChange={onGroup}
        idPrefix="roster-tab"
        panelId="roster-results"
        items={groups.map(([key, label]) => ({
          value: key,
          label: (
            <>
              {label}{' '}
              <span>
                (
                {key === 'all'
                  ? allPlayers.length
                  : allPlayers.filter((p) => p.group === key).length}
                )
              </span>
            </>
          ),
        }))}
      />
      <div
        id="roster-results"
        role="tabpanel"
        aria-labelledby={`roster-tab-${group}`}
        className="roster-scroll"
      >
        <table aria-label="My roster">
          <thead>
            <tr>
              <th scope="col">SLOT</th>
              <th scope="col">PLAYER</th>
              <th scope="col">TEAM</th>
              <th scope="col">POS</th>
              <th scope="col">NEXT TEAM GAME</th>
              <th scope="col">FPTS L7</th>
              <th scope="col">AVG</th>
              <th scope="col">STATUS</th>
              <th scope="col">
                <span className="sr-only">Inspect</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((player) => (
              <tr key={player.id} className={selectedId === player.id ? 'selected-player' : ''}>
                <td>{player.position}</td>
                <td>
                  <button
                    className="player-name"
                    aria-label={`Inspect ${player.name}`}
                    aria-pressed={selectedId === player.id}
                    onClick={() => onSelect(player.id)}
                  >
                    <PlayerAvatar index={player.avatar} name={player.name} />
                    <span>{player.name}</span>
                  </button>
                </td>
                <td>
                  <span className="team-cell">
                    <TeamMark code={player.team} />
                    <span>{player.team}</span>
                  </span>
                </td>
                <td>{player.position}</td>
                <td className="next-game">{referenceWeek ? player.nextGame : 'Unknown'}</td>
                <td>
                  <DataValue datum={player.weeklyPoints} format={(n) => n.toFixed(1)} />
                </td>
                <td>
                  <DataValue datum={player.average} format={(n) => n.toFixed(1)} />
                </td>
                <td className="status-cell">
                  <DataValue datum={player.status} />
                </td>
                <td>
                  <button
                    className="row-menu icon-button"
                    aria-label={`Inspect details for ${player.name}`}
                    onClick={() => onSelect(player.id)}
                  >
                    <MoreVertical size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {players.length === 0 && (
          <div className="empty-roster">
            <Users size={28} />
            <p>No players match your filters.</p>
            <Button
              onClick={() =>
                onNotice('Clear the search or choose a different position group to see players.')
              }
            >
              Filter help
            </Button>
          </div>
        )}
      </div>
      <p className="roster-footnote">
        DEMO DATA <span>·</span> FANTASY STATS SUBJECT TO LEAGUE SCORING <span>·</span> TEAM GAME ≠
        PLAYER APPEARANCE
      </p>
    </Panel>
  );
}

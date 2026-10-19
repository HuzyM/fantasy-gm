import { isObservation } from '../api';
import { useState } from 'react';
import type { ScreenProps } from '../application';
import type { PositionGroup, Player } from '../view-model';
import { filterPlayers } from '../view-model';
import { RosterTable } from '../components/RosterTable';
import { PlayerInspection } from '../components/PlayerInspection';
import { ScreenHeading } from '../components/ScreenHeading';
import { Button, DataValue, Panel, TeamMark } from '../components/primitives';

function SlotSection({
  title,
  players,
  onSelect,
}: {
  title: string;
  players: readonly Player[];
  onSelect: (id: string) => void;
}) {
  return (
    <section className="panel slot-section" aria-label={`${title} (${players.length})`}>
      <h2>
        {title} ({players.length})
      </h2>
      {players.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Slot</th>
                <th>Player</th>
                <th>Team</th>
                <th>Injury report</th>
              </tr>
            </thead>
            <tbody>
              {players.map((p) => (
                <tr key={p.id}>
                  <td>
                    <DataValue datum={p.rosterSlot} />
                  </td>
                  <td>
                    <button className="text-button" onClick={() => onSelect(p.id)}>
                      {p.name}
                    </button>
                  </td>
                  <td>
                    <TeamMark code={p.team} />
                  </td>
                  <td>
                    <DataValue datum={p.injury} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>No players match these slot filters.</p>
      )}
    </section>
  );
}
export default function MyRoster({ search, players, onNavigate, onNotice, local }: ScreenProps) {
  const observed = isObservation(local?.view);
  const [group, setGroup] = useState<PositionGroup>('all');
  const [selected, setSelected] = useState<string | undefined>(players[0]?.id);
  const player = players.find((p) => p.id === selected);
  const filteredPlayers = filterPlayers(players, search, group);
  const slot = (p: Player) =>
    p.rosterSlot.state === 'verified' || p.rosterSlot.state === 'incomplete'
      ? p.rosterSlot.value
      : '';
  return (
    <div className="roster-page">
      <ScreenHeading
        title="My Roster"
        description="Inspect your players, statistics and reported roster slots."
      >
        <span className="button">
          {observed ? 'Reported roster · coverage unverified' : 'Week 14 · demo period'}
        </span>
      </ScreenHeading>
      <p className="source-banner">
        {observed
          ? 'Reported local roster · total, effective coverage, injuries and performance unknown · read-only'
          : 'Synthetic roster and statistics · real-player injury reports unknown · read-only'}
      </p>
      <div className={`roster-layout ${player ? '' : 'inspection-closed'}`}>
        <div className="roster-main">
          <Panel className="roster-summary">
            {[
              ['Roster size', players.length],
              ['Forwards', players.filter((p) => p.group === 'forwards').length],
              ['Defense', players.filter((p) => p.group === 'defense').length],
              ['Goalies', players.filter((p) => p.group === 'goalies').length],
              ['Projected points', 'Unavailable'],
              ['Appearances', 'Unconfirmed'],
            ].map(([label, value]) => (
              <div key={label}>
                <strong>{value}</strong>
                <span>{label}</span>
              </div>
            ))}
          </Panel>
          <RosterTable
            players={filteredPlayers}
            allPlayers={players}
            group={group}
            onGroup={setGroup}
            selectedId={selected}
            onSelect={setSelected}
            onNotice={onNotice}
            isDemo={!observed}
            referenceWeek={!observed}
            detailed
            onCompare={() => onNavigate('comparison', selected)}
          />
          <div className="roster-subsets">
            <SlotSection
              title="Bench"
              players={filteredPlayers.filter((p) => slot(p) === 'BN')}
              onSelect={setSelected}
            />
            <SlotSection
              title="Injured Reserve"
              players={filteredPlayers.filter((p) => ['IR', 'IR+'].includes(slot(p)))}
              onSelect={setSelected}
            />
          </div>
          <p className="muted">
            Reserve slots and reported injury designations are separate. Unknown does not mean
            healthy. Roster completeness and lineup legality are unverified.
          </p>
        </div>
        {player && (
          <div className="roster-side">
            <PlayerInspection
              key={player.id}
              player={player}
              onClose={() => setSelected(undefined)}
              isDemo={!observed}
              referenceWeek={!observed}
              onProfile={() => onNavigate('profile', player.id)}
            />
            <Panel className="read-only-actions">
              <h2>Roster actions</h2>
              <p>Transactions and lineup changes are outside this read-only app.</p>
              <Button disabled>Set lineup</Button>
              <Button disabled>Add / drop / trade</Button>
            </Panel>
          </div>
        )}
      </div>
    </div>
  );
}

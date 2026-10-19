import { Info } from 'lucide-react';
import { useState } from 'react';
import type { ScreenProps } from '../application';
import { PlayerInspection } from '../components/PlayerInspection';
import { RosterTable } from '../components/RosterTable';
import { WeekSchedule } from '../components/WeekSchedule';
import { ImageCredits } from '../components/ImageCredits';
import { daysForWeek, overviewFixture } from '../fixtures/overview';
import type { PositionGroup } from '../view-model';
import { filterPlayers, shiftWeek } from '../view-model';
import { isObservation, scheduleDays } from '../api';

export default function Overview({
  search,
  players,
  onNavigate,
  onNotice: setNotice,
  local,
}: ScreenProps) {
  const observed = isObservation(local?.view);
  const loadedStart = observed
    ? (local?.view?.schedule?.start ?? new Date().toISOString().slice(0, 10))
    : overviewFixture.weekStart;
  const [group, setGroup] = useState<PositionGroup>('all');
  const [selectedId, setSelectedId] = useState<string | undefined>(players[0]?.id);
  const [start, setStart] = useState(loadedStart);
  const [selectedDay, setSelectedDay] = useState(loadedStart);
  const [showNotes, setShowNotes] = useState(false);
  const [showCredits, setShowCredits] = useState(false);
  const selectedPlayer = players.find((player) => player.id === selectedId);
  const filtered = filterPlayers(players, search, group);
  const referenceWeek = !observed && start === overviewFixture.weekStart;
  function moveWeek(direction: number) {
    const next = shiftWeek(start, direction);
    setStart(next);
    setSelectedDay(next);
  }
  function resetWeek() {
    setStart(loadedStart);
    setSelectedDay(loadedStart);
  }
  return (
    <>
      <WeekSchedule
        days={observed ? scheduleDays(start, local?.view) : daysForWeek(start)}
        start={start}
        selectedDay={selectedDay}
        onSelectDay={setSelectedDay}
        onMove={moveWeek}
        onReset={resetWeek}
        isReference={referenceWeek}
        isObservation={observed}
      />
      <div className={`roster-layout ${selectedPlayer ? '' : 'inspection-closed'}`}>
        <RosterTable
          players={filtered}
          allPlayers={players}
          group={group}
          onGroup={setGroup}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onNotice={setNotice}
          isDemo={!observed}
          referenceWeek={referenceWeek}
          onCompare={() => onNavigate('comparison', selectedId)}
        />
        {selectedPlayer && (
          <PlayerInspection
            key={selectedPlayer.id}
            player={selectedPlayer}
            onClose={() => setSelectedId(undefined)}
            isDemo={!observed}
            referenceWeek={referenceWeek}
            onProfile={() => onNavigate('profile', selectedPlayer.id)}
          />
        )}
      </div>
      <footer className="demo-footer">
        <span>
          <span className="demo-indicator" />
          {observed ? 'SOURCE: LOCAL PROVIDER OBSERVATION' : 'SOURCE: SYNTHETIC FIXTURES'}
        </span>
        <p>
          {observed
            ? 'Read-only observation; roster coverage, injuries, performance and appearances unverified.'
            : 'No live connection. Synthetic statistics; historical licensed photos.'}
        </p>
        <button onClick={() => setShowCredits(!showCredits)} aria-expanded={showCredits}>
          Image credits
        </button>
        <button onClick={() => setShowNotes(!showNotes)} aria-expanded={showNotes}>
          <Info size={13} /> Data notes
        </button>
      </footer>
      {showCredits && <ImageCredits />}
      {showNotes && observed && (
        <section className="panel data-notes" aria-label="Data certainty notes">
          <h2>Local observations</h2>
          {local?.view?.provenance.map((note, i) => (
            <p key={i}>{note}</p>
          ))}
          <p>
            Yahoo IDs are not NHL IDs. No approximate name match, current injury, statistical
            forecast, roster completeness or appearance is inferred.
          </p>
        </section>
      )}
      {showNotes && !observed && (
        <section className="panel data-notes" aria-label="Data certainty notes">
          <h2>Clear about what we know</h2>
          <p>
            Performance and schedules are synthetic fixtures. Photographs and team identities have
            separate source records; real-player injury reports are unknown.
          </p>
          <dl>
            <div>
              <dt>Verified</dt>
              <dd>A supplied value validated within its source. Here that source is a fixture.</dd>
            </div>
            <div>
              <dt>Incomplete</dt>
              <dd>
                Observed values exist; the total remains unknown. Thursday demonstrates this state.
              </dd>
            </div>
            <div>
              <dt>Unknown</dt>
              <dd>
                A value was not supplied. Another week never becomes seven confirmed off-days.
              </dd>
            </div>
            <div>
              <dt>Unsupported</dt>
              <dd>No implemented source or meaning, such as a player game log.</dd>
            </div>
          </dl>
        </section>
      )}
    </>
  );
}

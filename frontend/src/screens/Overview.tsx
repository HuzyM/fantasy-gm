import { Info, X } from 'lucide-react';
import { useState } from 'react';
import { AppShell } from '../components/AppShell';
import { Button } from '../components/primitives';
import { PlayerInspection } from '../components/PlayerInspection';
import { RosterTable } from '../components/RosterTable';
import { WeekSchedule } from '../components/WeekSchedule';
import { ImageCredits } from '../components/ImageCredits';
import { daysForWeek, overviewFixture } from '../fixtures/overview';
import type { PositionGroup } from '../view-model';
import { filterPlayers, shiftWeek } from '../view-model';

export default function Overview() {
  const [search, setSearch] = useState('');
  const [group, setGroup] = useState<PositionGroup>('all');
  const [selectedId, setSelectedId] = useState<string | undefined>('makar');
  const [start, setStart] = useState(overviewFixture.weekStart);
  const [selectedDay, setSelectedDay] = useState(overviewFixture.weekStart);
  const [notice, setNotice] = useState('');
  const [showNotes, setShowNotes] = useState(false);
  const [showCredits, setShowCredits] = useState(false);
  const selectedPlayer = overviewFixture.players.find((player) => player.id === selectedId);
  const filtered = filterPlayers(overviewFixture.players, search, group);
  const referenceWeek = start === overviewFixture.weekStart;
  function moveWeek(direction: number) {
    const next = shiftWeek(start, direction);
    setStart(next);
    setSelectedDay(next);
  }
  function resetWeek() {
    setStart(overviewFixture.weekStart);
    setSelectedDay(overviewFixture.weekStart);
  }
  return (
    <AppShell search={search} onSearch={setSearch} onNotice={setNotice}>
      <WeekSchedule
        days={daysForWeek(start)}
        start={start}
        selectedDay={selectedDay}
        onSelectDay={setSelectedDay}
        onMove={moveWeek}
        onReset={resetWeek}
        isReference={referenceWeek}
      />
      <div className={`roster-layout ${selectedPlayer ? '' : 'inspection-closed'}`}>
        <RosterTable
          players={filtered}
          allPlayers={overviewFixture.players}
          group={group}
          onGroup={setGroup}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onNotice={setNotice}
          referenceWeek={referenceWeek}
        />
        {selectedPlayer && (
          <PlayerInspection
            key={selectedPlayer.id}
            player={selectedPlayer}
            onClose={() => setSelectedId(undefined)}
            referenceWeek={referenceWeek}
          />
        )}
      </div>
      <footer className="demo-footer">
        <span>
          <span className="demo-indicator" />
          SOURCE: SYNTHETIC FIXTURES
        </span>
        <p>No live connection. Synthetic statistics; historical licensed photos.</p>
        <button onClick={() => setShowCredits(!showCredits)} aria-expanded={showCredits}>
          Image credits
        </button>
        <button onClick={() => setShowNotes(!showNotes)} aria-expanded={showNotes}>
          <Info size={13} /> Data notes
        </button>
      </footer>
      {showCredits && <ImageCredits />}
      {showNotes && (
        <section className="panel data-notes" aria-label="Data certainty notes">
          <h2>Clear about what we know</h2>
          <p>All values on this page are synthetic fixtures, never verified sports information.</p>
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
      <div className={`notice ${notice ? 'visible' : ''}`} role="status" aria-live="polite">
        {notice && (
          <>
            <Info size={18} />
            <span>{notice}</span>
            <Button
              className="icon-button"
              aria-label="Dismiss notice"
              onClick={() => setNotice('')}
            >
              <X size={18} />
            </Button>
          </>
        )}
      </div>
    </AppShell>
  );
}

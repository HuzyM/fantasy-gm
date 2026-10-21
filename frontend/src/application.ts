import type { Player } from './view-model';
import type { LocalSession } from './useLocalSession';

export type Screen =
  | 'overview'
  | 'roster'
  | 'profile'
  | 'planner'
  | 'comparison'
  | 'league'
  | 'connections'
  | 'settings';
export interface ScreenProps {
  local?: LocalSession;
  search: string;
  players: readonly Player[];
  onNavigate: (screen: Screen, playerId?: string, context?: { comparisonStart: string }) => void;
  onNotice: (message: string) => void;
}
export interface DisplayPreferences {
  logos: boolean;
  compact: boolean;
  contrast: boolean;
}

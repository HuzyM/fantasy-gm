import type { Player } from './view-model';

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
  search: string;
  players: readonly Player[];
  onNavigate: (screen: Screen, playerId?: string) => void;
  onNotice: (message: string) => void;
}

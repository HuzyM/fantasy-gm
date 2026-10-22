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
  selectedId?: string;
  context?: NavigationContext;
  onNavigate: (screen: Screen, playerId?: string, context?: NavigationContext) => void;
  onNotice: (message: string) => void;
}
export interface NavigationContext {
  comparisonStart?: string;
  comparisonRightId?: string;
  reviewDate?: string;
  showPlan?: boolean;
}
export interface DisplayPreferences {
  logos: boolean;
  compact: boolean;
  contrast: boolean;
}

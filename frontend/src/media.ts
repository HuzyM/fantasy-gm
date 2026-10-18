/** Static public identity/asset research, checked 2026-10-18. No runtime provider calls. */
export interface PlayerPhoto {
  readonly name: string;
  readonly src: string;
  readonly wikidata: string;
  readonly birthDate: string;
  readonly identitySource: string;
  readonly source: string;
  readonly author: string;
  readonly license: string;
  readonly licenseUrl: string;
  readonly photoDate: string;
  readonly zoom: number;
  readonly x: number;
  readonly y: number;
}
export interface TeamAsset {
  readonly nhlId: number;
  readonly name: string;
  readonly logo: string;
  readonly source: string;
}
export const playerPhotos: Readonly<Record<number, PlayerPhoto>> = {
  '8480069': {
    name: 'Cale Makar',
    src: '/assets/players/8480069.jpg',
    wikidata: 'Q29342308',
    birthDate: '1998-10-30',
    identitySource: 'https://api-web.nhle.com/v1/player/8480069/landing',
    source:
      'https://commons.wikimedia.org/wiki/File:Cale_Makar_playing_with_the_Avalanche_in_2020_(Quintin_Soloviev).jpg',
    author: 'Quintin Soloviev',
    license: 'CC BY-SA 4.0',
    licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0',
    photoDate: '2020-01-06 22:13:41',
    zoom: 2.2,
    x: 67,
    y: 13,
  },
  '8480803': {
    name: 'Evan Bouchard',
    src: '/assets/players/8480803.jpg',
    wikidata: 'Q50347957',
    birthDate: '1999-10-20',
    identitySource: 'https://api-web.nhle.com/v1/player/8480803/landing',
    source: 'https://commons.wikimedia.org/wiki/File:Evan_Bouchard.jpg',
    author: 'TheAHL',
    license: 'CC BY 2.0',
    licenseUrl: 'https://creativecommons.org/licenses/by/2.0',
    photoDate: 'Taken on 26 January 2020, 06:11',
    zoom: 1.6,
    x: 54,
    y: 20,
  },
  '8477492': {
    name: 'Nathan MacKinnon',
    src: '/assets/players/8477492.jpg',
    wikidata: 'Q1966594',
    birthDate: '1995-09-01',
    identitySource: 'https://api-web.nhle.com/v1/player/8477492/landing',
    source: 'https://commons.wikimedia.org/wiki/File:Nathan_MacKinnon_Avalanche-2.jpg',
    author: '5of7',
    license: 'CC BY-SA 2.0',
    licenseUrl: 'https://creativecommons.org/licenses/by-sa/2.0',
    photoDate: '2013-12-06 20:23',
    zoom: 1.1,
    x: 50,
    y: 30,
  },
  '8476453': {
    name: 'Nikita Kucherov',
    src: '/assets/players/8476453.png',
    wikidata: 'Q1693680',
    birthDate: '1993-06-17',
    identitySource: 'https://api-web.nhle.com/v1/player/8476453/landing',
    source: 'https://commons.wikimedia.org/wiki/File:Nikita_Kucherov_140103.png',
    author: 'Resolute',
    license: 'CC BY-SA 3.0',
    licenseUrl: 'https://creativecommons.org/licenses/by-sa/3.0',
    photoDate: '2014-01-03',
    zoom: 2.4,
    x: 56,
    y: 16,
  },
  '8479318': {
    name: 'Auston Matthews',
    src: '/assets/players/8479318.jpg',
    wikidata: 'Q20090644',
    birthDate: '1997-09-17',
    identitySource: 'https://api-web.nhle.com/v1/player/8479318/landing',
    source: 'https://commons.wikimedia.org/wiki/File:Auston_Matthews_9.jpg',
    author: 'Azadeh Kashani',
    license: 'CC BY-SA 4.0',
    licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0',
    photoDate: '2020-01-09',
    zoom: 1.7,
    x: 55,
    y: 26,
  },
  '8477956': {
    name: 'David Pastrnak',
    src: '/assets/players/8477956.jpg',
    wikidata: 'Q16224594',
    birthDate: '1996-05-25',
    identitySource: 'https://api-web.nhle.com/v1/player/8477956/landing',
    source: 'https://commons.wikimedia.org/wiki/File:David_pastrnak_2019_(cropped).jpg',
    author: 'Bostonbruinsfan22',
    license: 'CC BY-SA 4.0',
    licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0',
    photoDate: '2019-09-14',
    zoom: 1.6,
    x: 51,
    y: 24,
  },
};
/** Logos are official copyrighted/trademarked assets, not covered by the code license. See ASSETS.md. */
export const teamAssets: Readonly<Record<string, TeamAsset>> = {
  ANA: {
    logo: '/assets/teams/ANA.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/ANA_dark.svg',
    name: 'Anaheim Ducks',
    nhlId: 24,
  },
  BOS: {
    logo: '/assets/teams/BOS.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/BOS_dark.svg',
    name: 'Boston Bruins',
    nhlId: 6,
  },
  BUF: {
    logo: '/assets/teams/BUF.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/BUF_dark.svg',
    name: 'Buffalo Sabres',
    nhlId: 7,
  },
  CAR: {
    logo: '/assets/teams/CAR.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/CAR_dark.svg',
    name: 'Carolina Hurricanes',
    nhlId: 12,
  },
  CBJ: {
    logo: '/assets/teams/CBJ.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/CBJ_dark.svg',
    name: 'Columbus Blue Jackets',
    nhlId: 29,
  },
  CGY: {
    logo: '/assets/teams/CGY.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/CGY_dark.svg',
    name: 'Calgary Flames',
    nhlId: 20,
  },
  CHI: {
    logo: '/assets/teams/CHI.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/CHI_dark.svg',
    name: 'Chicago Blackhawks',
    nhlId: 16,
  },
  COL: {
    logo: '/assets/teams/COL.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/COL_dark.svg',
    name: 'Colorado Avalanche',
    nhlId: 21,
  },
  DAL: {
    logo: '/assets/teams/DAL.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/DAL_dark.svg',
    name: 'Dallas Stars',
    nhlId: 25,
  },
  DET: {
    logo: '/assets/teams/DET.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/DET_dark.svg',
    name: 'Detroit Red Wings',
    nhlId: 17,
  },
  EDM: {
    logo: '/assets/teams/EDM.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/EDM_dark.svg',
    name: 'Edmonton Oilers',
    nhlId: 22,
  },
  FLA: {
    logo: '/assets/teams/FLA.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/FLA_dark.svg',
    name: 'Florida Panthers',
    nhlId: 13,
  },
  LAK: {
    logo: '/assets/teams/LAK.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/LAK_dark.svg',
    name: 'Los Angeles Kings',
    nhlId: 26,
  },
  MIN: {
    logo: '/assets/teams/MIN.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/MIN_dark.svg',
    name: 'Minnesota Wild',
    nhlId: 30,
  },
  MTL: {
    logo: '/assets/teams/MTL.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/MTL_dark.svg',
    name: 'Montréal Canadiens',
    nhlId: 8,
  },
  NJD: {
    logo: '/assets/teams/NJD.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/NJD_dark.svg',
    name: 'New Jersey Devils',
    nhlId: 1,
  },
  NSH: {
    logo: '/assets/teams/NSH.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/NSH_dark.svg',
    name: 'Nashville Predators',
    nhlId: 18,
  },
  NYI: {
    logo: '/assets/teams/NYI.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/NYI_dark.svg',
    name: 'New York Islanders',
    nhlId: 2,
  },
  NYR: {
    logo: '/assets/teams/NYR.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/NYR_dark.svg',
    name: 'New York Rangers',
    nhlId: 3,
  },
  OTT: {
    logo: '/assets/teams/OTT.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/OTT_dark.svg',
    name: 'Ottawa Senators',
    nhlId: 9,
  },
  PHI: {
    logo: '/assets/teams/PHI.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/PHI_dark.svg',
    name: 'Philadelphia Flyers',
    nhlId: 4,
  },
  PIT: {
    logo: '/assets/teams/PIT.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/PIT_dark.svg',
    name: 'Pittsburgh Penguins',
    nhlId: 5,
  },
  SEA: {
    logo: '/assets/teams/SEA.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/SEA_dark.svg',
    name: 'Seattle Kraken',
    nhlId: 55,
  },
  SJS: {
    logo: '/assets/teams/SJS.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/SJS_dark.svg',
    name: 'San Jose Sharks',
    nhlId: 28,
  },
  STL: {
    logo: '/assets/teams/STL.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/STL_dark.svg',
    name: 'St. Louis Blues',
    nhlId: 19,
  },
  TBL: {
    logo: '/assets/teams/TBL.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/TBL_dark.svg',
    name: 'Tampa Bay Lightning',
    nhlId: 14,
  },
  TOR: {
    logo: '/assets/teams/TOR.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/TOR_dark.svg',
    name: 'Toronto Maple Leafs',
    nhlId: 10,
  },
  UTA: {
    logo: '/assets/teams/UTA.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/UTA_dark.svg',
    name: 'Utah Mammoth',
    nhlId: 68,
  },
  VAN: {
    logo: '/assets/teams/VAN.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/VAN_dark.svg',
    name: 'Vancouver Canucks',
    nhlId: 23,
  },
  VGK: {
    logo: '/assets/teams/VGK.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/VGK_dark.svg',
    name: 'Vegas Golden Knights',
    nhlId: 54,
  },
  WPG: {
    logo: '/assets/teams/WPG.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/WPG_dark.svg',
    name: 'Winnipeg Jets',
    nhlId: 52,
  },
  WSH: {
    logo: '/assets/teams/WSH.svg',
    source: 'https://assets.nhle.com/logos/nhl/svg/WSH_secondary_dark.svg',
    name: 'Washington Capitals',
    nhlId: 15,
  },
};

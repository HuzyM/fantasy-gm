import { playerPhotos } from '../media';

export function ImageCredits() {
  return (
    <section className="panel image-credits" aria-label="Image credits">
      <h2>Photograph and logo credits</h2>
      <p>
        Historical photographs identify the players; they do not verify current teams, injuries or
        statistics. Cropping and dark overlays are applied in the UI. Photo adaptations retain the
        linked Creative Commons licenses.
      </p>
      <ul>
        {Object.entries(playerPhotos).map(([id, photo]) => (
          <li key={id}>
            <a href={photo.source} target="_blank" rel="noreferrer">
              {photo.name}
            </a>{' '}
            — {photo.author},{' '}
            <a href={photo.licenseUrl} target="_blank" rel="noreferrer">
              {photo.license}
            </a>
            . NHL ID {id}.
          </li>
        ))}
      </ul>
      <p>
        Official team logos © NHL and respective clubs; used for club identification. No affiliation
        or endorsement. Redistribution and commercial-use permission has not been established. See{' '}
        <a href="https://www.nhl.com/info/terms-of-service" target="_blank" rel="noreferrer">
          NHL terms
        </a>
        .
      </p>
      <p>
        Arena background: original generated decorative artwork. No generated player portraits
        remain.
      </p>
    </section>
  );
}

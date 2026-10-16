# FGM-004 scoring and roster compatibility audit

**Historical investigation:** The earlier blockers and proposed next steps below
are superseded for the supported application workflow. The human operator has
confirmed league/team selection, scoring, roster and position displays work and
match Yahoo. See the [current acceptance boundary](fgm-004-private-cli.md#acceptance-and-remaining-limitations).
This does not certify every scoring rule, completeness or lineup legality.

This records the earlier audit. The subsequent authorized
[private application implementation](fgm-004-private-cli.md) adds shared settings
normalization, explicit competition flags, optional slot labels and reported
roster facts with unresolved-state marking. Those corrections supersede the
earlier exclusions below; neither actual live trigger has been identified.

This audit uses code, public documentation and wholly synthetic responses. No
authenticated request, credential inspection or live response capture occurred.
The latest human-supplied fixed summary is evidence of stages reached, not of
the actual unsupported field or its meaning. No parser acceptance rules or
diagnostic reporting were changed: public evidence did not establish a safe
correction for either live trigger.

## Scoring classification

`contract_verifier.py::_scoring` classifies direct children of `settings`:

| Class | Current handling |
|---|---|
| `scoring_type`, `uses_fractional_points`, `uses_negative_points` | Exact namespace and no attributes; subsequent scalar, duplicate and flag checks remain required. |
| `stat_categories`, `stat_modifiers` | Strict containers, stat IDs, joins, Decimal values and applicability checks. |
| `roster_positions` | Separate strict slot validation after basic roster normalization. |
| `_SETTING_METADATA` | 31 explicit administrative scalar names, correct namespace, no attributes/children; duplicates fail. |
| `divisions` | Only the published division ID/name collection shape, with count and identity validation. |
| Everything else | UNVERIFIED; no substring-based classification or blanket ignore. |

`UNSUPPORTED_SCORING_SETTING` can mean an unknown direct name, a known metadata
name with attributes/nesting/wrong namespace, or attributes on a scoring scalar.
A settings wrapper with any attributes instead yields
`UNSUPPORTED_SCORING_CONTAINER`. A familiar spelling alone cannot establish that
the response matches the supported contract. Missing required scoring fields
still fail once classification permits their validation.

[Yahoo's reference](https://sports.yahoo.com/developer/docs/) distinguishes
league metadata from settings and lists settings subresources; it does not
provide an exhaustive current NHL settings XML schema. Its roster XML snippets
are PUT inputs, not proof of GET response structure. It documents date-organized
NHL rosters and the server's default date; this integration still never invents
a returned date.

The [YFPY Settings model](https://yfpy.uberfastman.com/models/#yfpy.models.Settings)
and [yfantasy XML Settings type](https://pkg.go.dev/github.com/famendola1/yfantasy/schema#Settings)
corroborate administrative names already handled. `uses_median_score` and
`has_multiweek_championship` concern competition/aggregation rather than a stat
weight alone; their complete NHL semantics remain unverified. Premium feature
containers also remain unresolved. No further harmless direct field was
established by this audit, so no new administrative exception was added.

The public [yahoo_fantasy_api League.settings implementation](https://github.com/spilchen/yahoo_fantasy_api/blob/master/yahoo_fantasy_api/league.py)
merges league metadata and settings into one result. Its documented flattened
example therefore cannot establish that every returned key is a direct XML
settings child. In particular, importing the whole flattened key list would
broaden the wrong contract. Reference clients' permissive parsing, defaults,
storage and logging behavior are not adopted here.

## Exact roster rejection boundary

`fantasy.py::_roster_envelope` validates the selected team key and any supplied
team ID, obtains exactly one roster, then calls `_known_children`. That call is
the only source of `ROSTER_STRUCTURE / UNSUPPORTED_STRUCTURE` in this flow:

- The roster wrapper must have no attributes.
- Direct children must be `coverage_type`, `date`, `week`, `is_editable` or
  `players`, in the same supported Yahoo namespace.
- Those children must have no attributes, except `players` may have `count`.

The latest last-stop code therefore establishes that the roster GET and team
identity checks were reached. It does not identify which rule above rejected
the response. Unknown optional team metadata is already ignored. Player
metadata, eligible positions and selected positions are inspected later and
cannot explain this particular last-stop code. Missing/duplicate players
collections, inconsistent counts and required identity mismatches instead fail
validation; unsupported normalization would leave ROSTER_STRUCTURE PASS.

Both published XML namespace URIs are supported. Namespace declarations and
lexical prefixes are resolved by the XML parser, not treated as wrapper
attributes. Wrong namespace bindings remain unsupported. No evidence supports
blanket acceptance of other wrapper or pagination attributes.

The [yfantasy Roster and SelectedPosition XML types](https://pkg.go.dev/github.com/famendola1/yfantasy/schema#Roster)
corroborate the existing coverage/date/players and assignment child fields. The
[YFPY Roster model](https://yfpy.uberfastman.com/models/#yfpy.models.Roster)
additionally recognizes `is_prescoring` as a numeric boolean, while explicitly
leaving its meaning as a TODO in source. This identifies a public compatibility
candidate, not the live trigger, an NHL XML contract, or proof of harmlessness.
Silently discarding it could conceal a state relevant to scoring-effective
coverage. It remains unsupported until its XML location/shape and semantics can
be established. It is not translated into a date, position or completeness flag.

Ordinary optional team logos/managers and player status/headshot/editorial
metadata already leave basic roster normalization unchanged. Consumed identity,
eligibility, selected position and coverage fields retain strict validation.
NFL examples do not establish NHL reserve behavior, applicability, coverage or
completeness. No additional roster exception was justified.

## Private evidence still missing and approved inspection

At audit time, the alternate-screen panel showed only qualified settings names
and could not identify roster shape mismatches. The subsequently approved
[minimal structural view](nhl-contract-verification.md#settings-classification-evidence-and-private-inspection)
now shows bounded rejected-node names, fixed parent paths, namespace labels,
attribute names and content shape for these two blockers. It shows no values or
raw XML and changes no parser acceptance or status rules.

One separately approved private session can now use the same in-memory
responses and existing panel to obtain this missing evidence:

1. For scoring, identify the exact direct child's qualified name, attribute
   names and whether it has child elements. Match the same location and shape
   to a public contract; do not infer semantics from a similar name.
2. For roster, identify whether the rejection concerns a wrapper attribute,
   direct child name/namespace or child attribute. Inspect names and structural
   shape locally, without values, fragments, raw XML or player/account metadata.
3. Establish any effect on scoring, coverage or lineup interpretation before
   accepting a new state field. Otherwise retain UNVERIFIED.

The later inspection patch implements only this small prerequisite. It adds no
endpoint, request, report fields, persistence or diagnostic engine. It caps the
view at four rejected nodes and four attribute/child names per node; long names
are escaped/truncated and unknown namespace URIs are hidden. Deeper structures
and undocumented semantics may therefore remain unresolved after a session.
Do not copy even structural live-derived details to AI tools, notes or fixtures.
Only public source references and the existing fixed summary are shareable.

## Shortest completion path and private CLI behavior

| Capability | Existing foundation and proposed human CLI behavior |
|---|---|
| League selection | Current discovery and private explicit menu are reusable. Only discovered leagues may be selected. |
| Owned-team selection/identity | Existing ownership and league-membership cross-checks support multiple owned teams and a private explicit menu. Invalid/unowned selections must prevent roster GET. |
| Basic roster facts | Existing provider normalizes supported identities, names, reported positions, coverage and count in memory. Show only after normalization succeeds, labelled as reported fields; absence stays unknown. |
| League configuration | League identity is available. Settings/scoring currently have verifier checks/private comparisons, not a normalized domain contract or a production settings method. Do not advertise configuration retrieval as complete. |
| Unsupported areas | Use fixed unavailable labels: scoring unsupported, roster unsupported, coverage unknown, capacity unverified or completeness unverified. Preserve successful independent team results. No retry, fallback guess or automatic PASS. |

The current executable remains a contract verifier, not the finished personal
league/roster application. Its roster comparison panel runs after slot parsing;
it does not yet offer an independent basic-roster display when slots are
unsupported. A later minimal CLI integration should show normalized roster
facts before optional slot/completeness assessment and preserve independent
results. Reuse Team/Roster models, private terminal escaping and existing guards;
do not return Yahoo XML, expose MCP tools or add another provider framework.

The shortest remaining sequence is: obtain the missing private structural
evidence with the narrow view above; make one evidence-backed parser change per
actual mismatch with synthetic tests; privately establish scoring joins/weights,
position scopes, slots, NHL coverage and roster completeness; then finish the
minimal settings/scoring domain contracts and one human-operated workflow.
Scoring and completeness remain unavailable until their own evidence exists.
After structural evidence is established, prioritize the settings/scoring,
roster and private CLI work; no generalized verifier expansion is recommended.

## Offline regression evidence

`tests/test_contract_compatibility.py` reproduces the exact first/last status
pattern through distinct invented envelope shapes, proving why the report
cannot identify the live trigger. It also checks familiar settings names with
unfamiliar shapes, ignored ordinary team/player metadata, both Yahoo namespace
URIs and explicit prefixes. Mocked HTTP, blocked file access, absent logging and
exact fixed summaries cover the privacy boundary. No live fixtures are used.

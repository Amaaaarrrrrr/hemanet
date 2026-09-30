# ADR-009 — Coordinates + haversine now, PostGIS in V1

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** Store `latitude/longitude` numerics; compute distance with bounding box + haversine SQL behind `geo.find_within_radius()`. Introduce PostGIS (geography column + GiST index, backfilled by migration) when radius queries or transfer planning need it.
- **Alternatives:** PostGIS from day one (small cost, but adds an extension dependency to every environment and more to learn); external maps APIs for distance (cost, latency, dependency, privacy).
- **Reason:** Adequate at pilot scale; the migration path is trivial because the interface is stable.
- **Consequences:** Straight-line distance only (not travel time); acceptable for ranking.

// V2 initial schema migration
// Version: 2.0.0
// Source:  docs/v2/GRAPH_SCHEMA_V2.md §3
//
// Run this against a Neo4j 5.x instance before any V2 code paths execute.
// Idempotent — safe to re-run. Validated by validate_graph_schema.py.

// -- Uniqueness constraints -------------------------------------------------
CREATE CONSTRAINT brand_id IF NOT EXISTS FOR (b:Brand) REQUIRE b.id IS UNIQUE;
CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT scene_id IF NOT EXISTS FOR (s:Scene) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT placement_id IF NOT EXISTS FOR (p:Placement) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT camera_id IF NOT EXISTS FOR (c:Camera) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT interaction_id IF NOT EXISTS FOR (i:Interaction) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT render_id IF NOT EXISTS FOR (r:Render) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT color_hex IF NOT EXISTS FOR (c:Color) REQUIRE c.hex IS UNIQUE;

// -- Existence constraints --------------------------------------------------
CREATE CONSTRAINT brand_name IF NOT EXISTS FOR (b:Brand) REQUIRE b.name IS NOT NULL;
CREATE CONSTRAINT brand_version IF NOT EXISTS FOR (b:Brand) REQUIRE b.schema_version IS NOT NULL;
CREATE CONSTRAINT asset_type IF NOT EXISTS FOR (a:Asset) REQUIRE a.asset_type IS NOT NULL;
CREATE CONSTRAINT scene_context IF NOT EXISTS FOR (s:Scene) REQUIRE s.deployment_context IS NOT NULL;

// -- Vector index on Asset embeddings ---------------------------------------
CREATE VECTOR INDEX asset_clip_embedding IF NOT EXISTS
FOR (a:Asset) ON (a.clip_embedding)
OPTIONS { indexConfig: { `vector.dimensions`: 768, `vector.similarity_function`: 'cosine' } };

// -- Range / lookup indexes -------------------------------------------------
CREATE INDEX interaction_session IF NOT EXISTS FOR (i:Interaction) ON (i.session_id);
CREATE INDEX interaction_timestamp IF NOT EXISTS FOR (i:Interaction) ON (i.timestamp);
CREATE INDEX asset_status IF NOT EXISTS FOR (a:Asset) ON (a.ingestion_status);
CREATE INDEX render_scene IF NOT EXISTS FOR (r:Render) ON (r.scene_id);

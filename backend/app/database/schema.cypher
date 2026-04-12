# Neo4j Graph Schema for Brand-Aligned Content Platform
# Run these commands in Neo4j Browser to set up the schema

# ========================
# CONSTRAINTS (Uniqueness)
# ========================

# Brand ID must be unique
CREATE CONSTRAINT brand_id IF NOT EXISTS 
FOR (b:Brand) REQUIRE b.id IS UNIQUE;

# Color hex codes should be unique (avoid duplicate color nodes)
CREATE CONSTRAINT color_hex IF NOT EXISTS 
FOR (c:Color) REQUIRE c.hex IS UNIQUE;

# ========================
# INDEXES (Performance)
# ========================

# Index on brand website for faster lookups
CREATE INDEX brand_website IF NOT EXISTS 
FOR (b:Brand) ON (b.website);

# Index on brand name for searching
CREATE INDEX brand_name IF NOT EXISTS 
FOR (b:Brand) ON (b.name);

# Index on product name for searching
CREATE INDEX product_name IF NOT EXISTS 
FOR (p:Product) ON (p.name);

# ========================
# SAMPLE DATA (For Testing)
# ========================

# Create a sample brand
CREATE (b:Brand {
  id: 'sample01',
  name: 'Sunrise Coffee',
  website: 'https://sunrisecoffee.com',
  tagline: 'Start your day with sunshine in a cup',
  industry: 'Food & Beverage',
  created_at: datetime()
})

# Add logo
CREATE (l:Logo {
  url: 'https://example.com/logo.png',
  quality_score: 0.85,
  source: 'scraped'
})

# Add colors
CREATE (c1:Color {hex: '#8B4513', name: 'Coffee Brown'})
CREATE (c2:Color {hex: '#FFD700', name: 'Sunrise Gold'})
CREATE (c3:Color {hex: '#F5F5DC', name: 'Cream'})

# Add products
CREATE (p1:Product {
  id: 'prod01',
  name: 'House Blend',
  price: '$15',
  category: 'Coffee',
  description: 'Our signature medium roast blend'
})
CREATE (p2:Product {
  id: 'prod02', 
  name: 'Cold Brew',
  price: '$5',
  category: 'Coffee',
  description: 'Smooth, refreshing cold-brewed coffee'
})

# Connect relationships
MATCH (b:Brand {id: 'sample01'}), (l:Logo {url: 'https://example.com/logo.png'})
CREATE (b)-[:HAS_LOGO]->(l);

MATCH (b:Brand {id: 'sample01'}), (c:Color)
WHERE c.hex IN ['#8B4513', '#FFD700', '#F5F5DC']
CREATE (b)-[:USES_COLOR]->(c);

MATCH (b:Brand {id: 'sample01'}), (p:Product)
WHERE p.id IN ['prod01', 'prod02']
CREATE (b)-[:SELLS]->(p);

# ========================
# USEFUL QUERIES
# ========================

# Get full brand context (for content generation)
# MATCH (b:Brand {id: 'sample01'})-[r]->(related)
# RETURN b, collect(related) as context;

# Get brand with all relationships visualized
# MATCH (b:Brand {id: 'sample01'})-[r]-(n)
# RETURN b, r, n;

# Find brands by color
# MATCH (b:Brand)-[:USES_COLOR]->(c:Color {hex: '#8B4513'})
# RETURN b.name, b.website;

# Get generation history for a brand
# MATCH (b:Brand {id: 'sample01'})-[:GENERATED]->(g:Generation)
# RETURN g ORDER BY g.created_at DESC LIMIT 10;

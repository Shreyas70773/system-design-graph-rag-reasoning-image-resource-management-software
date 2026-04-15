# System Design Diagrams

This document contains PlantUML diagrams for the Brand-Aligned Content Generation System. These can be rendered using:
- PlantUML extension in VS Code
- Online at https://www.plantuml.com/plantuml/uml/
- Draw.io import

---

## 1. Context Diagram (Level 0 DFD)

```plantuml
@startuml Context_Diagram
!theme plain
skinparam backgroundColor #FFFFFF
skinparam actorStyle awesome

title Brand Content Generation System - Context Diagram

actor "Marketing\nProfessional" as user #lightblue
rectangle "Brand Content\nGeneration System" as system #lightgreen {
}
database "Neo4j\nKnowledge Graph" as neo4j #orange
cloud "External APIs" as apis #lightyellow {
  rectangle "LLM APIs\n(OpenAI/Groq)" as llm
  rectangle "Image Gen\n(Gemini/Replicate)" as img
  rectangle "Search\n(Perplexity)" as search
}

user -right-> system : Website URL\nGeneration Prompt\nFeedback Ratings
system -right-> user : Brand DNA\nGenerated Images\nLinkedIn Posts\nGraph Visualization

system <-down-> neo4j : Graph Queries\nNode Updates\nPreference Storage

system <-down-> llm : Reasoning Requests\nPost Generation
system <-down-> img : Image Generation
system <-down-> search : News Retrieval

@enduml
```

---

## 2. Level 1 Data Flow Diagram

```plantuml
@startuml Level1_DFD
!theme plain
skinparam backgroundColor #FFFFFF

title Brand Content Generation - Level 1 DFD

actor "User" as user

rectangle "1.0\nBrand\nOnboarding" as P1 #lightblue
rectangle "2.0\nIndustry\nClassification" as P2 #lightblue
rectangle "3.0\nGraphRAG\nRetrieval" as P3 #lightblue
rectangle "4.0\nContent\nGeneration" as P4 #lightblue
rectangle "5.0\nLinkedIn\nModule" as P5 #lightblue
rectangle "6.0\nFeedback\nProcessing" as P6 #lightblue

database "D1: Brand DNA" as D1 #orange
database "D2: Generation History" as D2 #orange
database "D3: Preferences" as D3 #orange

user --> P1 : Website URL
P1 --> D1 : Brand Data
P1 --> P2 : Extracted Info

P2 --> D1 : Industry Tag

user --> P3 : Generation Request
D1 --> P3 : Brand Context
D3 --> P3 : Learned Prefs
P3 --> P4 : Compiled Context

P4 --> D2 : Store Result
P4 --> user : Generated Image

user --> P5 : Post Request
D1 --> P5 : Brand Voice
P5 --> user : LinkedIn Post

user --> P6 : Feedback
D2 --> P6 : Generation Ref
P6 --> D3 : New Preference

@enduml
```

---

## 3. Class Diagram

```plantuml
@startuml Class_Diagram
!theme plain
skinparam backgroundColor #FFFFFF
skinparam classAttributeIconSize 0

title Brand Content Generation - Class Diagram

package "Services" {
  class BrandDNAService {
    - neo4j: Neo4jClient
    - reasoner: LLMReasoner
    - generator: ImageGenerator
    --
    + get_brand_dna(brand_id: str): BrandDNA
    + generate_content(request: GenerationRequest): GenerationResult
    + process_feedback(feedback: FeedbackData): LearnedPreference
  }

  class LinkedInService {
    - perplexity: PerplexityClient
    - llm: LLMReasoner
    --
    + get_industry_news(industry: str): List<NewsItem>
    + generate_post(brand: BrandVoice, news: NewsItem): LinkedInPost
    + generate_batch(brand: BrandVoice, news: List<NewsItem>): List<LinkedInPost>
  }
}

package "Models" {
  class BrandDNA {
    + brand_id: str
    + brand_name: str
    + logo_url: str
    + industry: str
    + colors: List<Color>
    + styles: List<Style>
    + products: List<Product>
    + characters: List<Character>
    + preferences: List<Preference>
  }

  class GenerationRequest {
    + prompt: str
    + brand_id: str
    + condition: BrandCondition
    + headline: str
    + body_copy: str
  }

  class GenerationResult {
    + success: bool
    + image_url: str
    + compiled_prompt: str
    + model: str
    + provider: str
  }

  class LinkedInPost {
    + hook: str
    + body: str
    + cta: str
    + hashtags: List<str>
    + full_post: str
    + char_count: int
  }
}

package "Generation" {
  abstract class ImageGenerator {
    {abstract} + generate(request): GenerationResult
  }

  class GeminiGenerator {
    - api_key: str
    + generate(request): GenerationResult
  }

  class ReplicateGenerator {
    - api_token: str
    + generate(request): GenerationResult
  }

  class FallbackGenerator {
    - generators: List<ImageGenerator>
    + generate(request): GenerationResult
  }

  ImageGenerator <|-- GeminiGenerator
  ImageGenerator <|-- ReplicateGenerator
  ImageGenerator <|-- FallbackGenerator
  FallbackGenerator o-- ImageGenerator
}

package "Database" {
  class Neo4jClient {
    - driver: Driver
    --
    + create_brand(brand: BrandDNA): str
    + get_brand(id: str): BrandDNA
    + add_preference(brand_id: str, pref: Preference): void
    + query(cypher: str): List
  }
}

BrandDNAService --> Neo4jClient
BrandDNAService --> ImageGenerator
BrandDNAService --> BrandDNA
LinkedInService --> LinkedInPost

@enduml
```

---

## 4. Sequence Diagram - Content Generation Flow

```plantuml
@startuml Sequence_Generation
!theme plain
skinparam backgroundColor #FFFFFF

title Content Generation Flow

actor User
participant "Frontend\n(React)" as FE
participant "API\n(FastAPI)" as API
participant "GraphRAG\nService" as GR
database "Neo4j" as DB
participant "LLM\nReasoner" as LLM
participant "Image\nGenerator" as IMG

User -> FE : Enter prompt + select brand
FE -> API : POST /api/generate
activate API

API -> GR : retrieve_context(brand_id, prompt)
activate GR
GR -> DB : MATCH (b:Brand)-[:HAS_*]->(n)\nWHERE b.id = $brand_id
DB --> GR : Brand nodes + relationships
GR -> DB : MATCH (p:Preference)\nWHERE p.brand_id = $brand_id
DB --> GR : Learned preferences
GR --> API : Compiled brand context
deactivate GR

API -> LLM : plan_generation(prompt, context)
activate LLM
LLM --> API : Generation plan + compiled prompt
deactivate LLM

API -> IMG : generate(compiled_prompt, params)
activate IMG
IMG -> IMG : Try primary provider
alt Rate limited
  IMG -> IMG : Fallback to secondary
end
IMG --> API : image_url, metadata
deactivate IMG

API -> DB : Store generation record
API --> FE : GenerationResult
deactivate API

FE --> User : Display generated image

@enduml
```

---

## 5. Sequence Diagram - Feedback Loop

```plantuml
@startuml Sequence_Feedback
!theme plain
skinparam backgroundColor #FFFFFF

title Feedback Learning Flow

actor User
participant "Frontend" as FE
participant "API" as API
participant "LLM\nAnalyzer" as LLM
database "Neo4j" as DB

User -> FE : Rate image (1-5 stars)\n+ Select aspects\n+ Add comment
FE -> API : POST /api/feedback
activate API

API -> LLM : analyze_feedback(feedback_data)
activate LLM
note right of LLM
  Extract semantic meaning:
  - What was good/bad
  - Style preferences
  - Color preferences
  - Composition notes
end note
LLM --> API : FeedbackAnalysis
deactivate LLM

API -> DB : CREATE (p:LearnedPreference)\nSET p.trigger = "style"\np.action = "prefer warm tones"
API -> DB : CREATE (g:Generation)-[:RECEIVED]->(f:Feedback)

DB --> API : Confirmation
API --> FE : Success
deactivate API

FE --> User : "Thanks for feedback!"

note over DB
  Next generation will query:
  MATCH (p:Preference)
  WHERE p.brand_id = $id
  And apply learned preferences
end note

@enduml
```

---

## 6. Component Diagram

```plantuml
@startuml Component_Diagram
!theme plain
skinparam backgroundColor #FFFFFF

title System Component Architecture

package "Frontend Layer" {
  [React App] as react
  [Onboarding Page] as onboard
  [Generate Page] as generate
  [Results Page] as results
  [LinkedIn Page] as linkedin
  
  react --> onboard
  react --> generate
  react --> results
  react --> linkedin
}

package "API Layer" {
  [FastAPI Server] as api
  [Brands Router] as brands_r
  [Generation Router] as gen_r
  [Feedback Router] as feed_r
  [LinkedIn Router] as li_r
  
  api --> brands_r
  api --> gen_r
  api --> feed_r
  api --> li_r
}

package "Service Layer" {
  [Scraping Service] as scrape
  [GraphRAG Service] as graphrag
  [Generation Service] as genserv
  [LinkedIn Service] as liserv
  [Feedback Service] as feedserv
}

package "External APIs" {
  cloud "OpenAI GPT-4" as openai
  cloud "Gemini" as gemini
  cloud "Replicate" as replicate
  cloud "Perplexity" as perplexity
}

database "Neo4j Aura" as neo4j

react --> api : REST API
brands_r --> scrape
gen_r --> graphrag
gen_r --> genserv
feed_r --> feedserv
li_r --> liserv

scrape --> neo4j
graphrag --> neo4j
feedserv --> neo4j

graphrag --> openai
genserv --> gemini
genserv --> replicate
liserv --> perplexity
liserv --> openai

@enduml
```

---

## 7. Knowledge Graph Schema

```plantuml
@startuml Graph_Schema
!theme plain
skinparam backgroundColor #FFFFFF

title Neo4j Knowledge Graph Schema

object Brand #lightblue {
  id: UUID
  name: String
  website: URL
  industry: String
  tagline: String
}

object Color #orange {
  hex: String
  name: String
  role: String
}

object Style #lightgreen {
  name: String
  description: String
}

object Product #lightyellow {
  id: UUID
  name: String
  image_url: URL
}

object Character #pink {
  id: UUID
  name: String
  image_url: URL
}

object Generation #lightgray {
  id: UUID
  prompt: String
  result_url: URL
  timestamp: DateTime
}

object Preference #violet {
  id: UUID
  trigger: String
  action: String
  weight: Float
}

object Feedback #cyan {
  id: UUID
  rating: Int
  aspects: List
  comment: String
}

Brand "1" --> "*" Color : HAS_COLOR
Brand "1" --> "*" Style : HAS_STYLE
Brand "1" --> "*" Product : HAS_PRODUCT
Brand "1" --> "*" Character : HAS_CHARACTER
Brand "1" --> "*" Generation : GENERATED
Brand "1" --> "*" Preference : LEARNED
Generation "1" --> "0..1" Feedback : RECEIVED
Feedback "1" --> "0..1" Preference : CREATED

@enduml
```

---

## 8. Deployment Diagram

```plantuml
@startuml Deployment_Diagram
!theme plain
skinparam backgroundColor #FFFFFF

title Deployment Architecture

node "User Device" {
  [Web Browser]
}

node "Frontend Host\n(Vercel/Netlify)" {
  [React SPA]
}

node "Backend Host\n(Railway/Heroku)" {
  [FastAPI Server]
  [Uvicorn ASGI]
}

cloud "Neo4j Aura" {
  database "Graph Database"
}

cloud "API Providers" {
  [OpenAI API]
  [Google AI API]
  [Replicate API]
  [Perplexity API]
}

[Web Browser] --> [React SPA] : HTTPS
[React SPA] --> [FastAPI Server] : REST API
[FastAPI Server] --> [Graph Database] : Bolt Protocol
[FastAPI Server] --> [OpenAI API] : HTTPS
[FastAPI Server] --> [Google AI API] : HTTPS
[FastAPI Server] --> [Replicate API] : HTTPS
[FastAPI Server] --> [Perplexity API] : HTTPS

@enduml
```

---

## Rendering Instructions

### VS Code
1. Install "PlantUML" extension
2. Open this file
3. Press `Alt+D` to preview diagrams

### Online
1. Visit https://www.plantuml.com/plantuml/uml/
2. Copy diagram code (between ```plantuml and ```)
3. Paste and render

### Export
- PNG: Right-click rendered diagram → Export
- SVG: Use PlantUML CLI with `-tsvg` flag

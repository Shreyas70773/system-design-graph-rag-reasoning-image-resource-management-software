"""
Character Consistency Module
=============================
This module implements identity preservation for characters/faces across edits
and multiple generations. It ensures that when editing images with human faces,
the face remains consistent even with pose, angle, or style changes.

Key Features:
- Face detection and embedding extraction
- Identity comparison and verification
- Embedding storage in Neo4j
- Consistency guidance for generation prompts
- Reference image management

Part of Capstone Research: GraphRAG-Guided Compositional Image Generation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import json
import uuid
import base64
import io
import os
from datetime import datetime
import httpx

try:
    from PIL import Image
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not available, some character consistency features disabled")


@dataclass
class FaceRegion:
    """Detected face region in an image."""
    x: float  # Left edge (0-1)
    y: float  # Top edge (0-1)
    width: float
    height: float
    confidence: float
    landmarks: Optional[Dict[str, Tuple[float, float]]] = None  # eyes, nose, mouth positions
    
    def to_dict(self) -> Dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "landmarks": self.landmarks
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "FaceRegion":
        return cls(
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            confidence=data.get("confidence", 1.0),
            landmarks=data.get("landmarks")
        )
    
    def center(self) -> Tuple[float, float]:
        """Get center point of face region."""
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    def area(self) -> float:
        """Get area as percentage of image."""
        return self.width * self.height


@dataclass
class FaceEmbedding:
    """Face embedding for identity comparison."""
    id: str
    embedding: List[float]  # Vector representation of face
    source_image_url: str
    face_region: FaceRegion
    quality_score: float
    attributes: Dict[str, Any] = field(default_factory=dict)  # age_range, etc.
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "embedding": self.embedding,
            "source_image_url": self.source_image_url,
            "face_region": self.face_region.to_dict(),
            "quality_score": self.quality_score,
            "attributes": self.attributes,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "FaceEmbedding":
        return cls(
            id=data["id"],
            embedding=data["embedding"],
            source_image_url=data["source_image_url"],
            face_region=FaceRegion.from_dict(data["face_region"]),
            quality_score=data["quality_score"],
            attributes=data.get("attributes", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now()
        )


@dataclass
class Character:
    """A character identity that should be consistent across generations."""
    id: str
    name: str
    description: str
    reference_embeddings: List[FaceEmbedding]
    reference_images: List[str]  # URLs to reference images
    style_notes: str = ""  # Notes about how to render this character
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "reference_embeddings": [e.to_dict() for e in self.reference_embeddings],
            "reference_images": self.reference_images,
            "style_notes": self.style_notes,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Character":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            reference_embeddings=[FaceEmbedding.from_dict(e) for e in data.get("reference_embeddings", [])],
            reference_images=data.get("reference_images", []),
            style_notes=data.get("style_notes", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now()
        )
    
    def get_best_embedding(self) -> Optional[FaceEmbedding]:
        """Get the highest quality embedding for this character."""
        if not self.reference_embeddings:
            return None
        return max(self.reference_embeddings, key=lambda e: e.quality_score)
    
    def get_average_embedding(self) -> Optional[List[float]]:
        """Get average embedding across all references."""
        if not self.reference_embeddings:
            return None
        
        embeddings = [e.embedding for e in self.reference_embeddings]
        if not embeddings:
            return None
        
        # Average the embeddings
        avg = [sum(vals) / len(vals) for vals in zip(*embeddings)]
        return avg


@dataclass
class IdentityVerification:
    """Result of identity verification between two faces."""
    is_same_person: bool
    confidence: float  # 0-1
    similarity_score: float  # Raw cosine similarity
    face1_quality: float
    face2_quality: float
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "is_same_person": self.is_same_person,
            "confidence": self.confidence,
            "similarity_score": self.similarity_score,
            "face1_quality": self.face1_quality,
            "face2_quality": self.face2_quality,
            "details": self.details
        }


class CharacterConsistencyEngine:
    """
    Engine for maintaining character/face consistency across generations.
    
    This module addresses a key challenge in AI image generation:
    maintaining the same person's identity when:
    - Editing an existing image
    - Generating variations
    - Changing poses/angles
    - Creating multi-image campaigns
    
    Approach:
    1. Extract face embeddings from reference images
    2. Store embeddings in Neo4j linked to Character nodes
    3. When editing, extract embedding from source image
    4. Guide generation with identity-preserving prompts
    5. Verify consistency post-generation
    """
    
    # Similarity threshold for identity matching (cosine similarity)
    IDENTITY_THRESHOLD = 0.65
    HIGH_CONFIDENCE_THRESHOLD = 0.80
    
    def __init__(self, neo4j_client=None, use_api_detection: bool = True):
        """
        Initialize the character consistency engine.
        
        Args:
            neo4j_client: Neo4j client for storing embeddings
            use_api_detection: Whether to use external API for face detection
        """
        self.db = neo4j_client
        self.use_api_detection = use_api_detection
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        
    async def detect_faces(self, image_data: bytes) -> List[FaceRegion]:
        """
        Detect faces in an image.
        
        Args:
            image_data: Image bytes
            
        Returns:
            List of detected face regions
        """
        if not PIL_AVAILABLE:
            return []
        
        # Try API-based detection first
        if self.use_api_detection and self.hf_api_key:
            try:
                faces = await self._api_detect_faces(image_data)
                if faces:
                    return faces
            except Exception as e:
                print(f"API face detection failed: {e}")
        
        # Fallback to simple heuristic detection
        return self._simple_face_detection(image_data)
    
    async def _api_detect_faces(self, image_data: bytes) -> List[FaceRegion]:
        """Use HuggingFace API for face detection."""
        # Using a face detection model from HuggingFace
        api_url = "https://api-inference.huggingface.co/models/facebook/detr-resnet-50"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                api_url,
                headers={"Authorization": f"Bearer {self.hf_api_key}"},
                content=image_data
            )
            
            if response.status_code != 200:
                raise Exception(f"API error: {response.text}")
            
            results = response.json()
            faces = []
            
            # Parse detection results - look for person detections
            for detection in results:
                label = detection.get("label", "").lower()
                if "person" in label or "face" in label:
                    box = detection.get("box", {})
                    faces.append(FaceRegion(
                        x=box.get("xmin", 0) / 1000,  # Normalize
                        y=box.get("ymin", 0) / 1000,
                        width=(box.get("xmax", 100) - box.get("xmin", 0)) / 1000,
                        height=(box.get("ymax", 100) - box.get("ymin", 0)) / 1000,
                        confidence=detection.get("score", 0.5)
                    ))
            
            return faces
    
    def _simple_face_detection(self, image_data: bytes) -> List[FaceRegion]:
        """Simple heuristic-based face region estimation."""
        if not PIL_AVAILABLE:
            return []
        
        try:
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            
            # Simple heuristic: assume face in upper-center third of image
            # This is a fallback when proper detection isn't available
            return [FaceRegion(
                x=0.25,
                y=0.1,
                width=0.5,
                height=0.4,
                confidence=0.3,  # Low confidence for heuristic
                landmarks=None
            )]
        except Exception as e:
            print(f"Simple face detection failed: {e}")
            return []
    
    async def extract_embedding(
        self, 
        image_data: bytes,
        face_region: Optional[FaceRegion] = None
    ) -> Optional[FaceEmbedding]:
        """
        Extract face embedding from an image.
        
        Args:
            image_data: Image bytes
            face_region: Optional specific face region to extract from
            
        Returns:
            FaceEmbedding if face detected, None otherwise
        """
        # Detect faces if region not specified
        if face_region is None:
            faces = await self.detect_faces(image_data)
            if not faces:
                return None
            face_region = faces[0]  # Use first/largest face
        
        # Extract embedding using API or generate placeholder
        embedding = await self._get_face_embedding(image_data, face_region)
        
        if embedding is None:
            return None
        
        # Calculate quality score based on face region size and detection confidence
        quality = self._calculate_quality(face_region)
        
        return FaceEmbedding(
            id=f"emb_{uuid.uuid4().hex[:8]}",
            embedding=embedding,
            source_image_url="",  # Set by caller
            face_region=face_region,
            quality_score=quality,
            attributes={}
        )
    
    async def _get_face_embedding(
        self, 
        image_data: bytes, 
        face_region: FaceRegion
    ) -> Optional[List[float]]:
        """
        Get face embedding vector.
        
        Uses a combination of:
        1. Image feature extraction from face region
        2. Perceptual hashing for identity
        """
        if not PIL_AVAILABLE:
            return None
        
        try:
            # Open and crop to face region
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            
            # Convert relative coords to pixels
            left = int(face_region.x * width)
            top = int(face_region.y * height)
            right = int((face_region.x + face_region.width) * width)
            bottom = int((face_region.y + face_region.height) * height)
            
            face_crop = image.crop((left, top, right, bottom))
            
            # Resize to standard size for embedding
            face_crop = face_crop.resize((128, 128))
            
            # Convert to grayscale for simpler embedding
            face_gray = face_crop.convert('L')
            
            # Create embedding from pixel values + simple features
            embedding = self._create_embedding_from_image(face_gray)
            
            return embedding
            
        except Exception as e:
            print(f"Embedding extraction failed: {e}")
            return None
    
    def _create_embedding_from_image(self, image: Image.Image) -> List[float]:
        """
        Create a 512-dimensional embedding from a face image.
        
        This is a simplified embedding approach. In production, you would use
        a proper face recognition model like ArcFace or FaceNet.
        """
        import hashlib
        
        # Resize to multiple scales
        sizes = [8, 16, 32, 64]
        embedding = []
        
        for size in sizes:
            resized = image.resize((size, size))
            pixels = list(resized.getdata())
            
            # Normalize pixels to 0-1
            normalized = [p / 255.0 for p in pixels]
            embedding.extend(normalized)
        
        # Pad or truncate to 512 dimensions
        if len(embedding) > 512:
            embedding = embedding[:512]
        else:
            embedding.extend([0.0] * (512 - len(embedding)))
        
        # Add some hash-based features for uniqueness
        img_bytes = image.tobytes()
        hash_obj = hashlib.sha256(img_bytes)
        hash_vals = [int(hash_obj.hexdigest()[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
        
        # Replace last 16 dims with hash features
        embedding[-16:] = hash_vals
        
        return embedding
    
    def _calculate_quality(self, face_region: FaceRegion) -> float:
        """Calculate quality score for a face region."""
        # Factors:
        # 1. Detection confidence
        # 2. Face size (larger = better)
        # 3. Aspect ratio (closer to square = better)
        
        confidence_score = face_region.confidence
        
        # Size score (optimal around 0.15-0.3 of image area)
        area = face_region.area()
        if area < 0.05:
            size_score = area / 0.05 * 0.5
        elif area < 0.15:
            size_score = 0.5 + (area - 0.05) / 0.10 * 0.5
        elif area < 0.35:
            size_score = 1.0
        else:
            size_score = max(0.5, 1.0 - (area - 0.35) / 0.65 * 0.5)
        
        # Aspect ratio score
        aspect = face_region.width / face_region.height if face_region.height > 0 else 1
        optimal_aspect = 0.75  # Typical face aspect ratio
        aspect_score = 1.0 - min(1.0, abs(aspect - optimal_aspect) / optimal_aspect)
        
        # Weighted combination
        quality = (
            0.4 * confidence_score +
            0.35 * size_score +
            0.25 * aspect_score
        )
        
        return round(quality, 3)
    
    def compare_embeddings(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """
        Compare two face embeddings using cosine similarity.
        
        Returns:
            Similarity score 0-1 (higher = more similar)
        """
        if len(embedding1) != len(embedding2):
            # Pad shorter one
            max_len = max(len(embedding1), len(embedding2))
            embedding1 = embedding1 + [0.0] * (max_len - len(embedding1))
            embedding2 = embedding2 + [0.0] * (max_len - len(embedding2))
        
        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a * a for a in embedding1) ** 0.5
        norm2 = sum(b * b for b in embedding2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return max(0.0, min(1.0, similarity))
    
    def verify_identity(
        self,
        embedding1: FaceEmbedding,
        embedding2: FaceEmbedding
    ) -> IdentityVerification:
        """
        Verify if two face embeddings belong to the same person.
        
        Returns:
            IdentityVerification result with confidence
        """
        similarity = self.compare_embeddings(embedding1.embedding, embedding2.embedding)
        
        # Adjust threshold based on quality
        min_quality = min(embedding1.quality_score, embedding2.quality_score)
        adjusted_threshold = self.IDENTITY_THRESHOLD * (1 + 0.1 * (1 - min_quality))
        
        is_same = similarity >= adjusted_threshold
        
        # Calculate confidence
        if is_same:
            # How far above threshold
            confidence = min(1.0, 0.5 + (similarity - adjusted_threshold) / (1 - adjusted_threshold) * 0.5)
        else:
            # How far below threshold
            confidence = min(1.0, 0.5 + (adjusted_threshold - similarity) / adjusted_threshold * 0.5)
        
        return IdentityVerification(
            is_same_person=is_same,
            confidence=confidence,
            similarity_score=similarity,
            face1_quality=embedding1.quality_score,
            face2_quality=embedding2.quality_score,
            details={
                "threshold_used": adjusted_threshold,
                "quality_adjusted": min_quality < 0.7
            }
        )
    
    def verify_against_character(
        self,
        face_embedding: FaceEmbedding,
        character: Character
    ) -> IdentityVerification:
        """
        Verify if a face matches a character's identity.
        
        Uses the character's average embedding for comparison.
        """
        avg_embedding = character.get_average_embedding()
        if avg_embedding is None:
            return IdentityVerification(
                is_same_person=False,
                confidence=0.0,
                similarity_score=0.0,
                face1_quality=face_embedding.quality_score,
                face2_quality=0.0,
                details={"error": "No reference embeddings for character"}
            )
        
        # Create a temporary embedding for comparison
        ref_embedding = FaceEmbedding(
            id="avg_ref",
            embedding=avg_embedding,
            source_image_url="",
            face_region=FaceRegion(0, 0, 1, 1, 1.0),
            quality_score=0.8  # Assume good quality for averaged embedding
        )
        
        return self.verify_identity(face_embedding, ref_embedding)
    
    async def create_character(
        self,
        name: str,
        description: str,
        reference_images: List[bytes],
        brand_id: Optional[str] = None
    ) -> Character:
        """
        Create a new character from reference images.
        
        Args:
            name: Character name/identifier
            description: Description of the character
            reference_images: List of image bytes for references
            brand_id: Optional brand to associate character with
            
        Returns:
            Created Character object
        """
        character_id = f"char_{uuid.uuid4().hex[:8]}"
        embeddings = []
        image_urls = []
        
        for i, img_data in enumerate(reference_images):
            embedding = await self.extract_embedding(img_data)
            if embedding:
                embedding.source_image_url = f"ref_{character_id}_{i}"
                embeddings.append(embedding)
                image_urls.append(embedding.source_image_url)
        
        character = Character(
            id=character_id,
            name=name,
            description=description,
            reference_embeddings=embeddings,
            reference_images=image_urls
        )
        
        # Store in Neo4j if client available
        if self.db and brand_id:
            await self._store_character(character, brand_id)
        
        return character
    
    async def _store_character(self, character: Character, brand_id: str):
        """Store character in Neo4j."""
        query = """
        MATCH (b:Brand {id: $brand_id})
        CREATE (c:Character {
            id: $char_id,
            name: $name,
            description: $description,
            style_notes: $style_notes,
            reference_images: $reference_images,
            created_at: datetime()
        })
        CREATE (b)-[:HAS_CHARACTER]->(c)
        """
        
        await self.db.execute_query(query, {
            "brand_id": brand_id,
            "char_id": character.id,
            "name": character.name,
            "description": character.description,
            "style_notes": character.style_notes,
            "reference_images": json.dumps(character.reference_images)
        })
        
        # Store embeddings
        for emb in character.reference_embeddings:
            await self._store_embedding(emb, character.id)
    
    async def _store_embedding(self, embedding: FaceEmbedding, character_id: str):
        """Store face embedding in Neo4j."""
        query = """
        MATCH (c:Character {id: $char_id})
        CREATE (e:FaceEmbedding {
            id: $emb_id,
            embedding_vector: $embedding,
            source_image_url: $source_url,
            face_region: $face_region,
            quality_score: $quality,
            attributes: $attributes,
            created_at: datetime()
        })
        CREATE (c)-[:HAS_EMBEDDING]->(e)
        """
        
        await self.db.execute_query(query, {
            "char_id": character_id,
            "emb_id": embedding.id,
            "embedding": json.dumps(embedding.embedding),
            "source_url": embedding.source_image_url,
            "face_region": json.dumps(embedding.face_region.to_dict()),
            "quality": embedding.quality_score,
            "attributes": json.dumps(embedding.attributes)
        })
    
    def generate_consistency_prompt(
        self,
        character: Character,
        target_pose: Optional[str] = None,
        target_expression: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate prompt components for maintaining character consistency.
        
        Returns:
            Dict with 'positive' and 'negative' prompt additions
        """
        positive_additions = []
        negative_additions = []
        
        # Add character description
        positive_additions.append(f"same person as reference, {character.description}")
        
        # Add style notes if available
        if character.style_notes:
            positive_additions.append(character.style_notes)
        
        # Identity preservation keywords
        positive_additions.extend([
            "consistent facial features",
            "same face structure",
            "identical facial proportions",
            "recognizable identity"
        ])
        
        # Avoid identity changes
        negative_additions.extend([
            "different person",
            "changed face",
            "altered identity",
            "morphed features",
            "face swap"
        ])
        
        # Add pose/expression guidance if specified
        if target_pose:
            positive_additions.append(f"pose: {target_pose}")
        if target_expression:
            positive_additions.append(f"expression: {target_expression}")
        
        return {
            "positive": ", ".join(positive_additions),
            "negative": ", ".join(negative_additions)
        }
    
    async def get_character_for_brand(self, brand_id: str) -> List[Character]:
        """Retrieve all characters associated with a brand."""
        if not self.db:
            return []
        
        query = """
        MATCH (b:Brand {id: $brand_id})-[:HAS_CHARACTER]->(c:Character)
        OPTIONAL MATCH (c)-[:HAS_EMBEDDING]->(e:FaceEmbedding)
        RETURN c.id as id, c.name as name, c.description as description,
               c.style_notes as style_notes, c.reference_images as reference_images,
               collect(e) as embeddings
        """
        
        characters = []
        try:
            results = await self.db.execute_query(query, {"brand_id": brand_id})
            for record in results:
                # Parse embeddings
                embeddings = []
                for emb_data in record.get("embeddings", []):
                    if emb_data:
                        embeddings.append(FaceEmbedding(
                            id=emb_data.get("id", ""),
                            embedding=json.loads(emb_data.get("embedding_vector", "[]")),
                            source_image_url=emb_data.get("source_image_url", ""),
                            face_region=FaceRegion.from_dict(json.loads(emb_data.get("face_region", "{}"))),
                            quality_score=emb_data.get("quality_score", 0.5)
                        ))
                
                characters.append(Character(
                    id=record["id"],
                    name=record["name"],
                    description=record.get("description", ""),
                    reference_embeddings=embeddings,
                    reference_images=json.loads(record.get("reference_images", "[]")),
                    style_notes=record.get("style_notes", "")
                ))
        except Exception as e:
            print(f"Error fetching characters: {e}")
        
        return characters


# Utility functions
def image_to_bytes(image: Image.Image, format: str = "PNG") -> bytes:
    """Convert PIL Image to bytes."""
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return buffer.getvalue()


def bytes_to_image(data: bytes) -> Image.Image:
    """Convert bytes to PIL Image."""
    return Image.open(io.BytesIO(data))

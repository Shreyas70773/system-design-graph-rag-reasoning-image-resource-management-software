# Capstone Local Models Setup

## Goal

This project now exposes a real capstone editing backend built around:

- SAM 2 point-prompt segmentation
- LaMa / Big-LaMa object removal inpainting
- Persistent GraphRAG scene state in `/api/v3/...`

## Python Dependencies

```bash
pip install -r backend/requirements.txt -r backend/requirements_capstone_v3.txt
pip install git+https://github.com/facebookresearch/sam2.git
```

Or run the all-in-one bootstrap script on Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_capstone_models.ps1
```

## LaMa Repo

Clone LaMa locally so the backend can call its prediction script:

```bash
git clone https://github.com/advimman/lama.git external/lama
cd external/lama
pip install -r requirements.txt
cd ../..
```

## Required Environment Variables

Set these in `backend/.env`:

```env
CAPSTONE_SAM2_CHECKPOINT=checkpoints/sam2.1_hiera_large.pt
CAPSTONE_SAM2_CONFIG=configs/sam2.1/sam2.1_hiera_l.yaml
CAPSTONE_LAMA_REPO_PATH=external/lama
CAPSTONE_LAMA_MODEL_PATH=models/big-lama
CAPSTONE_LAMA_PYTHON=python
CAPSTONE_DEVICE=auto
CAPSTONE_ALLOW_MOCK_FALLBACKS=false
```

## Verify Model Readiness

```bash
cd backend
python scripts/verify_capstone_models.py
```

The JSON output should show:

- `sam2.ready: true`
- `lama.ready: true`

## Core Capstone Endpoints

- `GET /api/v3/capabilities`
- `POST /api/v3/scenes/upload`
- `POST /api/v3/scenes/{scene_id}/segment-click`
- `POST /api/v3/scenes/{scene_id}/remove-object`
- `GET /api/v3/scenes/{scene_id}/inpaint-context/{object_id}`

## Expected Flow

1. Upload an image with `POST /api/v3/scenes/upload`
2. Click-segment an object with `POST /api/v3/scenes/{scene_id}/segment-click`
3. Remove it with `POST /api/v3/scenes/{scene_id}/remove-object`
4. The backend writes the new canvas image, removes the object from the scene graph, and records an `EditEvent`

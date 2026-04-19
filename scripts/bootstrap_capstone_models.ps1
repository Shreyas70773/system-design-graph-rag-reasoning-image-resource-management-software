$ErrorActionPreference = "Stop"

Write-Host "[1/5] Installing capstone Python dependencies..."
python -m pip install -r backend/requirements.txt -r backend/requirements_capstone_v3.txt

Write-Host "[2/5] Installing SAM2 package..."
python -m pip install git+https://github.com/facebookresearch/sam2.git

if (-not (Test-Path "external")) {
    New-Item -ItemType Directory -Path "external" | Out-Null
}

if (-not (Test-Path "external/lama")) {
    Write-Host "[3/5] Cloning LaMa repo..."
    git clone https://github.com/advimman/lama.git external/lama
} else {
    Write-Host "[3/5] LaMa repo already present, skipping clone."
}

Write-Host "[4/5] Installing LaMa dependencies..."
python -m pip install -r external/lama/requirements.txt

Write-Host "[5/5] Downloading SAM2 + Big-LaMa weights..."
python backend/scripts/download_capstone_weights.py

Write-Host ""
Write-Host "Bootstrap complete. Next:"
Write-Host "  1. Set backend/.env CAPSTONE_* variables"
Write-Host "  2. Run: python backend/scripts/verify_capstone_models.py"

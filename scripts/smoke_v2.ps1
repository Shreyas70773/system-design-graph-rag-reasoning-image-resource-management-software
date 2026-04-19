# End-to-end smoke test for V2 pipeline, in mock mode.
# Run while `uvicorn app.main:app --port 8765` is up with V2_MOCK_MODE=true.

$base = "http://127.0.0.1:8765"

function Post { param($path, $body)
    Invoke-RestMethod -Method Post -Uri "$base$path" `
        -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 10)
}
function Get-Json { param($path)
    Invoke-RestMethod -Method Get -Uri "$base$path"
}

Write-Host "== 1. health" -ForegroundColor Cyan
Get-Json "/api/v2/health"

Write-Host "`n== 2. create brand" -ForegroundColor Cyan
$brand = Post "/api/v2/brands" @{
    name = "SmokeCo"
    primary_hex = @("#ff3344", "#102030")
    voice_keywords = @("bold", "confident")
    description = "Smoke test brand"
}
$brandId = $brand.brand_id
Write-Host "brand_id=$brandId"

Write-Host "`n== 3. ingest asset (sync)" -ForegroundColor Cyan
# Generate a 512x512 test PNG in memory so mock steps have realistic input.
$tmpPng = Join-Path $env:TEMP "smoke_v2_input.png"
python -c @"
from PIL import Image, ImageDraw
img = Image.new('RGB', (512, 512), (200, 64, 64))
d = ImageDraw.Draw(img)
d.ellipse([96, 96, 416, 416], fill=(240, 230, 210))
d.rectangle([200, 220, 312, 312], fill=(30, 40, 80))
img.save(r'$tmpPng', 'PNG')
"@
$bytes = [System.IO.File]::ReadAllBytes($tmpPng)
$b64 = [Convert]::ToBase64String($bytes)
$dataUrl = "data:image/png;base64,$b64"
$asset = Post "/api/v2/assets" @{
    brand_id = $brandId
    asset_type = "product"
    source_image_url = $dataUrl
    sync = $true
}
Write-Host ($asset | ConvertTo-Json -Depth 6)
$assetId = $asset.asset_id

Write-Host "`n== 4. approve asset" -ForegroundColor Cyan
Post "/api/v2/assets/$assetId/approve" @{}

Write-Host "`n== 5. create + render scene" -ForegroundColor Cyan
$scene = Post "/api/v2/scenes" @{
    brand_id = $brandId
    intent_text = "Hero shot of the product on a clean studio backdrop with the tagline 'Bold.'"
    deployment_context = "digital"
    sync = $true
    cameras = @(
        @{ shot_type = "hero"; aspect_ratio = "1:1" },
        @{ shot_type = "detail"; aspect_ratio = "1:1" },
        @{ shot_type = "wide"; aspect_ratio = "16:9" }
    )
}
Write-Host "scene_id=$($scene.scene_id)  renders=$($scene.renders.Count)"
foreach ($r in $scene.renders) { Write-Host "  - $($r.camera_id) -> $($r.image_url)" }

Write-Host "`n== 6. retrieval preview" -ForegroundColor Cyan
Get-Json "/api/v2/brands/$brandId/retrieval-preview"

Write-Host "`nSMOKE OK" -ForegroundColor Green

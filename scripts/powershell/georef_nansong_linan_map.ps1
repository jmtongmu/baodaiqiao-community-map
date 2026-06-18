param(
    [string]$Python = "C:\Python313\python.exe"
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\.."))
Set-Location $RepoRoot

$ControlPoints = Join-Path $RepoRoot "data\maps\control_points\nansong_linan_map_to_osm_control_points.csv"
$ImageControlGeoJson = Join-Path $RepoRoot "data\maps\control_points\nansong_linan_map_image_control_points.geojson"
$OsmControlGeoJson = Join-Path $RepoRoot "data\maps\control_points\nansong_linan_map_osm_control_points.geojson"
$Transform = Join-Path $RepoRoot "data\maps\transforms\nansong_linan_map_pixel_to_osm.json"
$Image = Join-Path $RepoRoot "assets\maps\nansong_linan_map.jpg"
$GeorefImage = Join-Path $RepoRoot "qgis\georef\nansong_linan_map_osm_affine.jpg"
$Candidates = Join-Path $RepoRoot "data\ocr\nansong_linan_map_rapidocr_text_candidates.json"
$Boxes = Join-Path $RepoRoot "data\ocr\osm_space\nansong_linan_map_rapidocr_osm_boxes.geojson"
$Points = Join-Path $RepoRoot "data\ocr\osm_space\nansong_linan_map_rapidocr_osm_points.geojson"

if (!(Test-Path -LiteralPath $Python)) {
    throw "Python not found: $Python"
}
if (!(Test-Path -LiteralPath $ControlPoints)) {
    throw "Control point CSV not found: $ControlPoints"
}

if ((Test-Path -LiteralPath $ImageControlGeoJson) -and (Test-Path -LiteralPath $OsmControlGeoJson)) {
    Write-Host "Syncing editable QGIS control-point GeoJSON back to CSV..."
    & $Python ".\scripts\tools\control_points_from_geojson.py" `
        --control-points $ControlPoints `
        --image-input $ImageControlGeoJson `
        --osm-input $OsmControlGeoJson `
        --output $ControlPoints
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$Rows = Import-Csv -LiteralPath $ControlPoints
$EnabledRows = @($Rows | Where-Object {
    $Value = [string]$_.enabled
    $Value.Trim().ToLowerInvariant() -in @("1", "true", "yes", "y", "enabled")
})

if ($EnabledRows.Count -lt 3) {
    Write-Host "Enabled control points: $($EnabledRows.Count)"
    Write-Host "Edit this CSV and set enabled=true for at least 3 verified control points:"
    Write-Host $ControlPoints
    Write-Host "For a stable georeference, use 6-10 verified anchors spread across the map."
    exit 2
}

Write-Host "Repo root: $RepoRoot"
Write-Host "Enabled control points: $($EnabledRows.Count)"

& $Python ".\scripts\tools\fit_pixel_to_map_transform.py" `
    --map-id nansong_linan_map `
    --control-points $ControlPoints `
    --output $Transform `
    --image $Image `
    --georef-image-output $GeorefImage

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$Payload = Get-Content -LiteralPath $Transform -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $Payload.accuracy.accepted) {
    Write-Host "Transform was rejected."
    Write-Host "RMSE m: $($Payload.accuracy.rmse_m)"
    Write-Host "Max error m: $($Payload.accuracy.max_error_m)"
    Write-Host "Fix/disable bad control points before projecting OCR to OSM space."
    exit 3
}

& $Python ".\scripts\tools\project_ocr_to_osm_geojson.py" `
    --candidates $Candidates `
    --transform $Transform `
    --polygon-output $Boxes `
    --point-output $Points

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Done. Load in QGIS with:"
Write-Host "scripts\pyqgis\load_nansong_linan_map_osm_registered_ocr.py"

param(
    [string]$Python = "C:\Python313\python.exe"
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\.."))
Set-Location $RepoRoot

$ControlPoints = Join-Path $RepoRoot "data\maps\control_points\nansong_linan_map_to_osm_control_points.csv"
$ImageGeoJson = Join-Path $RepoRoot "data\maps\control_points\nansong_linan_map_image_control_points.geojson"
$OsmGeoJson = Join-Path $RepoRoot "data\maps\control_points\nansong_linan_map_osm_control_points.geojson"

& $Python ".\scripts\tools\control_points_from_geojson.py" `
    --control-points $ControlPoints `
    --image-input $ImageGeoJson `
    --osm-input $OsmGeoJson `
    --output $ControlPoints

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Synced edited QGIS control points back to:"
Write-Host $ControlPoints

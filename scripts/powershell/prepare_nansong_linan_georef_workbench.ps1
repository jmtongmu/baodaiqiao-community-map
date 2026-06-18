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

& $Python ".\scripts\tools\control_points_to_geojson.py" `
    --control-points $ControlPoints `
    --image-output $ImageGeoJson `
    --osm-output $OsmGeoJson

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Generated editable control-point layers."
Write-Host "Load in QGIS with:"
Write-Host "scripts\pyqgis\load_nansong_linan_georef_workbench.py"

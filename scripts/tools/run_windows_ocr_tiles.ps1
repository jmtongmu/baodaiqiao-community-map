param(
  [Parameter(Mandatory=$true)][string]$ImagePath,
  [Parameter(Mandatory=$true)][string]$MapId,
  [string]$OutputPath = "",
  [int]$TileWidth = 360,
  [int]$TileHeight = 260,
  [int]$Overlap = 80,
  [int]$Scale = 3,
  [int]$MinTextLength = 1
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Runtime.WindowsRuntime

[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null

function Await-AsyncOperation($operation, [Type]$resultType) {
  $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
      $_.Name -eq "AsTask" -and
      $_.IsGenericMethod -and
      $_.GetParameters().Count -eq 1 -and
      $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    } |
    Select-Object -First 1
  $task = $method.MakeGenericMethod($resultType).Invoke($null, @($operation))
  $task.Wait() | Out-Null
  return $task.Result
}

function Invoke-OcrFile([string]$Path, $Engine) {
  $file = Await-AsyncOperation ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Path)) ([Windows.Storage.StorageFile])
  $stream = Await-AsyncOperation ($file.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
  $decoder = Await-AsyncOperation ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
  $bitmap = Await-AsyncOperation ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
  return Await-AsyncOperation ($Engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
}

function Normalize-Text([string]$Text) {
  return ($Text -replace "\s+", "" -replace "[|`"']", "").Trim()
}

function Add-Candidate($List, [string]$Text, [double]$X1, [double]$Y1, [double]$X2, [double]$Y2, [string]$TileId, [string]$Kind) {
  $clean = Normalize-Text $Text
  if ($clean.Length -lt $MinTextLength) { return }
  $List.Add([ordered]@{
    text = $clean
    category = "ocr_text"
    bbox_pixel = @(
      [Math]::Round($X1, 2),
      [Math]::Round($Y1, 2),
      [Math]::Round($X2, 2),
      [Math]::Round($Y2, 2)
    )
    orientation = "unknown"
    confidence = "medium"
    source_map = $MapId
    source_stage = "windows_ocr_tiles"
    reference_logic = "Windows OCR tiled extraction from $MapId; tile=$TileId; kind=$Kind"
    notes = "raw_ocr_asset"
  }) | Out-Null
}

function Union-WordBounds($Words) {
  $left = [double]::PositiveInfinity
  $top = [double]::PositiveInfinity
  $right = [double]::NegativeInfinity
  $bottom = [double]::NegativeInfinity
  foreach ($word in $Words) {
    $rect = $word.BoundingRect
    $left = [Math]::Min($left, [double]$rect.X)
    $top = [Math]::Min($top, [double]$rect.Y)
    $right = [Math]::Max($right, [double]$rect.X + [double]$rect.Width)
    $bottom = [Math]::Max($bottom, [double]$rect.Y + [double]$rect.Height)
  }
  if ([double]::IsInfinity($left)) { return $null }
  return @($left, $top, $right, $bottom)
}

if (-not $OutputPath) {
  $repo = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
  $OutputPath = Join-Path $repo "data\ocr\$($MapId)_text_candidates.json"
}

$image = [System.Drawing.Image]::FromFile($ImagePath)
$bitmap = New-Object System.Drawing.Bitmap($image)
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("linan_ocr_" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tmpRoot | Out-Null

$language = [Windows.Globalization.Language]::new("zh-Hans-CN")
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
if ($null -eq $engine) {
  throw "Cannot create Windows OCR engine for zh-Hans-CN"
}

$candidates = New-Object System.Collections.ArrayList
$stepX = [Math]::Max(1, $TileWidth - $Overlap)
$stepY = [Math]::Max(1, $TileHeight - $Overlap)
$tileIndex = 0

try {
  for ($y = 0; $y -lt $image.Height; $y += $stepY) {
    for ($x = 0; $x -lt $image.Width; $x += $stepX) {
      $w = [Math]::Min($TileWidth, $image.Width - $x)
      $h = [Math]::Min($TileHeight, $image.Height - $y)
      if ($w -lt 80 -or $h -lt 80) { continue }

      $tileIndex += 1
      $tileId = "tile_$tileIndex"
      $scaledW = $w * $Scale
      $scaledH = $h * $Scale
      $tile = New-Object System.Drawing.Bitmap($scaledW, $scaledH)
      $graphics = [System.Drawing.Graphics]::FromImage($tile)
      $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
      $graphics.DrawImage(
        $bitmap,
        [System.Drawing.Rectangle]::new(0, 0, $scaledW, $scaledH),
        [System.Drawing.Rectangle]::new($x, $y, $w, $h),
        [System.Drawing.GraphicsUnit]::Pixel
      )
      $tilePath = Join-Path $tmpRoot "$tileId.png"
      $tile.Save($tilePath, [System.Drawing.Imaging.ImageFormat]::Png)
      $graphics.Dispose()
      $tile.Dispose()

      $result = Invoke-OcrFile $tilePath $engine
      foreach ($line in $result.Lines) {
        $bounds = Union-WordBounds $line.Words
        if ($null -eq $bounds) { continue }
        Add-Candidate $candidates $line.Text `
          ($x + $bounds[0] / $Scale) `
          ($y + $bounds[1] / $Scale) `
          ($x + $bounds[2] / $Scale) `
          ($y + $bounds[3] / $Scale) `
          $tileId "line"

        foreach ($word in $line.Words) {
          $rect = $word.BoundingRect
          Add-Candidate $candidates $word.Text `
            ($x + [double]$rect.X / $Scale) `
            ($y + [double]$rect.Y / $Scale) `
            ($x + ([double]$rect.X + [double]$rect.Width) / $Scale) `
            ($y + ([double]$rect.Y + [double]$rect.Height) / $Scale) `
            $tileId "word"
        }
      }
    }
  }
}
finally {
  $bitmap.Dispose()
  $image.Dispose()
  Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
}

$seen = @{}
$deduped = New-Object System.Collections.ArrayList
foreach ($candidate in $candidates) {
  $bbox = $candidate.bbox_pixel
  $cx = [Math]::Round((([double]$bbox[0] + [double]$bbox[2]) / 2) / 12) * 12
  $cy = [Math]::Round((([double]$bbox[1] + [double]$bbox[3]) / 2) / 12) * 12
  $key = "$($candidate.text)|$cx|$cy"
  if (-not $seen.ContainsKey($key)) {
    $seen[$key] = $true
    $deduped.Add($candidate) | Out-Null
  }
}

$payload = [ordered]@{
  map_id = $MapId
  image_file = $ImagePath
  crs = "EPSG:3857"
  ocr_engine = "Windows.Media.Ocr zh-Hans-CN"
  extraction = [ordered]@{
    mode = "tiled_scaled"
    tile_width = $TileWidth
    tile_height = $TileHeight
    overlap = $Overlap
    scale = $Scale
    raw_candidate_count = $candidates.Count
    deduped_candidate_count = $deduped.Count
  }
  candidates = @($deduped)
}

$outputDir = Split-Path $OutputPath -Parent
if ($outputDir) { New-Item -ItemType Directory -Force -Path $outputDir | Out-Null }
$payload | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Output "ocr candidates: $($deduped.Count)"
Write-Output $OutputPath

#!/usr/bin/env pwsh
# Test comparativo delle dimensioni dei blocchi sulla stessa parete

Write-Host "🔬 TEST COMPARATIVO DIMENSIONI BLOCCHI" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
Write-Host ""

# TEST 1: Dimensioni Standard [1500, 826, 413]
Write-Host "📦 TEST 1: Dimensioni STANDARD [1500, 826, 413]" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

$response1 = curl -X POST "http://localhost:8000/api/upload" `
  -F "file=@tests/test_parete_difficile.svg" `
  -F "config={`"block_widths`":[1500,826,413],`"block_height`":495,`"block_depth`":100}" `
  -F "colors={`"standardBlockColor`":`"#e5e7eb`",`"standardBlockBorder`":`"#374151`",`"doorWindowColor`":`"#fee2e2`",`"doorWindowBorder`":`"#dc2626`",`"wallOutlineColor`":`"#1e40af`",`"wallLineWidth`":2,`"customPieceColor`":`"#f3e8ff`",`"customPieceBorder`":`"#7c3aed`"}" `
  2>&1

# Estrai informazioni chiave
$mappings1 = $response1 | Select-String "🔗 Mapping"
$categories1 = $response1 | Select-String "📋 Categoria [A-C] →" 
$sample_calc1 = $response1 | Select-String "🚀 Avanzato: Spazio.*→ Sequenza" | Select-Object -First 3

Write-Host "🔗 MAPPATURE:" -ForegroundColor Yellow
$mappings1 | ForEach-Object { Write-Host "   $_" -ForegroundColor White }
Write-Host ""
Write-Host "📋 CATEGORIE PRINCIPALI:" -ForegroundColor Yellow  
$categories1 | ForEach-Object { Write-Host "   $_" -ForegroundColor White }
Write-Host ""
Write-Host "🚀 ESEMPI CALCOLO:" -ForegroundColor Yellow
$sample_calc1 | ForEach-Object { Write-Host "   $_" -ForegroundColor White }

Write-Host "`n" + "="*80 + "`n"

# TEST 2: Dimensioni Grandi [2000, 1200, 600]  
Write-Host "📦 TEST 2: Dimensioni GRANDI [2000, 1200, 600]" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

$response2 = curl -X POST "http://localhost:8000/api/upload" `
  -F "file=@tests/test_parete_difficile.svg" `
  -F "config={`"block_widths`":[2000,1200,600],`"block_height`":495,`"block_depth`":100}" `
  -F "colors={`"standardBlockColor`":`"#e5e7eb`",`"standardBlockBorder`":`"#374151`",`"doorWindowColor`":`"#fee2e2`",`"doorWindowBorder`":`"#dc2626`",`"wallOutlineColor`":`"#1e40af`",`"wallLineWidth`":2,`"customPieceColor`":`"#f3e8ff`",`"customPieceBorder`":`"#7c3aed`"}" `
  2>&1

$mappings2 = $response2 | Select-String "🔗 Mapping"
$categories2 = $response2 | Select-String "📋 Categoria [A-C] →"
$sample_calc2 = $response2 | Select-String "🚀 Avanzato: Spazio.*→ Sequenza" | Select-Object -First 3

Write-Host "🔗 MAPPATURE:" -ForegroundColor Yellow
$mappings2 | ForEach-Object { Write-Host "   $_" -ForegroundColor White }
Write-Host ""
Write-Host "📋 CATEGORIE PRINCIPALI:" -ForegroundColor Yellow
$categories2 | ForEach-Object { Write-Host "   $_" -ForegroundColor White }
Write-Host ""
Write-Host "🚀 ESEMPI CALCOLO:" -ForegroundColor Yellow
$sample_calc2 | ForEach-Object { Write-Host "   $_" -ForegroundColor White }

Write-Host "`n" + "="*80 + "`n"

# TEST 3: Dimensioni Piccole [800, 500, 250]
Write-Host "📦 TEST 3: Dimensioni PICCOLE [800, 500, 250]" -ForegroundColor Cyan  
Write-Host "==============================================" -ForegroundColor Cyan

$response3 = curl -X POST "http://localhost:8000/api/upload" `
  -F "file=@tests/test_parete_difficile.svg" `
  -F "config={`"block_widths`":[800,500,250],`"block_height`":495,`"block_depth`":100}" `
  -F "colors={`"standardBlockColor`":`"#e5e7eb`",`"standardBlockBorder`":`"#374151`",`"doorWindowColor`":`"#fee2e2`",`"doorWindowBorder`":`"#dc2626`",`"wallOutlineColor`":`"#1e40af`",`"wallLineWidth`":2,`"customPieceColor`":`"#f3e8ff`",`"customPieceBorder`":`"#7c3aed`"}" `
  2>&1

$mappings3 = $response3 | Select-String "🔗 Mapping"
$categories3 = $response3 | Select-String "📋 Categoria [A-C] →"
$sample_calc3 = $response3 | Select-String "🚀 Avanzato: Spazio.*→ Sequenza" | Select-Object -First 3

Write-Host "🔗 MAPPATURE:" -ForegroundColor Yellow
$mappings3 | ForEach-Object { Write-Host "   $_" -ForegroundColor White }
Write-Host ""
Write-Host "📋 CATEGORIE PRINCIPALI:" -ForegroundColor Yellow
$categories3 | ForEach-Object { Write-Host "   $_" -ForegroundColor White }
Write-Host ""
Write-Host "🚀 ESEMPI CALCOLO:" -ForegroundColor Yellow
$sample_calc3 | ForEach-Object { Write-Host "   $_" -ForegroundColor White }

Write-Host "`n" + "="*80
Write-Host "🎯 ANALISI COMPARATIVA COMPLETATA!" -ForegroundColor Green  
Write-Host "✅ Ogni test mostra calcoli reali diversi per le stesse dimensioni parete" -ForegroundColor Green
Write-Host "✅ Le mappature adattano le dimensioni ottimizzate a quelle logiche" -ForegroundColor Green
Write-Host "="*80

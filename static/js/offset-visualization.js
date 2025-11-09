// ================================================================
// WALL OFFSET VISUALIZATION SYSTEM
// ================================================================

/**
 * Visualizza doppio poligono (originale + offset) nello Step 2
 * @param {Array} originalCoords - Coordinate poligono originale [[x,y], ...]
 * @param {Array} offsetCoords - Coordinate poligono con offset [[x,y], ...]
 * @param {number} offsetMm - Distanza offset applicata in mm
 * @param {string} containerId - ID del container SVG
 */
function renderOffsetVisualization(originalCoords, offsetCoords, offsetMm, containerId = 'wallPreview') {
    console.log(`📐 Rendering offset visualization: ${offsetMm}mm`);
    
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`❌ Container ${containerId} not found`);
        return;
    }
    
    // Calcola bounds combinati per centrare la vista
    const allCoords = [...originalCoords, ...offsetCoords];
    const xs = allCoords.map(c => c[0]);
    const ys = allCoords.map(c => c[1]);
    
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    
    const width = maxX - minX;
    const height = maxY - minY;
    const padding = Math.max(width, height) * 0.1; // 10% padding
    
    // ViewBox per SVG
    const viewBox = `${minX - padding} ${minY - padding} ${width + 2*padding} ${height + 2*padding}`;
    
    // Crea SVG
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', viewBox);
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    svg.setAttribute('style', 'max-height: 500px; border: 1px solid #E5E7EB; border-radius: 8px; background: #F9FAFB;');
    
    // Layer 1: Poligono ORIGINALE (blu tratteggiato)
    const originalPath = createPolygonPath(originalCoords, {
        fill: 'rgba(59, 130, 246, 0.1)',
        stroke: '#3B82F6',
        strokeWidth: 2,
        strokeDasharray: '10,5',
        strokeLinecap: 'round'
    });
    svg.appendChild(originalPath);
    
    // Layer 2: Poligono OFFSET (verde pieno)
    const offsetPath = createPolygonPath(offsetCoords, {
        fill: 'rgba(34, 197, 94, 0.2)',
        stroke: '#22C55E',
        strokeWidth: 3,
        strokeLinecap: 'round'
    });
    svg.appendChild(offsetPath);
    
    // Calcola aree per statistiche
    const originalArea = calculatePolygonArea(originalCoords);
    const offsetArea = calculatePolygonArea(offsetCoords);
    const areaReduction = ((originalArea - offsetArea) / originalArea * 100).toFixed(2);
    
    // Replace container content
    container.innerHTML = '';
    container.appendChild(svg);
    
    // Aggiungi legenda sotto l'immagine
    const legend = createOffsetLegend(originalArea, offsetArea, offsetMm, areaReduction);
    container.appendChild(legend);
    
    console.log(`✅ Offset visualization rendered successfully`);
}

/**
 * Crea un path SVG da coordinate poligono
 */
function createPolygonPath(coords, style) {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    
    // Costruisci il path data
    const pathData = coords.map((coord, index) => {
        const command = index === 0 ? 'M' : 'L';
        return `${command} ${coord[0]},${coord[1]}`;
    }).join(' ') + ' Z'; // Chiudi il path
    
    path.setAttribute('d', pathData);
    path.setAttribute('fill', style.fill || 'none');
    path.setAttribute('stroke', style.stroke || '#000');
    path.setAttribute('stroke-width', style.strokeWidth || 1);
    
    if (style.strokeDasharray) {
        path.setAttribute('stroke-dasharray', style.strokeDasharray);
    }
    
    if (style.strokeLinecap) {
        path.setAttribute('stroke-linecap', style.strokeLinecap);
    }
    
    return path;
}

/**
 * Calcola area di un poligono usando formula Shoelace
 */
function calculatePolygonArea(coords) {
    let area = 0;
    const n = coords.length;
    
    for (let i = 0; i < n; i++) {
        const j = (i + 1) % n;
        area += coords[i][0] * coords[j][1];
        area -= coords[j][0] * coords[i][1];
    }
    
    return Math.abs(area) / 2;
}

/**
 * Crea legenda con statistiche offset
 */
function createOffsetLegend(originalArea, offsetArea, offsetMm, areaReduction) {
    const legend = document.createElement('div');
    legend.className = 'offset-legend';
    legend.style.cssText = `
        margin-top: 16px;
        padding: 16px;
        background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%);
        border-left: 4px solid #3B82F6;
        border-radius: 8px;
        font-size: 14px;
    `;
    
    legend.innerHTML = `
        <div style="display: grid; grid-template-columns: auto 1fr; gap: 16px;">
            <div style="display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 30px; height: 3px; background: #3B82F6; border: 2px dashed #3B82F6;"></div>
                    <span style="color: #1E40AF; font-weight: 600;">Perimetro Originale</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 30px; height: 3px; background: #22C55E; border: 2px solid #22C55E;"></div>
                    <span style="color: #15803D; font-weight: 600;">Area Packing (con offset)</span>
                </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px; justify-content: center;">
                <div style="font-size: 13px; color: #374151;">
                    <strong>Offset applicato:</strong> ${offsetMm}mm su tutti i lati
                </div>
                <div style="font-size: 13px; color: #374151;">
                    <strong>Area originale:</strong> ${(originalArea / 1000000).toFixed(2)} m² 
                    → <strong>Area ridotta:</strong> ${(offsetArea / 1000000).toFixed(2)} m²
                </div>
                <div style="font-size: 13px; color: #DC2626; font-weight: 600;">
                    <i class="fas fa-chart-pie"></i> Riduzione area: ${areaReduction}%
                </div>
            </div>
        </div>
    `;
    
    return legend;
}

/**
 * Visualizza singolo poligono (quando offset NON applicato)
 */
function renderSinglePolygonVisualization(coords, containerId = 'wallPreview') {
    console.log(`📐 Rendering single polygon (no offset)`);
    
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`❌ Container ${containerId} not found`);
        return;
    }
    
    // Calcola bounds
    const xs = coords.map(c => c[0]);
    const ys = coords.map(c => c[1]);
    
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    
    const width = maxX - minX;
    const height = maxY - minY;
    const padding = Math.max(width, height) * 0.1;
    
    const viewBox = `${minX - padding} ${minY - padding} ${width + 2*padding} ${height + 2*padding}`;
    
    // Crea SVG
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', viewBox);
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    svg.setAttribute('style', 'max-height: 500px; border: 1px solid #E5E7EB; border-radius: 8px; background: #F9FAFB;');
    
    // Poligono singolo (blu)
    const path = createPolygonPath(coords, {
        fill: 'rgba(59, 130, 246, 0.2)',
        stroke: '#3B82F6',
        strokeWidth: 3
    });
    svg.appendChild(path);
    
    // Replace container content
    container.innerHTML = '';
    container.appendChild(svg);
    
    console.log(`✅ Single polygon visualization rendered`);
}

console.log('✅ Wall Offset Visualization system loaded');

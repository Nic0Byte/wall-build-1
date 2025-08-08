import json
import math
from shapely.geometry import Polygon, box, MultiPolygon, mapping
import svgpathtools
import matplotlib.pyplot as plt
import matplotlib.patches as patches

SCARTO_CUSTOM_MM = 5  # Tolleranza in mm per considerare due custom uguali

def parse_svg_wall(svg_path: str, layer_wall: str="MURO", layer_holes: str="BUCHI") -> Polygon:
    # ... (stessa implementazione vista prima) ...
    pass

def pack_wall(polygon: Polygon,
              block_widths: list[float],
              block_height: float,
              row_offset: float=0.5) -> tuple[list, list]:
    """
    Packing "a mattoncino" ottimizzato:
      - Righe pari (row%2==0): greedy da x = minx
      - Righe dispari: piazza PRIMA un blocco di larghezza `row_offset` a x=minx, poi greedy
      - LOGICA PULITA: evita sovrapposizioni e pezzi custom non necessari
    """
    minx, miny, maxx, maxy = polygon.bounds
    placed = []
    custom = []
    y = miny
    row = 0

    while y < maxy - 1e-6:
        stripe_top = min(y + block_height, maxy)
        stripe = box(minx, y, maxx, stripe_top)
        inter = polygon.intersection(stripe)
        geoms = inter.geoms if isinstance(inter, MultiPolygon) else [inter]

        for comp in geoms:
            if comp.is_empty: 
                continue
            seg_minx, _, seg_maxx, _ = comp.bounds

            # impostiamo il cursore
            cursor = seg_minx

            # se riga dispari, piazza il blocco row_offset in testa
            if row % 2 == 1 and row_offset in block_widths and cursor + row_offset <= seg_maxx + 1e-6:
                candidate = box(cursor, y, cursor + row_offset, stripe_top)
                intersec = candidate.intersection(comp)
                if intersec.area >= 1e-4:
                    # Verifica se è un blocco standard (PERFETTO, non quasi perfetto)
                    if math.isclose(intersec.area, candidate.area, rel_tol=1e-6):
                        placed.append({
                            "type": f"std_{int(row_offset)}x{int(block_height)}",
                            "width": row_offset,
                            "height": block_height,
                            "x": cursor,
                            "y": y
                        })
                    else:
                        # È un pezzo custom
                        custom.append({
                            "type": "custom",
                            "width": intersec.bounds[2]-intersec.bounds[0],
                            "height": intersec.bounds[3]-intersec.bounds[1],
                            "x": intersec.bounds[0],
                            "y": intersec.bounds[1],
                            "geometry": mapping(intersec)
                        })
                cursor += row_offset

            # poi greedy sulle rimanenti larghezze
            while cursor < seg_maxx - 1e-6:
                placed_one = False
                for bw in block_widths:
                    if cursor + bw <= seg_maxx + 1e-6:
                        candidate = box(cursor, y, cursor + bw, stripe_top)
                        intersec = candidate.intersection(comp)
                        if intersec.area < 1e-4:
                            continue
                        
                        # Verifica se è un blocco standard (PERFETTO, non quasi perfetto)
                        if math.isclose(intersec.area, candidate.area, rel_tol=1e-6):
                            placed.append({
                                "type": f"std_{int(bw)}x{int(block_height)}",
                                "width": bw,
                                "height": block_height,
                                "x": cursor,
                                "y": y
                            })
                        else:
                            # È un pezzo custom
                            custom.append({
                                "type": "custom",
                                "width": intersec.bounds[2]-intersec.bounds[0],
                                "height": intersec.bounds[3]-intersec.bounds[1],
                                "x": intersec.bounds[0],
                                "y": intersec.bounds[1],
                                "geometry": mapping(intersec)
                            })
                        placed_one = True
                        cursor += bw
                        break
                
                # GESTIONE AREE RESIDUE: solo se non riesce a piazzare blocchi standard
                if not placed_one:
                    # Crea un pezzo custom per l'area rimanente
                    remaining_width = seg_maxx - cursor
                    if remaining_width > 1e-6:  # se c'è ancora spazio da riempire
                        remaining_area = comp.intersection(box(cursor, y, seg_maxx, stripe_top))
                        if remaining_area.area > 1e-4:
                            custom.append({
                                "type": "custom",
                                "width": remaining_area.bounds[2] - remaining_area.bounds[0],
                                "height": remaining_area.bounds[3] - remaining_area.bounds[1],
                                "x": remaining_area.bounds[0],
                                "y": remaining_area.bounds[1],
                                "geometry": mapping(remaining_area)
                            })
                    break

        y += block_height
        row += 1

    return placed, custom

def summarize_blocks(placed: list[dict]) -> dict:
    summary = {}
    for blk in placed:
        summary[blk["type"]] = summary.get(blk["type"], 0) + 1
    return summary

def create_block_labels(placed: list[dict], custom: list[dict]) -> tuple[dict, dict]:
    """
    Crea etichette standardizzate per blocchi:
    - Standard: A1, A2, B1, B2, C1, C2... (lettera + ID sequenziale)
    - Custom: CU1(1), CU1(2), CU2(1), CU2(2)... (CU + tipo_taglio + posizione)
    """
    # Contatori per ogni tipo di blocco standard
    std_counters = {"A": 0, "B": 0, "C": 0}  # A=1.24m, B=0.83m, C=0.41m
    
    # Mappa dimensioni -> lettera per blocchi standard
    size_to_letter = {
        1239: "A",  # Grande
        826: "B",   # Medio  
        413: "C"    # Piccolo
    }
    
    # Etichette per blocchi standard
    std_labels = {}
    for i, blk in enumerate(placed):
        width = blk["width"]
        letter = size_to_letter.get(width, "X")
        if letter == "X":
            # Se non trova corrispondenza, usa la lettera più vicina
            closest_letter = "A"
            min_diff = abs(width - 1239)
            if abs(width - 826) < min_diff:
                closest_letter = "B"
                min_diff = abs(width - 826)
            if abs(width - 413) < min_diff:
                closest_letter = "C"
            letter = closest_letter
        std_counters[letter] += 1
        std_labels[i] = f"{letter}{std_counters[letter]}"
    
    # Etichette per pezzi custom (tipo_taglio + posizione) con tolleranza
    custom_labels = {}
    custom_types = []  # lista di (width, height) rappresentativi
    
    for i, rit in enumerate(custom):
        w = int(rit["width"])
        h = int(rit["height"])
        # Cerca se esiste già un tipo simile entro la tolleranza
        found = False
        for idx, (w0, h0) in enumerate(custom_types):
            if abs(w - w0) <= SCARTO_CUSTOM_MM and abs(h - h0) <= SCARTO_CUSTOM_MM:
                tipo_taglio = idx + 1
                found = True
                break
        if not found:
            custom_types.append((w, h))
            tipo_taglio = len(custom_types)
        # Conta quante volte abbiamo visto questo tipo
        count = sum(1 for j in range(i) 
                    if any(abs(int(custom[j]["width"]) - w0) <= SCARTO_CUSTOM_MM and abs(int(custom[j]["height"]) - h0) <= SCARTO_CUSTOM_MM 
                           for (w0, h0) in [custom_types[tipo_taglio-1]]))
        custom_labels[i] = f"CU{tipo_taglio}({count})"
    
    return std_labels, custom_labels

def export_to_json(summary: dict, customs: list[dict], placed: list[dict], out_path="distinta_wall.json"):
    # Crea etichette standardizzate
    std_labels, custom_labels = create_block_labels(placed, customs)
    
    # Riorganizza i blocchi standard con etichette
    standard_with_labels = {}
    std_counters = {"A": 0, "B": 0, "C": 0}
    size_to_letter = {1.239: "A", 0.826: "B", 0.413: "C"}
    
    for blk in placed:
        width = blk["width"]
        letter = size_to_letter.get(width, "X")
        if letter == "X":
            # Se non trova corrispondenza, usa la lettera più vicina
            closest_letter = "A"
            min_diff = abs(width - 1239)
            if abs(width - 826) < min_diff:
                closest_letter = "B"
                min_diff = abs(width - 826)
            if abs(width - 413) < min_diff:
                closest_letter = "C"
            letter = closest_letter
        std_counters[letter] += 1
        label = f"{letter}{std_counters[letter]}"
        standard_with_labels[label] = {
            "type": f"std_{width}x{blk['height']}",
            "width": int(width),
            "height": int(blk['height']),
            "x": int(blk['x']),
            "y": int(blk['y'])
        }
    
    # Riorganizza i pezzi custom con etichette
    custom_with_labels = []
    custom_types = {}
    
    for i, rit in enumerate(custom):
        dim_key = (round(rit["width"], 3), round(rit["height"], 3))
        
        if dim_key not in custom_types:
            custom_types[dim_key] = len(custom_types) + 1
        
        tipo_taglio = custom_types[dim_key]
        count = sum(1 for j in range(i) if 
                   (round(custom[j]["width"], 3), round(custom[j]["height"], 3)) == dim_key)
        
        label = f"CU{tipo_taglio}({count + 1})"
        
        custom_with_labels.append({
            "label": label,
            "type": "custom",
            "width": int(rit["width"]),
            "height": int(rit["height"]),
            "x": int(rit["x"]),
            "y": int(rit["y"]),
            "geometry": rit["geometry"]
        })
    
    data = {
        "standard": standard_with_labels,
        "custom": custom_with_labels
    }
    
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"⚙️ Distinta base salvata in {out_path}")

def visualize_wall(polygon: Polygon,
                   placed: list[dict],
                   custom: list[dict],
                   block_height: float,
                   apertures: list[Polygon] = None):
    fig, ax = plt.subplots(figsize=(15, 10))
    ax.set_aspect('equal')
    minx, miny, maxx, maxy = polygon.bounds
    ax.set_xlim(minx-0.1, maxx+0.1)
    ax.set_ylim(miny-0.1, maxy+0.1)
    ax.set_title("Wall Packing with Apertures", fontsize=14, fontweight='bold')

    # contorno parete
    x, y = polygon.exterior.xy
    ax.plot(x, y, color='blue', linewidth=3, label='Wall Outline')

    # Crea etichette standardizzate
    std_labels, custom_labels = create_block_labels(placed, custom)

    # standard con etichette
    for i, blk in enumerate(placed):
        r = patches.Rectangle((blk['x'], blk['y']),
                              blk['width'], blk['height'],
                              facecolor='lightgray', edgecolor='black', linewidth=0.5)
        ax.add_patch(r)
        
        # Aggiungi etichetta del blocco standard
        center_x = blk['x'] + blk['width'] / 2
        center_y = blk['y'] + blk['height'] / 2
        ax.text(center_x, center_y, std_labels[i], 
                ha='center', va='center', fontsize=7, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))

    # custom con etichette
    for i, rit in enumerate(custom):
        r = patches.Polygon(rit['geometry']['coordinates'][0],
                            facecolor='lightgreen', edgecolor='green', hatch='//', linewidth=1)
        ax.add_patch(r)
        
        # Aggiungi etichetta del pezzo custom
        center_x = rit['x'] + rit['width'] / 2
        center_y = rit['y'] + rit['height'] / 2
        ax.text(center_x, center_y, custom_labels[i], 
                ha='center', va='center', fontsize=6, fontweight='bold', color='darkgreen',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))

    # aperture (porte/finestre)
    if apertures:
        for i, aperture in enumerate(apertures):
            x, y = aperture.exterior.xy
            ax.plot(x, y, color='red', linewidth=2, linestyle='--', 
                   label=f'Aperture {i+1}' if i == 0 else "")
            # Riempimento trasparente per le aperture
            ax.fill(x, y, color='red', alpha=0.2)

    # Legenda
    ax.legend()
    
    # Grid
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# ─────────────── esempio di utilizzo ───────────────
if __name__ == "__main__":
    # 1) Carica la parete (qui un semplice poligono “casa”)
    # Parete principale: 12000mm x 4500mm con tetto molto ripido
    wall_exterior = Polygon([(0,0), (12000,0), (12000,4500), (0,2500), (0,0)])
    
    # Porta 1: 1200mm x 2200mm (posizione: 2000mm da sinistra, base a 0mm)
    porta1 = Polygon([(2000,0), (3200,0), (3200,2200), (2000,2200), (2000,0)])
    
    # Porta 2: 1200mm x 2200mm (posizione: 8500mm da sinistra, base a 0mm)
    porta2 = Polygon([(8500,0), (9700,0), (9700,2200), (8500,2200), (8500,0)])
    
    # Sottrai le due porte dalla parete
    wall = wall_exterior.difference(porta1).difference(porta2)
    
    # 2) Parametri mattoni (dimensioni reali in millimetri)
    BLOCK_HEIGHT = 495  # 495mm
    BLOCK_WIDTHS = [1239, 826, 413]  # 1239mm, 826mm, 413mm

    # 3) Nesting “a mattoncino”
    # Usiamo il blocco medio (826mm) come offset per l'alternanza
    placed, custom = pack_wall(wall, BLOCK_WIDTHS, BLOCK_HEIGHT, row_offset=826)

    # 4) Distinta base su console con etichette standardizzate
    summary = summarize_blocks(placed)
    std_labels, custom_labels = create_block_labels(placed, custom)
    
    print("🔨 Distinta base blocchi standard:")
    for k,v in summary.items():
        print(f"  • {v} × {k}")
    
    print(f"\n✂️  Pezzi custom totali: {len(custom)}")
    for i, rit in enumerate(custom):
        label = custom_labels[i]
        print(f"  {label}) {int(rit['width'])}×{int(rit['height'])} mm @ ({int(rit['x'])},{int(rit['y'])})")


    # 5) Esporta in JSON
    export_to_json(summary, custom, placed, out_path="distinta_base_wall.json")

    # 6) Visualizza con Matplotlib
    visualize_wall(wall, placed, custom, BLOCK_HEIGHT, apertures=[porta1, porta2])

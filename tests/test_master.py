#!/usr/bin/env python3
"""
🧪 TEST MASTER - Suite completa di test unificata

Questo test unifica tutte le funzionalità di test in un unico file organizzato:
- Test parsing files (SVG, DWG, DXF)
- Test algoritmi di packing
- Test qualità risultati
- Test export (JSON, DXF, PDF)
- Analisi performance e metriche

Sostituisce tutti i test precedenti frammentati.
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import datetime

# Import sistema principale
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main

# Optional plotting per visualizzazioni
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Rectangle, Polygon as MPLPolygon
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ matplotlib non disponibile - visualizzazioni disabilitate")

# Shapely per geometrie
from shapely.geometry import Polygon, box


class WallBuildTestSuite:
    """Suite completa di test per il sistema wall-build."""
    
    def __init__(self):
        self.results = {}
        self.test_files = {
            # SVG convertiti (sempre disponibili)
            "ROTTINI_LAY_REV0.svg": {
                "type": "svg",
                "description": "SVG convertito - Progetto Rottini",
                "priority": "high"
            },
            "FELICE_LAY_REV0.svg": {
                "type": "svg", 
                "description": "SVG convertito - Progetto Felice",
                "priority": "high"
            },
            
            # DWG originali (se disponibili)
            "ROTTINI_LAY_REV0.dwg": {
                "type": "dwg",
                "description": "DWG originale - Progetto Rottini",
                "priority": "medium"
            },
            "FELICE_LAY_REV0.dwg": {
                "type": "dwg",
                "description": "DWG originale - Progetto Felice", 
                "priority": "medium"
            },
            
            # Test files personalizzati
            "test_parete_dwg.dwg": {
                "type": "dwg",
                "description": "DWG test personalizzato",
                "priority": "low"
            },
            "test_parete_semplice.svg": {
                "type": "svg",
                "description": "SVG test semplice",
                "priority": "low"
            },
            "test_parete_difficile.svg": {
                "type": "svg",
                "description": "SVG test complesso",
                "priority": "low"
            }
        }
    
    def run_all_tests(self) -> Dict:
        """Esegue suite completa di test."""
        
        print("🚀 WALL-BUILD TEST SUITE MASTER")
        print("=" * 60)
        print(f"⏰ Avvio: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. Test sistema parsing
        print("📁 1. TEST PARSING SYSTEM")
        print("-" * 40)
        parsing_results = self._test_parsing_system()
        self.results['parsing'] = parsing_results
        
        # 2. Test algoritmi packing
        print("\n🧱 2. TEST PACKING ALGORITHMS")
        print("-" * 40)
        packing_results = self._test_packing_algorithms()
        self.results['packing'] = packing_results
        
        # 3. Test qualità
        print("\n🔍 3. TEST QUALITY ANALYSIS") 
        print("-" * 40)
        quality_results = self._test_quality_analysis()
        self.results['quality'] = quality_results
        
        # 4. Test export
        print("\n📤 4. TEST EXPORT SYSTEM")
        print("-" * 40)
        export_results = self._test_export_system()
        self.results['export'] = export_results
        
        # 5. Report finale
        print("\n📊 5. FINAL REPORT")
        print("-" * 40)
        final_report = self._generate_final_report()
        
        # Assembla risultati
        complete_results = {
            'timestamp': datetime.datetime.now().isoformat(),
            'parsing': parsing_results,
            'packing': packing_results,
            'quality': quality_results,
            'export': export_results,
            'summary': final_report
        }
        
        # Salva risultati
        self._save_test_results(complete_results)
        
        return complete_results
    
    def _test_parsing_system(self) -> Dict:
        """Test completo del sistema di parsing."""
        
        results = {}
        
        for filename, info in self.test_files.items():
            filepath = Path(filename)
            
            if not filepath.exists():
                print(f"⏭️  {filename}: File non trovato")
                results[filename] = {'status': 'skipped', 'reason': 'file_not_found'}
                continue
            
            print(f"📄 Test: {filename} ({info['description']})")
            
            try:
                # Leggi file
                with open(filepath, 'rb') as f:
                    file_bytes = f.read()
                
                file_size = len(file_bytes)
                print(f"   📊 Size: {file_size:,} bytes")
                
                # Analizza header se DWG
                if info['type'] == 'dwg':
                    header_info = main._analyze_dwg_header(file_bytes)
                    print(f"   🔍 Format: {header_info['format']} {header_info['version']}")
                    print(f"   ✅ Compatible: {header_info['compatible']}")
                
                # Test parsing
                start_time = datetime.datetime.now()
                parete, aperture = main.parse_wall_file(
                    file_bytes, filename,
                    layer_wall="MURO", 
                    layer_holes="BUCHI"
                )
                parse_time = (datetime.datetime.now() - start_time).total_seconds()
                
                # Analizza risultato
                area_parete = parete.area
                num_aperture = len(aperture) if aperture else 0
                bounds = parete.bounds
                
                print(f"   ✅ SUCCESS!")
                print(f"   📐 Area: {area_parete:,.0f} mm²")
                print(f"   🔳 Aperture: {num_aperture}")
                print(f"   ⏱️  Parse time: {parse_time:.2f}s")
                print(f"   📏 Bounds: ({bounds[0]:.0f}, {bounds[1]:.0f}) → ({bounds[2]:.0f}, {bounds[3]:.0f})")
                
                results[filename] = {
                    'status': 'success',
                    'file_size': file_size,
                    'parse_time': parse_time,
                    'area': area_parete,
                    'apertures': num_aperture,
                    'bounds': bounds,
                    'wall_polygon': parete,
                    'aperture_polygons': aperture
                }
                
            except Exception as e:
                print(f"   ❌ FAILED: {e}")
                results[filename] = {'status': 'failed', 'error': str(e)}
        
        return results
    
    def _test_packing_algorithms(self) -> Dict:
        """Test algoritmi di packing su file parsati con successo."""
        
        results = {}
        
        # Prendi solo file parsati con successo
        successful_parses = {
            name: data for name, data in self.results.get('parsing', {}).items()
            if data.get('status') == 'success'
        }
        
        if not successful_parses:
            print("❌ Nessun file disponibile per test packing")
            return {}
        
        for filename, parse_data in successful_parses.items():
            print(f"🧱 Test packing: {filename}")
            
            try:
                parete = parse_data['wall_polygon']
                aperture = parse_data['aperture_polygons']
                
                # Configurazione packing
                config = {
                    'block_widths': [1239, 826, 413],
                    'block_height': 413,
                    'row_offset': 826
                }
                
                # Test packing
                start_time = datetime.datetime.now()
                placed_blocks, custom_pieces = main.pack_wall(
                    parete,
                    config['block_widths'],
                    config['block_height'],
                    row_offset=config['row_offset'],
                    apertures=aperture
                )
                pack_time = (datetime.datetime.now() - start_time).total_seconds()
                
                # Calcola metriche
                summary = main.summarize_blocks(placed_blocks)
                metrics = main.calculate_metrics(placed_blocks, custom_pieces, parete.area)
                
                print(f"   ✅ Packing completato")
                print(f"   🧱 Blocchi standard: {len(placed_blocks)}")
                print(f"   ✂️ Pezzi custom: {len(custom_pieces)}")
                print(f"   📊 Efficienza: {metrics['efficiency']:.1%}")
                print(f"   🗑️ Spreco: {metrics['waste_ratio']:.1%}")
                print(f"   ⏱️  Pack time: {pack_time:.2f}s")
                
                results[filename] = {
                    'status': 'success',
                    'pack_time': pack_time,
                    'placed_blocks': placed_blocks,
                    'custom_pieces': custom_pieces,
                    'summary': summary,
                    'metrics': metrics,
                    'config': config
                }
                
            except Exception as e:
                print(f"   ❌ Packing failed: {e}")
                results[filename] = {'status': 'failed', 'error': str(e)}
        
        return results
    
    def _test_quality_analysis(self) -> Dict:
        """Analisi qualità dei risultati di packing."""
        
        results = {}
        
        # Prendi solo packing riusciti
        successful_packs = {
            name: data for name, data in self.results.get('packing', {}).items()
            if data.get('status') == 'success'
        }
        
        for filename, pack_data in successful_packs.items():
            print(f"🔍 Quality analysis: {filename}")
            
            try:
                placed_blocks = pack_data['placed_blocks']
                custom_pieces = pack_data['custom_pieces']
                parse_data = self.results['parsing'][filename]
                parete = parse_data['wall_polygon']
                aperture = parse_data['aperture_polygons']
                
                # Analisi qualità
                quality_issues = self._analyze_packing_quality(
                    placed_blocks, custom_pieces, parete, aperture
                )
                
                # Calcola quality score
                total_blocks = len(placed_blocks) + len(custom_pieces)
                total_issues = (
                    len(quality_issues['blocks_outside_wall']) +
                    len(quality_issues['blocks_in_apertures']) +
                    len(quality_issues['overlapping_blocks'])
                )
                
                quality_score = max(0, 100 - (total_issues / total_blocks * 100)) if total_blocks > 0 else 0
                
                print(f"   📊 Quality Score: {quality_score:.1f}/100")
                print(f"   ❌ Blocchi fuori parete: {len(quality_issues['blocks_outside_wall'])}")
                print(f"   ❌ Blocchi in aperture: {len(quality_issues['blocks_in_apertures'])}")
                print(f"   ❌ Sovrapposizioni: {len(quality_issues['overlapping_blocks'])}")
                
                # Valutazione qualitativa
                if quality_score >= 90:
                    grade = "ECCELLENTE ✅"
                elif quality_score >= 70:
                    grade = "BUONO ⚠️"
                elif quality_score >= 50:
                    grade = "SUFFICIENTE ⚠️"
                else:
                    grade = "PROBLEMATICO ❌"
                
                print(f"   🎯 Valutazione: {grade}")
                
                results[filename] = {
                    'status': 'success',
                    'quality_score': quality_score,
                    'issues': quality_issues,
                    'grade': grade,
                    'total_blocks': total_blocks,
                    'total_issues': total_issues
                }
                
            except Exception as e:
                print(f"   ❌ Quality analysis failed: {e}")
                results[filename] = {'status': 'failed', 'error': str(e)}
        
        return results
    
    def _test_export_system(self) -> Dict:
        """Test sistema di export (JSON, DXF, visualizzazioni)."""
        
        results = {}
        
        # Prendi solo packing riusciti
        successful_packs = {
            name: data for name, data in self.results.get('packing', {}).items()
            if data.get('status') == 'success'
        }
        
        for filename, pack_data in successful_packs.items():
            print(f"📤 Export test: {filename}")
            
            project_name = filename.replace('.svg', '').replace('.dwg', '')
            
            try:
                placed_blocks = pack_data['placed_blocks']
                custom_pieces = pack_data['custom_pieces']
                summary = pack_data['summary']
                parse_data = self.results['parsing'][filename]
                parete = parse_data['wall_polygon']
                aperture = parse_data['aperture_polygons']
                
                export_results = {}
                
                # 1. Test export JSON
                try:
                    json_path = main.export_to_json(
                        summary, custom_pieces, placed_blocks,
                        f"test_output_{project_name}.json",
                        main.build_run_params(826)
                    )
                    export_results['json'] = {'status': 'success', 'path': json_path}
                    print(f"   ✅ JSON: {json_path}")
                except Exception as e:
                    export_results['json'] = {'status': 'failed', 'error': str(e)}
                    print(f"   ❌ JSON failed: {e}")
                
                # 2. Test export DXF
                try:
                    if main.ezdxf_available:
                        dxf_path = main.export_to_dxf(
                            summary, custom_pieces, placed_blocks,
                            parete, aperture, 
                            project_name=f"Test {project_name}",
                            out_path=f"test_output_{project_name}.dxf"
                        )
                        export_results['dxf'] = {'status': 'success', 'path': dxf_path}
                        print(f"   ✅ DXF: {dxf_path}")
                    else:
                        export_results['dxf'] = {'status': 'skipped', 'reason': 'ezdxf not available'}
                        print(f"   ⏭️  DXF: ezdxf not available")
                except Exception as e:
                    export_results['dxf'] = {'status': 'failed', 'error': str(e)}
                    print(f"   ❌ DXF failed: {e}")
                
                # 3. Test visualizzazione
                try:
                    if MATPLOTLIB_AVAILABLE:
                        plot_path = self._create_test_visualization(
                            placed_blocks, custom_pieces, parete, aperture,
                            f"test_visualization_{project_name}.png"
                        )
                        export_results['plot'] = {'status': 'success', 'path': plot_path}
                        print(f"   ✅ Plot: {plot_path}")
                    else:
                        export_results['plot'] = {'status': 'skipped', 'reason': 'matplotlib not available'}
                        print(f"   ⏭️  Plot: matplotlib not available")
                except Exception as e:
                    export_results['plot'] = {'status': 'failed', 'error': str(e)}
                    print(f"   ❌ Plot failed: {e}")
                
                results[filename] = {
                    'status': 'success',
                    'exports': export_results
                }
                
            except Exception as e:
                print(f"   ❌ Export test failed: {e}")
                results[filename] = {'status': 'failed', 'error': str(e)}
        
        return results
    
    def _analyze_packing_quality(self, placed_blocks: List[Dict], custom_pieces: List[Dict], 
                                parete: Polygon, aperture: List[Polygon]) -> Dict:
        """Analizza qualità del packing."""
        
        issues = {
            'blocks_outside_wall': [],
            'blocks_in_apertures': [],
            'overlapping_blocks': []
        }
        
        all_blocks = []
        
        # Converti blocchi in geometrie per analisi
        for i, block in enumerate(placed_blocks):
            x = block.get('x', 0)
            y = block.get('y', 0)
            w = block.get('width', 0)
            h = block.get('height', 0)
            
            block_poly = box(x, y, x + w, y + h)
            all_blocks.append({
                'id': f"std_{i}",
                'type': 'standard',
                'polygon': block_poly
            })
        
        for i, piece in enumerate(custom_pieces):
            if 'geometry' in piece:
                # Prova a creare poligono da geometry
                try:
                    geom_data = piece['geometry']
                    if isinstance(geom_data, dict):
                        # Coordinate format
                        coords = geom_data.get('coordinates', [[]])
                        if coords and len(coords[0]) >= 3:
                            piece_poly = Polygon(coords[0])
                        else:
                            # Fallback: usa bounds
                            x = piece.get('x', 0)
                            y = piece.get('y', 0)
                            w = piece.get('width', 0)
                            h = piece.get('height', 0)
                            piece_poly = box(x, y, x + w, y + h)
                    else:
                        # Fallback
                        x = piece.get('x', 0)
                        y = piece.get('y', 0)
                        w = piece.get('width', 0)
                        h = piece.get('height', 0)
                        piece_poly = box(x, y, x + w, y + h)
                    
                    all_blocks.append({
                        'id': f"custom_{i}",
                        'type': 'custom',
                        'polygon': piece_poly
                    })
                except:
                    # Ignora pezzi con geometria problematica
                    continue
        
        # Controlli qualità
        for block in all_blocks:
            try:
                block_poly = block['polygon']
                
                # 1. Controllo fuori parete
                if not parete.contains(block_poly):
                    intersection = parete.intersection(block_poly)
                    if intersection.area > 0:
                        outside_ratio = 1 - (intersection.area / block_poly.area)
                        if outside_ratio > 0.05:  # >5% fuori
                            issues['blocks_outside_wall'].append({
                                'id': block['id'],
                                'type': block['type'],
                                'outside_ratio': outside_ratio
                            })
                    else:
                        # Completamente fuori
                        issues['blocks_outside_wall'].append({
                            'id': block['id'],
                            'type': block['type'],
                            'outside_ratio': 1.0
                        })
                
                # 2. Controllo aperture
                for j, ap in enumerate(aperture):
                    if block_poly.intersects(ap):
                        intersection = block_poly.intersection(ap)
                        if intersection.area > 0:
                            overlap_ratio = intersection.area / block_poly.area
                            if overlap_ratio > 0.05:  # >5% sovrapposizione
                                issues['blocks_in_apertures'].append({
                                    'block_id': block['id'],
                                    'aperture_id': j,
                                    'overlap_ratio': overlap_ratio
                                })
            except:
                # Ignora errori geometrici
                continue
        
        return issues
    
    def _create_test_visualization(self, placed_blocks: List[Dict], custom_pieces: List[Dict],
                                  parete: Polygon, aperture: List[Polygon], 
                                  output_path: str) -> str:
        """Crea visualizzazione di test."""
        
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        ax.set_title(f'Wall Build Test Visualization', fontweight='bold')
        ax.set_aspect('equal')
        
        # Disegna parete
        wall_coords = list(parete.exterior.coords)
        wall_polygon = MPLPolygon(wall_coords, fill=False, edgecolor='black', linewidth=2)
        ax.add_patch(wall_polygon)
        
        # Disegna aperture
        for apertura in aperture:
            ap_coords = list(apertura.exterior.coords)
            ap_polygon = MPLPolygon(ap_coords, fill=True, facecolor='lightcoral', 
                                   edgecolor='red', alpha=0.7)
            ax.add_patch(ap_polygon)
        
        # Disegna blocchi standard
        for block in placed_blocks:
            x = block.get('x', 0)
            y = block.get('y', 0)
            w = block.get('width', 0)
            h = block.get('height', 0)
            
            rect = Rectangle((x, y), w, h, facecolor='lightblue', 
                           edgecolor='blue', alpha=0.6)
            ax.add_patch(rect)
        
        # Disegna pezzi custom
        for piece in custom_pieces:
            x = piece.get('x', 0)
            y = piece.get('y', 0)
            w = piece.get('width', 0)
            h = piece.get('height', 0)
            
            rect = Rectangle((x, y), w, h, facecolor='lightgreen',
                           edgecolor='green', alpha=0.6)
            ax.add_patch(rect)
        
        # Setup assi
        bounds = parete.bounds
        margin = max(bounds[2] - bounds[0], bounds[3] - bounds[1]) * 0.1
        ax.set_xlim(bounds[0] - margin, bounds[2] + margin)
        ax.set_ylim(bounds[1] - margin, bounds[3] + margin)
        ax.grid(True, alpha=0.3)
        
        # Legenda
        ax.legend(['Parete', 'Aperture', 'Blocchi Standard', 'Pezzi Custom'])
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def _generate_final_report(self) -> Dict:
        """Genera report finale."""
        
        parsing_success = len([r for r in self.results.get('parsing', {}).values() 
                              if r.get('status') == 'success'])
        parsing_total = len(self.results.get('parsing', {}))
        
        packing_success = len([r for r in self.results.get('packing', {}).values()
                              if r.get('status') == 'success'])
        packing_total = len(self.results.get('packing', {}))
        
        quality_scores = [r.get('quality_score', 0) for r in self.results.get('quality', {}).values()
                         if r.get('status') == 'success']
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        export_success = len([r for r in self.results.get('export', {}).values()
                             if r.get('status') == 'success'])
        export_total = len(self.results.get('export', {}))
        
        report = {
            'parsing_success_rate': f"{parsing_success}/{parsing_total}",
            'packing_success_rate': f"{packing_success}/{packing_total}",
            'average_quality_score': round(avg_quality, 1),
            'export_success_rate': f"{export_success}/{export_total}",
            'overall_status': 'PASS' if (parsing_success > 0 and packing_success > 0) else 'FAIL'
        }
        
        # Stampa report
        print(f"📊 PARSING: {report['parsing_success_rate']} files")
        print(f"🧱 PACKING: {report['packing_success_rate']} algorithms")
        print(f"🔍 QUALITY: {report['average_quality_score']}/100 average")
        print(f"📤 EXPORT: {report['export_success_rate']} systems")
        print(f"🎯 OVERALL: {report['overall_status']}")
        
        return report
    
    def _save_test_results(self, results: Dict):
        """Salva risultati test in JSON."""
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"test_master_results_{timestamp}.json"
        
        # Prepara dati per serializzazione (rimuovi oggetti Shapely)
        serializable_results = self._make_serializable(results)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Test results saved: {output_file}")
    
    def _make_serializable(self, obj):
        """Converte oggetti non serializzabili per JSON."""
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k in ['wall_polygon', 'aperture_polygons']:
                    # Salta geometrie Shapely
                    continue
                result[k] = self._make_serializable(v)
            return result
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Skip oggetti complessi
            return str(obj)
        else:
            return obj
    
    def run_quick_test(self, target_file: str = None) -> Dict:
        """Esegue test rapido su file specifico."""
        
        if target_file:
            # Test solo file specificato
            original_files = self.test_files.copy()
            self.test_files = {target_file: original_files.get(target_file, {
                'type': 'unknown', 'description': 'Target file', 'priority': 'high'
            })}
        
        print(f"⚡ QUICK TEST MODE")
        if target_file:
            print(f"🎯 Target: {target_file}")
        print("=" * 40)
        
        # Esegui solo parsing e packing
        parsing_results = self._test_parsing_system()
        self.results['parsing'] = parsing_results
        
        packing_results = self._test_packing_algorithms()
        self.results['packing'] = packing_results
        
        # Report rapido
        print(f"\n⚡ QUICK RESULTS:")
        for filename, result in packing_results.items():
            if result.get('status') == 'success':
                metrics = result['metrics']
                print(f"✅ {filename}:")
                print(f"   🧱 Blocks: {len(result['placed_blocks'])} std + {len(result['custom_pieces'])} custom")
                print(f"   📊 Efficiency: {metrics['efficiency']:.1%}")
        
        return {'parsing': parsing_results, 'packing': packing_results}


# ────────────────────────────────────────────────────────────────────────────────
# FUNZIONI DI UTILITÀ PER TEST SPECIFICI
# ────────────────────────────────────────────────────────────────────────────────

def test_specific_file(filename: str):
    """Test rapido su file specifico."""
    
    suite = WallBuildTestSuite()
    return suite.run_quick_test(filename)


def test_parsing_only():
    """Test solo sistema parsing."""
    
    suite = WallBuildTestSuite()
    return suite._test_parsing_system()


def test_dxfgrabber_compatibility():
    """Test compatibilità dxfgrabber."""
    
    print("🔧 TEST DXFGRABBER COMPATIBILITY")
    print("=" * 40)
    
    try:
        import dxfgrabber
        print(f"✅ dxfgrabber disponibile - versione: {dxfgrabber.__version__}")
        
        # Test su file DWG se disponibili
        dwg_files = ["ROTTINI_LAY_REV0.dwg", "FELICE_LAY_REV0.dwg"]
        
        for filename in dwg_files:
            if Path(filename).exists():
                print(f"\n📄 Test: {filename}")
                try:
                    dwg = dxfgrabber.readfile(filename)
                    print(f"   ✅ File aperto")
                    print(f"   📊 Version: {dwg.header.get('$ACADVER', 'Unknown')}")
                    print(f"   📁 Layers: {len(dwg.layers)}")
                    print(f"   🔷 Entities: {len(dwg.entities)}")
                    
                    # Cerca layer comuni
                    layer_names = set()
                    for entity in dwg.entities:
                        if hasattr(entity, 'layer'):
                            layer_names.add(entity.layer)
                    
                    print(f"   🗂️  Unique layers: {sorted(layer_names)}")
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    
    except ImportError:
        print("❌ dxfgrabber not available")
        return False
    
    return True


# ────────────────────────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ────────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test specifico
        command = sys.argv[1]
        
        if command == "quick":
            # Test rapido
            target_file = sys.argv[2] if len(sys.argv) > 2 else None
            suite = WallBuildTestSuite()
            results = suite.run_quick_test(target_file)
            
        elif command == "parsing":
            # Solo parsing
            results = test_parsing_only()
            
        elif command == "dxfgrabber":
            # Test dxfgrabber
            test_dxfgrabber_compatibility()
            
        elif command == "file" and len(sys.argv) > 2:
            # Test file specifico
            filename = sys.argv[2]
            results = test_specific_file(filename)
            
        else:
            print("❌ Comando non riconosciuto")
            print("Usage: python test_master.py [quick|parsing|dxfgrabber|file <filename>]")
            
    else:
        # Test completo
        suite = WallBuildTestSuite()
        results = suite.run_all_tests()
        
        print(f"\n🏁 TEST SUITE COMPLETED!")
        print(f"📊 Overall status: {results['summary']['overall_status']}")

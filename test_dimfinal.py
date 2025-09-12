#!/usr/bin/env python3
"""
Test finale per verificare che le dimensioni custom effettivamente cambino
il numero di blocchi prodotti dall'algoritmo.
"""

import json
import requests
import time

# Test configurations
configurations = [
    {
        "name": "Standard TAKTAK",
        "dimensions": [1500, 826, 413],
        "height": 495
    },
    {
        "name": "Blocchi Piccoli", 
        "dimensions": [800, 600, 400],
        "height": 495
    },
    {
        "name": "Blocchi Grandi",
        "dimensions": [2000, 1000, 500], 
        "height": 495
    }
]

def test_configuration(config):
    """Test una configurazione specifica"""
    print(f"\n🧪 Testing: {config['name']}")
    print(f"   Dimensioni: {config['dimensions']}×{config['height']}")
    
    # Prepare form data
    form_data = {
        'row_offset': 826,
        'block_widths': ','.join(map(str, config['dimensions'])),
        'project_name': f"Test_{config['name'].replace(' ', '_')}",
        'color_theme': json.dumps({}),
        'block_dimensions': json.dumps({
            'block_widths': config['dimensions'],
            'block_height': config['height'],
            'block_depth': 100
        })
    }
    
    # Prepare file
    with open('test_parete_semplice_custom.svg', 'rb') as f:
        files = {'file': ('test_parete_semplice_custom.svg', f, 'image/svg+xml')}
        
        try:
            response = requests.post(
                'http://localhost:8000/api/upload',
                data=form_data,
                files=files,
                auth=('admin', 'admin123')
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Success!")
                print(f"   📊 Summary: {result.get('summary', {})}")
                print(f"   ✂️ Custom pieces: {result.get('custom_count', 0)}")
                return result
            else:
                print(f"   ❌ Error {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"   🔌 Connection error: {e}")
            return None

def main():
    print("🎯 TESTING CUSTOM BLOCK DIMENSIONS")
    print("=" * 50)
    
    results = []
    for config in configurations:
        result = test_configuration(config)
        if result:
            results.append({
                'name': config['name'],
                'dimensions': config['dimensions'], 
                'summary': result.get('summary', {}),
                'custom_count': result.get('custom_count', 0)
            })
        time.sleep(1)  # Rate limiting
    
    # Compare results
    print(f"\n📈 COMPARISON:")
    print("=" * 50)
    for r in results:
        total_blocks = sum(r['summary'].values()) if r['summary'] else 0
        print(f"{r['name']:15} | Dimensions: {r['dimensions']} | Blocks: {total_blocks:3d} | Custom: {r['custom_count']:2d}")
    
    # Check if different
    if len(results) >= 2:
        summaries = [r['summary'] for r in results]
        all_same = all(s == summaries[0] for s in summaries)
        
        if all_same:
            print(f"\n❌ FAILED: All configurations produced SAME results!")
            print(f"   This indicates custom dimensions are NOT working properly.")
        else:
            print(f"\n✅ SUCCESS: Different configurations produced DIFFERENT results!")
            print(f"   Custom dimensions are working correctly.")
    else:
        print(f"\n⚠️ Need at least 2 successful tests to compare.")

if __name__ == "__main__":
    main()

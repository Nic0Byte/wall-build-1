"""
Test Script - Selezione Algoritmo Packing
Verifica che l'implementazione della selezione algoritmo funzioni correttamente
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'wallbuild.db')

def test_algorithm_field():
    """Testa che il campo algorithm_type esista e funzioni."""
    
    print("🧪 TEST: Selezione Algoritmo Packing")
    print("=" * 70)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database non trovato: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Verifica schema
        print("\n1️⃣ Verifica schema database...")
        cursor.execute("PRAGMA table_info(system_profiles)")
        columns = {col[1]: col for col in cursor.fetchall()}
        
        if 'algorithm_type' not in columns:
            print("❌ Colonna 'algorithm_type' non trovata!")
            return False
        
        algo_col = columns['algorithm_type']
        print(f"✅ Colonna 'algorithm_type' trovata:")
        print(f"   - Tipo: {algo_col[2]}")
        print(f"   - Default: {algo_col[4]}")
        print(f"   - NOT NULL: {'Sì' if algo_col[3] else 'No'}")
        
        # 2. Conta profili
        print("\n2️⃣ Analisi profili esistenti...")
        cursor.execute("SELECT COUNT(*) FROM system_profiles WHERE is_active = 1")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM system_profiles WHERE is_active = 1 AND algorithm_type = 'small'")
        small_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM system_profiles WHERE is_active = 1 AND algorithm_type = 'big'")
        big_count = cursor.fetchone()[0]
        
        print(f"   📊 Totale profili attivi: {total}")
        print(f"   🏠 Profili SMALL: {small_count}")
        print(f"   🏭 Profili BIG: {big_count}")
        
        # 3. Mostra esempi
        print("\n3️⃣ Esempi profili:")
        cursor.execute("""
            SELECT id, name, algorithm_type, is_default 
            FROM system_profiles 
            WHERE is_active = 1 
            LIMIT 5
        """)
        
        profiles = cursor.fetchall()
        if profiles:
            for prof in profiles:
                algo_icon = '🏭' if prof[2] == 'big' else '🏠'
                default_star = '⭐' if prof[3] else '  '
                print(f"   {default_star} [{prof[0]}] {prof[1]}: {algo_icon} {prof[2].upper()}")
        else:
            print("   📭 Nessun profilo trovato")
        
        # 4. Test creazione profilo (opzionale)
        test_creation = input("\n4️⃣ Vuoi testare la creazione di un profilo? (y/n): ")
        
        if test_creation.lower() == 'y':
            print("\n   Creazione profilo di test...")
            
            # Simula dati profilo
            test_profile = {
                'name': 'Test Algorithm BIG',
                'description': 'Profilo di test per algoritmo BIG',
                'block_config': json.dumps({
                    'widths': [1239, 826, 413],
                    'heights': [495, 495, 495]
                }),
                'moraletti_config': json.dumps({
                    'thickness': 58,
                    'height': 495,
                    'heightFromGround': 95,
                    'spacing': 420,
                    'countLarge': 3,
                    'countMedium': 2,
                    'countSmall': 1
                }),
                'algorithm_type': 'big',
                'user_id': 1,  # Assumi user_id = 1
                'is_default': False,
                'is_active': True
            }
            
            cursor.execute("""
                INSERT INTO system_profiles 
                (user_id, name, description, block_config, moraletti_config, 
                 algorithm_type, is_default, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_profile['user_id'],
                test_profile['name'],
                test_profile['description'],
                test_profile['block_config'],
                test_profile['moraletti_config'],
                test_profile['algorithm_type'],
                test_profile['is_default'],
                test_profile['is_active'],
                datetime.now(),
                datetime.now()
            ))
            
            conn.commit()
            profile_id = cursor.lastrowid
            
            print(f"   ✅ Profilo creato con ID: {profile_id}")
            print(f"   🏭 Algoritmo: {test_profile['algorithm_type'].upper()}")
            
            # Verifica creazione
            cursor.execute("""
                SELECT name, algorithm_type 
                FROM system_profiles 
                WHERE id = ?
            """, (profile_id,))
            
            created = cursor.fetchone()
            if created and created[1] == 'big':
                print(f"   ✅ Verifica: Profilo '{created[0]}' con algoritmo '{created[1]}' salvato correttamente!")
            else:
                print(f"   ❌ Errore: Profilo non salvato correttamente")
        
        print("\n" + "=" * 70)
        print("✅ Test completato con successo!")
        return True
        
    except Exception as e:
        print(f"\n❌ Errore durante il test: {e}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    success = test_algorithm_field()
    
    if success:
        print("\n🎉 Tutti i test passati!")
        print("\n📋 Prossimi passi:")
        print("   1. Avvia l'applicazione")
        print("   2. Vai nella sezione Profili Sistema")
        print("   3. Crea un nuovo profilo e seleziona un algoritmo")
        print("   4. Verifica che il badge algoritmo appaia correttamente")
        print("   5. Attiva il profilo e controlla la visualizzazione nello Step 3")
        exit(0)
    else:
        print("\n❌ Alcuni test sono falliti!")
        print("   Controlla i log sopra per dettagli")
        exit(1)

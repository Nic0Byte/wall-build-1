"""
Migration: Add geometry fields to saved_projects table
Date: 2025-10-21
Purpose: Enable DXF export from restored projects (Opzione 1)
"""

import sqlite3
from pathlib import Path
import sys

def migrate():
    """Add wall_geometry_json and apertures_geometry_json columns"""
    
    db_path = Path("data/wallbuild.db")
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    print(f"📊 Connecting to database: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(saved_projects)")
        columns = [column[1] for column in cursor.fetchall()]
        
        migrations_applied = []
        
        # Add wall_geometry_json column
        if 'wall_geometry_json' not in columns:
            print("➕ Adding column: wall_geometry_json")
            cursor.execute("""
                ALTER TABLE saved_projects
                ADD COLUMN wall_geometry_json TEXT
            """)
            migrations_applied.append('wall_geometry_json')
        else:
            print("✅ Column wall_geometry_json already exists")
        
        # Add apertures_geometry_json column
        if 'apertures_geometry_json' not in columns:
            print("➕ Adding column: apertures_geometry_json")
            cursor.execute("""
                ALTER TABLE saved_projects
                ADD COLUMN apertures_geometry_json TEXT
            """)
            migrations_applied.append('apertures_geometry_json')
        else:
            print("✅ Column apertures_geometry_json already exists")
        
        # Commit changes
        if migrations_applied:
            conn.commit()
            print(f"\n✅ Migration completed successfully!")
            print(f"   Columns added: {', '.join(migrations_applied)}")
        else:
            print(f"\n✅ No migration needed - all columns already exist")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("🔄 Database Migration: Add Geometry Fields for Session Restore")
    print("=" * 70)
    print()
    
    success = migrate()
    
    print()
    print("=" * 70)
    if success:
        print("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Migration failed!")
        sys.exit(1)

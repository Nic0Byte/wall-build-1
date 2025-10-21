"""
Migration: Add dxf_path field to saved_projects table
Date: 2025-10-21
Purpose: Store path to pre-generated DXF files
"""

import sqlite3
from pathlib import Path
import sys

def migrate():
    """Add dxf_path column to saved_projects table"""
    
    db_path = Path("data/wallbuild.db")
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    print(f"📊 Connecting to database: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(saved_projects)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add dxf_path column if it doesn't exist
        if 'dxf_path' not in columns:
            print("➕ Adding column: dxf_path")
            cursor.execute("""
                ALTER TABLE saved_projects
                ADD COLUMN dxf_path VARCHAR(500)
            """)
            conn.commit()
            print(f"✅ Migration completed successfully!")
        else:
            print("✅ Column dxf_path already exists")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(saved_projects)")
        columns_after = cursor.fetchall()
        
        print(f"\n📋 Current saved_projects schema:")
        for col in columns_after:
            print(f"   - {col[1]} ({col[2]})")
        
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
    print("🔄 Database Migration: Add DXF Path Field")
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

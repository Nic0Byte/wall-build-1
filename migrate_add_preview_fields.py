"""
Migration: Add preview_image and blocks_standard_json fields to saved_projects table
Date: 2025-10-21
Purpose: Enable direct Step 5 restore without file reprocessing
"""

import sqlite3
from pathlib import Path
import sys

def migrate():
    """Add preview_image and blocks_standard_json columns to saved_projects table"""
    
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
        
        # Add preview_image column if it doesn't exist
        if 'preview_image' not in columns:
            print("➕ Adding column: preview_image")
            cursor.execute("""
                ALTER TABLE saved_projects
                ADD COLUMN preview_image TEXT
            """)
            migrations_applied.append('preview_image')
        else:
            print("✅ Column preview_image already exists")
        
        # Add blocks_standard_json column if it doesn't exist
        if 'blocks_standard_json' not in columns:
            print("➕ Adding column: blocks_standard_json")
            cursor.execute("""
                ALTER TABLE saved_projects
                ADD COLUMN blocks_standard_json TEXT
            """)
            migrations_applied.append('blocks_standard_json')
        else:
            print("✅ Column blocks_standard_json already exists")
        
        # Commit changes
        if migrations_applied:
            conn.commit()
            print(f"\n✅ Migration completed successfully!")
            print(f"   Columns added: {', '.join(migrations_applied)}")
        else:
            print(f"\n✅ No migration needed - all columns already exist")
        
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
    print("🔄 Database Migration: Add Preview and Blocks Standard Fields")
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

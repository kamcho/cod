import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'COD.settings')
django.setup()

def reset_db():
    print("Starting database reset...")
    with connection.cursor() as cursor:
        print("Disabling foreign key checks...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        # Get all tables
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Filter tables to drop
        prefixes = ['home_', 'users_', 'payments_', 'user_notifications_']
        to_drop = [t for t in tables if any(t.startswith(p) for p in prefixes)]
        
        for table in to_drop:
            print(f"Dropping table {table}...")
            cursor.execute(f"DROP TABLE IF EXISTS `{table}`;")
            
        print("Clearing migration history for home and users...")
        cursor.execute("DELETE FROM django_migrations WHERE app IN ('home', 'users');")
        
        print("Re-enabling foreign key checks...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        print("Database reset complete.")
        print("\nNEXT STEPS:")
        print("1. python manage.py makemigrations home users")
        print("2. python manage.py migrate")
        print("3. python manage.py createsuperuser")

if __name__ == "__main__":
    try:
        reset_db()
    except Exception as e:
        print(f"Error during reset: {e}")

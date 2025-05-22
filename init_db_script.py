import sqlite3

# Copied from Leverancierv2.py
def init_db():
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    
    # Maak klanten tabel (Ultimo ERP systemen)
    c.execute('''
    CREATE TABLE IF NOT EXISTS klanten (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        naam TEXT NOT NULL,
        domein TEXT NOT NULL,
        api_key TEXT NOT NULL
    )
    ''')
    
    # Maak voortgangsstatus-toewijzingen tabel
    c.execute('''
    CREATE TABLE IF NOT EXISTS status_toewijzingen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        klant_id INTEGER NOT NULL,
        van_status TEXT NOT NULL,
        naar_status TEXT NOT NULL,
        FOREIGN KEY (klant_id) REFERENCES klanten (id)
    )
    ''')
    
    # Maak jobs cache tabel
    c.execute('''
    CREATE TABLE IF NOT EXISTS jobs_cache (
        id TEXT PRIMARY KEY,
        klant_id INTEGER NOT NULL,
        omschrijving TEXT NOT NULL,
        apparatuur_omschrijving TEXT,
        processfunctie_omschrijving TEXT,
        voortgang_status TEXT NOT NULL,
        leverancier_id TEXT NOT NULL,
        wijzigingsdatum TEXT NOT NULL,
        data JSON NOT NULL,
        FOREIGN KEY (klant_id) REFERENCES klanten (id)
    )
    ''')
    
    # Maak inlogcodes tabel
    c.execute('''
    CREATE TABLE IF NOT EXISTS inlogcodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        code TEXT NOT NULL,
        aangemaakt_op TEXT NOT NULL,
        gebruikt BOOLEAN NOT NULL DEFAULT 0
    )
    ''')
    
    # Maak email verificatie cache tabel
    c.execute('''
    CREATE TABLE IF NOT EXISTS email_verification_cache (
        email TEXT PRIMARY KEY,
        verified BOOLEAN NOT NULL,
        timestamp TEXT NOT NULL
    )
    ''')
    
    # Maak sync control tabel
    c.execute('''
    CREATE TABLE IF NOT EXISTS sync_control (
        id INTEGER PRIMARY KEY,
        force_sync BOOLEAN NOT NULL DEFAULT 0,
        last_sync TEXT,
        sync_interval INTEGER NOT NULL DEFAULT 3600
    )
    ''')
    
    # Voeg standaard sync instellingen toe als ze nog niet bestaan
    c.execute("SELECT COUNT(*) FROM sync_control")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO sync_control (id, force_sync, last_sync, sync_interval) VALUES (1, 0, NULL, 3600)")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()

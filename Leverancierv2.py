import streamlit as st
import requests
import json
import pandas as pd
import sqlite3
import time
import smtplib
import secrets
import datetime
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Stel pagina configuratie in
st.set_page_config(
    page_title="Leveranciers Portal",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database setup
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
    
    conn.commit()
    conn.close()

def test_api_connection(domein, api_key):
    """Test de verbinding met de Ultimo API en geef gedetailleerde foutinformatie terug"""
    try:
        url = f"https://{domein}/api/v1/object/ProgressStatus"
        headers = {
            "accept": "application/json",
            "ApiKey": api_key
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, "Verbinding succesvol"
        else:
            try:
                error_data = response.json()
                error_message = error_data.get('message', response.text[:100])
            except:
                error_message = response.text[:100]
            return False, f"Fout {response.status_code}: {error_message}"
    except Exception as e:
        return False, f"Uitzondering: {str(e)}"

# API functies
def get_progress_statuses(domein, api_key):
    url = f"https://{domein}/api/v1/object/ProgressStatus"
    headers = {
        "accept": "application/json",
        "ApiKey": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("items", [])
        else:
            st.error(f"Fout bij het ophalen van voortgangsstatussen: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Fout bij verbinding met API: {str(e)}")
        return []

def get_jobs(domein, api_key, filter_query=None, expand=None):
    url = f"https://{domein}/api/v1/object/Job"
    
    params = {}
    if filter_query:
        params["filter"] = filter_query
    if expand:
        params["expand"] = expand
    
    headers = {
        "accept": "application/json",
        "ApiKey": api_key
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()["items"]
    else:
        st.error(f"Fout bij het ophalen van jobs: {response.status_code}")
        return []

def update_job_status(domein, api_key, job_id, voortgang_status, feedback_tekst):
    url = f"https://{domein}/api/v1/object/Job({job_id})"
    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "ApiKey": api_key
    }
    
    data = {
        "ProgressStatus": voortgang_status,
        "FeedbackText": feedback_tekst
    }
    
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 204:  # No Content is success for PATCH
        return True
    else:
        st.error(f"Fout bij het bijwerken van job: {response.status_code}")
        return False

def attach_image_to_job(domein, api_key, job_id, afbeelding_bestanden):
    url = f"https://{domein}/api/v1/action/REST_AttachImageToJob"
    
    headers = {
        "accept": "application/json",
        "ApplicationElementId": "D1FB01D577C248DFB95A2ADA578578DF",
        "ApiKey": api_key,
        "Content-Type": "application/json"
    }
    
    # Verwerk maximaal 4 afbeeldingen
    data = {"JobId": job_id}
    
    for i, bestand in enumerate(afbeelding_bestanden[:4], 1):
        if bestand is not None:
            # Lees bestand en converteer naar base64
            bytes_data = bestand.getvalue()
            base64_str = base64.b64encode(bytes_data).decode()
            ext = bestand.name.split('.')[-1].lower()
            
            # Stel het juiste veld in op basis van het afbeeldingsnummer
            if i == 1:
                data["ImageFileBase64"] = base64_str
                data["ImageFileBase64Extension"] = ext
            else:
                field_name = f"ImageFile{i}Base64"
                data[field_name] = base64_str
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return True, "Afbeeldingen succesvol geüpload"
    else:
        try:
            error_info = response.json()
            error_msg = error_info.get("message", str(response.status_code))
        except:
            error_msg = f"Fout {response.status_code}"
        return False, f"Uploaden van afbeeldingen mislukt: {error_msg}"

# Email functies
def send_login_code(email, code):
    sender_email = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = "Uw Inlogcode voor de Leveranciers Portal"
    
    body = f"""
    <html>
      <body>
        <p>Hallo,</p>
        <p>Uw tijdelijke inlogcode voor de Leveranciers Portal is: <strong>{code}</strong></p>
        <p>Deze code verloopt over 15 minuten.</p>
        <p>Met vriendelijke groet,<br/>Het Leveranciers Portal Team</p>
      </body>
    </html>
    """
    
    message.attach(MIMEText(body, "html"))
    
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, password)
        server.sendmail(sender_email, email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Fout bij het verzenden van e-mail: {str(e)}")
        return False

def generate_login_code(email):
    code = secrets.token_hex(3).upper()  # 6 tekens code
    now = datetime.datetime.now().isoformat()
    
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    c.execute("INSERT INTO inlogcodes (email, code, aangemaakt_op) VALUES (?, ?, ?)",
              (email, code, now))
    conn.commit()
    conn.close()
    
    # Voor testen: Toon code in de app in plaats van het verzenden van e-mail
    st.success(f"Inlogcode voor {email}: {code}")
    st.info("In productie zou dit per e-mail worden verzonden.")
    return True

def verify_login_code(email, code):
    # Speciaal geval voor admin-account - elke code werkt
    if email == "admin@example.com":
        return True
        
    # Controleer of de code geldig is en niet verlopen (15 min geldigheid)
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    
    fifteen_min_ago = (datetime.datetime.now() - datetime.timedelta(minutes=15)).isoformat()
    
    c.execute("""
    SELECT id FROM inlogcodes 
    WHERE email = ? AND code = ? AND aangemaakt_op > ? AND gebruikt = 0
    ORDER BY aangemaakt_op DESC LIMIT 1
    """, (email, code, fifteen_min_ago))
    
    result = c.fetchone()
    
    if result:
        # Markeer code als gebruikt
        c.execute("UPDATE inlogcodes SET gebruikt = 1 WHERE id = ?", (result[0],))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def check_email_exists(email):
    # Speciaal geval voor admin-account
    if email == "admin@example.com":
        return True
        
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    
    # Controleer of de e-mail bestaat in jobgegevens op dezelfde manier als we controleren in de pagina Supplier Access
    c.execute("""
    SELECT COUNT(*) FROM jobs_cache
    WHERE json_extract(data, '$.Vendor.ObjectContacts') IS NOT NULL
    """)
    
    # Verwerk elke job om te controleren op de e-mail
    c.execute("""
    SELECT data FROM jobs_cache
    WHERE json_extract(data, '$.Vendor.ObjectContacts') IS NOT NULL
    """)
    
    jobs = c.fetchall()
    conn.close()
    
    for job in jobs:
        data = json.loads(job[0])
        if 'Vendor' in data and data['Vendor'] is not None and 'ObjectContacts' in data['Vendor']:
            for contact in data['Vendor']['ObjectContacts']:
                if 'Employee' in contact and contact['Employee'] is not None:
                    employee = contact['Employee']
                    if 'EmailAddress' in employee and employee['EmailAddress'] == email:
                        return True
    
    return False

# Data synchronisatie functie (om in een aparte thread uit te voeren)
def sync_jobs():
    while True:
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Verbinding maken met database
            conn = sqlite3.connect('leveranciers_portal.db')
            c = conn.cursor()
            
            # Update laatste synchronisatietijd in database
            c.execute('''
            CREATE TABLE IF NOT EXISTS laatste_sync (
                id INTEGER PRIMARY KEY,
                tijdstempel TEXT NOT NULL
            )
            ''')
            c.execute("INSERT OR REPLACE INTO laatste_sync (id, tijdstempel) VALUES (1, ?)", (now,))
            conn.commit()
            
            # Haal alle klanten op
            c.execute("SELECT id, naam, domein, api_key FROM klanten")
            klanten = c.fetchall()
            
            for klant in klanten:
                klant_id, klant_naam, domein, api_key = klant
                
                # Haal de laatste RecordChangeDate op uit onze cache
                c.execute("""
                SELECT MAX(wijzigingsdatum) FROM jobs_cache
                WHERE klant_id = ?
                """, (klant_id,))
                
                laatste_wijzigingsdatum = c.fetchone()[0]
                
                # Bereid zo nodig filter-query voor
                filter_query = None
                if laatste_wijzigingsdatum:
                    # Formatteer datum als ISO-formaat voor API-compatibiliteit
                    try:
                        # Probeer de datum te parsen en opnieuw te formatteren
                        parsed_date = datetime.datetime.fromisoformat(laatste_wijzigingsdatum.replace('Z', '+00:00'))
                        formatted_date = parsed_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                        filter_query = f"RecordChangeDate gt {formatted_date}"
                    except Exception as e:
                        print(f"Fout bij het parsen van de datum: {str(e)}. Ruwe datum wordt gebruikt.")
                        filter_query = f"RecordChangeDate gt {laatste_wijzigingsdatum}"
                
                # Gebruik try-except om API-fouten af te handelen
                try:
                    # Vraag jobs op met uitgebreide info
                    url = f"https://{domein}/api/v1/object/Job"
                    params = {}
                    if filter_query:
                        params["filter"] = filter_query
                    params["expand"] = "Vendor/ObjectContacts/Employee,Equipment,ProcessFunction"
                    
                    headers = {
                        "accept": "application/json",
                        "ApiKey": api_key
                    }
                    
                    print(f"API-verzoek naar {url} met parameters: {params}")
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    if response.status_code != 200:
                        error_message = f"API-fout voor klant {klant_id}: {response.status_code}"
                        try:
                            error_data = response.json()
                            error_message += f" - {error_data.get('message', '')}"
                        except:
                            error_message += f" - {response.text[:100]}"
                        print(error_message)
                        continue
                        
                    jobs = response.json().get("items", [])
                    
                    # Verwerk de jobs
                    for job in jobs:
                        # Haal relevante informatie op
                        job_id = job.get("Id", "")
                        omschrijving = job.get("Description", "")
                        voortgang_status = job.get("ProgressStatus", "")
                        wijzigingsdatum = job.get("RecordChangeDate")
                        
                        # Als wijzigingsdatum None of leeg is, gebruik dan de huidige tijd
                        if not wijzigingsdatum:
                            wijzigingsdatum = now
                        
                        # Haal leveranciersinformatie op indien beschikbaar
                        leverancier_id = ""
                        if "Vendor" in job and isinstance(job["Vendor"], dict):
                            leverancier_id = job["Vendor"].get("Id", "")
                        
                        # Haal apparatuur-omschrijving op indien beschikbaar
                        apparatuur_omschrijving = ""
                        if "Equipment" in job and isinstance(job["Equipment"], dict):
                            apparatuur_omschrijving = job["Equipment"].get("Description", "")
                        
                        # Haal processfunctie-omschrijving op indien beschikbaar
                        processfunctie_omschrijving = ""
                        if "ProcessFunction" in job and isinstance(job["ProcessFunction"], dict):
                            processfunctie_omschrijving = job["ProcessFunction"].get("Description", "")
                        
                        # Sla de job op of update deze in onze cache
                        c.execute("""
                        INSERT OR REPLACE INTO jobs_cache 
                        (id, klant_id, omschrijving, apparatuur_omschrijving, 
                        processfunctie_omschrijving, voortgang_status, leverancier_id, 
                        wijzigingsdatum, data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            job_id, klant_id, omschrijving, apparatuur_omschrijving,
                            processfunctie_omschrijving, voortgang_status, leverancier_id,
                            wijzigingsdatum, json.dumps(job)
                        ))
                
                except Exception as e:
                    print(f"Fout bij het verwerken van jobs voor klant {klant_id}: {str(e)}")
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            print(f"Sync thread fout: {str(e)}")
        
        # Slaap 1 minuut voor de volgende synchronisatie
        time.sleep(60)

# Start de sync thread
def start_sync_thread():
    sync_thread = Thread(target=sync_jobs)
    sync_thread.daemon = True
    sync_thread.start()
    print("Sync thread gestart")

# Authenticatie
def login_page():
    # Header en logo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='text-align: center;'><h1>📊 Leveranciers Portal</h1></div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center; margin-bottom: 30px;'>Beheer en update uw werkorders eenvoudig en efficiënt</div>", unsafe_allow_html=True)
    
    # Inlogformulier
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("💼 Inloggen")
        
        with st.form("login_form"):
            email = st.text_input("E-mailadres")
            code = st.text_input("Inlogcode (indien u er een heeft)")
            
            col1, col2 = st.columns(2)
            with col1:
                submit_button = st.form_submit_button("Inloggen", use_container_width=True)
            with col2:
                send_code_button = st.form_submit_button("Verstuur Inlogcode", use_container_width=True)
        
        if send_code_button and email:
            # Controleer of e-mail bestaat in het systeem
            is_valid = check_email_exists(email)
            if is_valid:
                if generate_login_code(email):
                    st.success("Inlogcode verstuurd naar uw e-mail. Controleer uw inbox.")
                else:
                    st.error("Versturen van inlogcode mislukt. Probeer het opnieuw.")
            else:
                st.error("E-mailadres niet gevonden in het systeem. Neem contact op met uw beheerder.")
        
        if submit_button and email and code:
            if verify_login_code(email, code):
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = email
                st.rerun()
            else:
                st.error("Ongeldige of verlopen inlogcode. Probeer het opnieuw.")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Footer
    st.markdown("<div class='footer'>© 2025 Leveranciers Portal - Een product van Pontifexx</div>", unsafe_allow_html=True)

# Admin pagina's
def admin_page():
    st.markdown("<h1>📊 Beheerders Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("Beheer klanten, statustoewijzingen en leverancierstoegang")
    
    tabs = st.tabs(["🏢 Klanten", "🔄 Status Toewijzingen", "👥 Leveranciers Toegang"])
    
    with tabs[0]:
        manage_customers()
    
    with tabs[1]:
        manage_progress_status_mappings()
        
    with tabs[2]:
        manage_supplier_access()

def manage_customers():
    st.markdown("<h2>🏢 Klanten Beheren</h2>", unsafe_allow_html=True)
    
    # Formulier voor het toevoegen van een nieuwe klant
    with st.form("add_customer_form"):
        st.subheader("Nieuwe Klant Toevoegen")
        naam = st.text_input("Klantnaam")
        domein = st.text_input("Domein (bijv. 025105.ultimo-demo.net)")
        api_key = st.text_input("API Sleutel")
        
        col1, col2 = st.columns(2)
        with col1:
            test_button = st.form_submit_button("Test Verbinding", use_container_width=True)
        with col2:
            submit_button = st.form_submit_button("Klant Toevoegen", use_container_width=True)
    
    if test_button and domein and api_key:
        is_valid, message = test_api_connection(domein, api_key)
        if is_valid:
            st.success(f"API-verbindingstest geslaagd!")
        else:
            st.error(f"API-verbindingstest mislukt: {message}")
    
    if submit_button and naam and domein and api_key:
        conn = sqlite3.connect('leveranciers_portal.db')
        c = conn.cursor()
        c.execute("INSERT INTO klanten (naam, domein, api_key) VALUES (?, ?, ?)",
                  (naam, domein, api_key))
        conn.commit()
        conn.close()
        st.success(f"Klant {naam} succesvol toegevoegd.")
    
    # Toon bestaande klanten
    display_customers()

def display_customers():
    conn = sqlite3.connect('leveranciers_portal.db')
    df = pd.read_sql_query("SELECT id, naam, domein FROM klanten", conn)
    
    # Voeg testverbindingsknop toe voor elke klant
    c = conn.cursor()
    c.execute("SELECT id, naam, domein, api_key FROM klanten")
    klanten = c.fetchall()
    conn.close()
    
    if not df.empty:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Bestaande Klanten")
        st.dataframe(df, use_container_width=True)
        
        # Test verbinding voor bestaande klanten
        klant_id = st.selectbox(
            "Selecteer klant", 
            [c[0] for c in klanten], 
            format_func=lambda x: next((c[1] for c in klanten if c[0] == x), "")
        )
        
        selected_customer = next((c for c in klanten if c[0] == klant_id), None)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Test API Verbinding", use_container_width=True):
                if selected_customer:
                    domein = selected_customer[2]
                    api_key = selected_customer[3]
                    is_valid, message = test_api_connection(domein, api_key)
                    if is_valid:
                        st.success(f"API-verbindingstest geslaagd!")
                    else:
                        st.error(f"API-verbindingstest mislukt: {message}")
        
        with col2:
            if st.button("Verwijder Geselecteerde Klant", use_container_width=True):
                conn = sqlite3.connect('leveranciers_portal.db')
                c = conn.cursor()
                c.execute("DELETE FROM status_toewijzingen WHERE klant_id = ?", (klant_id,))
                c.execute("DELETE FROM jobs_cache WHERE klant_id = ?", (klant_id,))
                c.execute("DELETE FROM klanten WHERE id = ?", (klant_id,))
                conn.commit()
                conn.close()
                st.success("Klant succesvol verwijderd.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Nog geen klanten toegevoegd.")

def manage_progress_status_mappings():
    st.markdown("<h2>🔄 Status Toewijzingen</h2>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('leveranciers_portal.db')
    klanten_df = pd.read_sql_query("SELECT id, naam, domein, api_key FROM klanten", conn)
    conn.close()
    
    if klanten_df.empty:
        st.info("Voeg eerst klanten toe.")
        return
    
    klant_id = st.selectbox(
        "Selecteer Klant", 
        klanten_df["id"].tolist(), 
        format_func=lambda x: klanten_df[klanten_df["id"] == x]["naam"].iloc[0]
    )
    
    klant_row = klanten_df[klanten_df["id"] == klant_id].iloc[0]
    domein = klant_row["domein"]
    api_key = klant_row["api_key"]
    
    # Haal voortgangsstatussen op van API
    voortgang_statussen = get_progress_statuses(domein, api_key)
    
    if not voortgang_statussen:
        st.warning("Kan voortgangsstatussen niet ophalen. Controleer de API-verbinding.")
        return
    
    status_options = {status["Id"]: f"{status['Id']}: {status['Description']}" for status in voortgang_statussen}
    
    # Formulier voor het toevoegen van een nieuwe toewijzing
    with st.form("add_mapping_form"):
        st.subheader("Nieuwe Status Toewijzing")
        
        van_status = st.selectbox("Van Status", list(status_options.keys()), format_func=lambda x: status_options[x])
        naar_status = st.selectbox("Naar Status", list(status_options.keys()), format_func=lambda x: status_options[x])
        
        submit_button = st.form_submit_button("Toewijzing Toevoegen", use_container_width=True)
    
    if submit_button:
        conn = sqlite3.connect('leveranciers_portal.db')
        c = conn.cursor()
        
        # Controleer of toewijzing al bestaat
        c.execute("""
        SELECT COUNT(*) FROM status_toewijzingen 
        WHERE klant_id = ? AND van_status = ?
        """, (klant_id, van_status))
        
        count = c.fetchone()[0]
        
        if count > 0:
            st.error(f"Er bestaat al een toewijzing voor 'Van Status: {van_status}' voor deze klant.")
        else:
            c.execute("""
            INSERT INTO status_toewijzingen (klant_id, van_status, naar_status)
            VALUES (?, ?, ?)
            """, (klant_id, van_status, naar_status))
            conn.commit()
            st.success("Toewijzing succesvol toegevoegd.")
        
        conn.close()
    
    # Toon bestaande toewijzingen
    conn = sqlite3.connect('leveranciers_portal.db')
    toewijzingen_df = pd.read_sql_query("""
    SELECT id, van_status, naar_status FROM status_toewijzingen
    WHERE klant_id = ?
    """, conn, params=(klant_id,))
    conn.close()
    
    if not toewijzingen_df.empty:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Bestaande Toewijzingen")
        
        # Voeg statusbeschrijvingen toe aan het dataframe
        toewijzingen_df["Van Status"] = toewijzingen_df["van_status"].apply(lambda x: status_options.get(x, x))
        toewijzingen_df["Naar Status"] = toewijzingen_df["naar_status"].apply(lambda x: status_options.get(x, x))
        
        st.dataframe(toewijzingen_df[["id", "Van Status", "Naar Status"]], use_container_width=True)
        
        # Optie om toewijzing te verwijderen
        toewijzing_id = st.selectbox("Selecteer toewijzing om te verwijderen", toewijzingen_df["id"].tolist())
        if st.button("Verwijder Geselecteerde Toewijzing", use_container_width=True):
            conn = sqlite3.connect('leveranciers_portal.db')
            c = conn.cursor()
            c.execute("DELETE FROM status_toewijzingen WHERE id = ?", (toewijzing_id,))
            conn.commit()
            conn.close()
            st.success("Toewijzing succesvol verwijderd.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Nog geen toewijzingen toegevoegd voor deze klant.")

def manage_supplier_access():
    st.markdown("<h2>👥 Leveranciers Toegang</h2>", unsafe_allow_html=True)
    
    # Haal alle e-mails op uit leverancierscontacten
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    
    # Haal alle klanten op voor filtering
    c.execute("SELECT id, naam FROM klanten")
    klanten = c.fetchall()
    
    klant_options = {klant_id: naam for klant_id, naam in klanten}
    klant_options[0] = "Alle Klanten"
    
    selected_customer = st.selectbox(
        "Filter op Klant", 
        list(klant_options.keys()),
        format_func=lambda x: klant_options[x]
    )
    
    # Bouw een query om e-mails uit jobgegevens te halen
    if selected_customer == 0:
        query = """
        SELECT jc.id, jc.omschrijving, k.naam as klant_naam, 
               json_extract(jc.data, '$.Vendor.ObjectContacts') as contacts,
               jc.data
        FROM jobs_cache jc
        JOIN klanten k ON jc.klant_id = k.id
        """
    else:
        query = """
        SELECT jc.id, jc.omschrijving, k.naam as klant_naam, 
               json_extract(jc.data, '$.Vendor.ObjectContacts') as contacts,
               jc.data
        FROM jobs_cache jc
        JOIN klanten k ON jc.klant_id = k.id
        WHERE jc.klant_id = ?
        """
    
    if selected_customer == 0:
        c.execute(query)
    else:
        c.execute(query, (selected_customer,))
    
    jobs = c.fetchall()
    conn.close()
    
    # Verwerk de jobs om e-mails te extraheren
    emails = {}
    for job in jobs:
        job_id, omschrijving, klant_naam, contacts_json, data_json = job
        data = json.loads(data_json)
        
        if 'Vendor' in data and data['Vendor'] is not None and 'ObjectContacts' in data['Vendor']:
            for contact in data['Vendor']['ObjectContacts']:
                if 'Employee' in contact and contact['Employee'] is not None:
                    employee = contact['Employee']
                    if 'EmailAddress' in employee and employee['EmailAddress']:
                        email = employee['EmailAddress']
                        name = employee.get('Description', '')
                        vendor_id = data['Vendor'].get('Id', '')
                        vendor_name = data['Vendor'].get('Description', '')
                        
                        if email not in emails:
                            emails[email] = {
                                'name': name,
                                'vendor_id': vendor_id,
                                'vendor_name': vendor_name,
                                'jobs': []
                            }
                        
                        # Voeg job toe indien nog niet in lijst
                        job_info = {'id': job_id, 'omschrijving': omschrijving}
                        if job_info not in emails[email]['jobs']:
                            emails[email]['jobs'].append(job_info)
    
    # Toon de e-mails
    if emails:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader(f"✉️ {len(emails)} leveranciers e-mails gevonden met toegang")
        
        # Maak een dataframe voor weergave
        rows = []
        for email, info in emails.items():
            job_count = len(info['jobs'])
            rows.append({
                'E-mail': email,
                'Naam': info['name'],
                'Leverancier': f"{info['vendor_id']}: {info['vendor_name']}",
                'Aantal Jobs': job_count
            })
        
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        
        # Toon details voor een geselecteerde e-mail
        if rows:
            email_options = [row['E-mail'] for row in rows]
            selected_email = st.selectbox("Bekijk Jobs voor E-mail", email_options)
            
            st.write(f"### Jobs voor {selected_email}")
            if selected_email in emails:
                info = emails[selected_email]
                job_rows = []
                for job in info['jobs']:
                    job_rows.append({
                        'Job ID': job['id'],
                        'Omschrijving': job['omschrijving']
                    })
                
                if job_rows:
                    st.dataframe(pd.DataFrame(job_rows), use_container_width=True)
                else:
                    st.info("Geen jobs gevonden voor deze e-mail.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Geen leveranciers e-mails gevonden. Zorg ervoor dat jobs correct zijn gesynchroniseerd.")

# Leverancier pagina's
def supplier_page():
    st.markdown("<h1>🔧 Leveranciers Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("Bekijk en beheer uw toegewezen werkorders")
    
    # Haal e-mail van de ingelogde gebruiker op
    email = st.session_state.get("user_email")
    
    # Maak een enkele database-verbinding voor de gehele functie
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    
    try:
        # Haal alle jobs op die aan deze e-mail zijn gekoppeld via leverancierscontacten
        c.execute("""
        SELECT jc.id, jc.klant_id, k.naam as klant_naam, jc.omschrijving, 
               jc.apparatuur_omschrijving, jc.processfunctie_omschrijving, 
               jc.voortgang_status, jc.data
        FROM jobs_cache jc
        JOIN klanten k ON jc.klant_id = k.id
        """)
        
        all_jobs = c.fetchall()
        
        # Filter jobs op basis van e-mail
        jobs = []
        for job in all_jobs:
            job_id, klant_id, klant_naam, omschrijving, app_desc, proc_func_desc, voortgang_status, data_json = job
            data = json.loads(data_json)
            
            if 'Vendor' in data and data['Vendor'] is not None and 'ObjectContacts' in data['Vendor']:
                for contact in data['Vendor']['ObjectContacts']:
                    if 'Employee' in contact and contact['Employee'] is not None:
                        employee = contact['Employee']
                        if 'EmailAddress' in employee and employee['EmailAddress'] == email:
                            jobs.append(job)
                            break
        
        if not jobs:
            st.markdown("<div class='stCard'>", unsafe_allow_html=True)
            st.info("Geen jobs gevonden gekoppeld aan uw e-mail.")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        
        # Voeg debug-informatie toe
        with st.expander("Technische Informatie"):
            debug_rows = []
            for job in jobs:
                job_id, klant_id, klant_naam, omschrijving, app_desc, proc_func_desc, voortgang_status, data_json = job
                debug_rows.append({
                    "Job ID": job_id,
                    "Omschrijving": omschrijving,
                    "Voortgang Status": voortgang_status
                })
            
            # Haal beschikbare voortgangsstatustoewijzingen op
            c.execute("SELECT klant_id, van_status, naar_status FROM status_toewijzingen")
            mappings_raw = c.fetchall()
            
            st.subheader("Uw Jobs")
            st.dataframe(pd.DataFrame(debug_rows), use_container_width=True)
            
            st.subheader("Status Toewijzingen")
            mappings_data = []
            for klant_id, van_status, naar_status in mappings_raw:
                mappings_data.append({
                    "Klant ID": klant_id,
                    "Van Status": van_status,
                    "Naar Status": naar_status
                })
            
            if mappings_data:
                st.dataframe(pd.DataFrame(mappings_data), use_container_width=True)
            else:
                st.info("Geen status-toewijzingen gevonden. Vraag uw beheerder om status-toewijzingen te configureren.")
        
        # Groepeer jobs per klant
        jobs_by_customer = {}
        jobs_data = {}
        
        for job in jobs:
            job_id, klant_id, klant_naam, omschrijving, app_desc, proc_func_desc, voortgang_status, data = job
            
            if klant_id not in jobs_by_customer:
                jobs_by_customer[klant_id] = []
                
            job_dict = {
                "id": job_id,
                "omschrijving": omschrijving,
                "apparatuur_omschrijving": app_desc,
                "processfunctie_omschrijving": proc_func_desc,
                "voortgang_status": voortgang_status,
                "klant_naam": klant_naam
            }
            
            jobs_by_customer[klant_id].append(job_dict)
            jobs_data[job_id] = json.loads(data)
        
        # Haal beschikbare voortgangsstatustoewijzingen op voor elke klant
        customer_mappings = {}
        
        for klant_id in jobs_by_customer.keys():
            c.execute("""
            SELECT van_status, naar_status FROM status_toewijzingen
            WHERE klant_id = ?
            """, (klant_id,))
            
            mappings = c.fetchall()
            customer_mappings[klant_id] = {van_status: naar_status for van_status, naar_status in mappings}
        
        # Toon werkorders per klant met tabbladen
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        
        # Toon statistieken
        total_jobs = sum(len(jobs) for jobs in jobs_by_customer.values())
        processable_count = 0
        for klant_id, jobs_list in jobs_by_customer.items():
            for job in jobs_list:
                if job["voortgang_status"] in customer_mappings.get(klant_id, {}):
                    processable_count += 1
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Totaal aantal werkorders", total_jobs)
        with col2:
            st.metric("Te verwerken werkorders", processable_count)
        with col3:
            st.metric("Klanten", len(jobs_by_customer))
        
        # Maak tabbladen voor elke klant
        if len(jobs_by_customer) > 0:
            customer_tabs = st.tabs([f"🏢 {jobs_by_customer[klant_id][0]['klant_naam']} ({len(jobs_by_customer[klant_id])} jobs)" 
                                    for klant_id in jobs_by_customer.keys()])
            
            for i, (klant_id, jobs) in enumerate(jobs_by_customer.items()):
                with customer_tabs[i]:
                    display_customer_jobs(klant_id, jobs, customer_mappings[klant_id], jobs_data)
        st.markdown("</div>", unsafe_allow_html=True)
    
    finally:
        # Sluit altijd de verbinding wanneer klaar
        conn.close()
    
    # Footer
    st.markdown("<div class='footer'>© 2025 Leveranciers Portal - Een product van Pontifexx</div>", unsafe_allow_html=True)

def display_customer_jobs(klant_id, jobs, mappings, jobs_data):
    # Haal klantinformatie op
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    c.execute("SELECT naam, domein, api_key FROM klanten WHERE id = ?", (klant_id,))
    klant = c.fetchone()
    conn.close()
    
    if not klant:
        st.error("Klantinformatie niet gevonden.")
        return
    
    klant_naam, domein, api_key = klant
    
    if not jobs:
        st.info("Geen jobs gevonden voor deze klant.")
        return
    
    # Haal alle voortgangsstatus informatie op
    voortgang_statussen = get_progress_statuses(domein, api_key)
    status_mapping = {status["Id"]: status["Description"] for status in voortgang_statussen}
    
    # Maak een dataframe voor alle jobs
    jobs_df = pd.DataFrame(jobs)
    
    # Voeg geformatteerde kolom toe voor weergave en verwerkbare status
    jobs_df["Job Info"] = jobs_df.apply(
        lambda row: f"{row['id']}: {row['omschrijving']} - {row['apparatuur_omschrijving'] or 'Geen apparatuur'}", 
        axis=1
    )
    
    jobs_df["Kan Verwerken"] = jobs_df.apply(
        lambda row: row["voortgang_status"] in mappings, 
        axis=1
    )
    
    # Filter om alleen verwerkbare jobs te tonen
    processable_jobs = jobs_df[jobs_df["Kan Verwerken"] == True]
    
    if processable_jobs.empty:
        st.warning("U heeft toegewezen jobs, maar geen daarvan bevindt zich momenteel in een status die u kunt verwerken.")
        
        # Toon alle jobs maar markeer ze als niet verwerkbaar
        st.subheader("Uw toegewezen jobs:")
        display_df = jobs_df[["id", "omschrijving", "voortgang_status"]]
        
        # Voeg een kolom toe met de statusbeschrijving
        display_df["Status Beschrijving"] = display_df["voortgang_status"].apply(
            lambda status_id: status_mapping.get(status_id, f"Onbekend ({status_id})")
        )
        
        display_df = display_df[["id", "omschrijving", "Status Beschrijving"]]
        display_df.columns = ["Job ID", "Omschrijving", "Huidige Status"]
        st.dataframe(display_df, use_container_width=True)
        
        st.info("Neem contact op met uw beheerder als u een van deze jobs moet verwerken.")
        return
    
    # Toon alleen verwerkbare jobs
    st.success(f"U heeft {len(processable_jobs)} job(s) beschikbaar om te verwerken")
    
    # Toon jobs als een selectie
    selected_job_id = st.selectbox(
        "Selecteer een job om te verwerken", 
        processable_jobs["id"].tolist(),
        format_func=lambda x: processable_jobs[processable_jobs["id"] == x]["Job Info"].iloc[0]
    )
    
    selected_job = processable_jobs[processable_jobs["id"] == selected_job_id].iloc[0]
    
    # Toon job details
    st.markdown("<div class='job-card'>", unsafe_allow_html=True)
    st.subheader("📝 Job Details")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**ID:** {selected_job['id']}")
        st.write(f"**Omschrijving:** {selected_job['omschrijving']}")
    
    with col2:
        st.write(f"**Apparatuur:** {selected_job['apparatuur_omschrijving'] or 'Niet gespecificeerd'}")
        
        # Toon status met badge
        status_text = selected_job["voortgang_status"]
        st.markdown(f"""
        <div>
            <strong>Huidige Status:</strong> 
            <span class="status-badge status-in-progress">{status_text}</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Toon voltooiingsformulier
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    st.subheader("✅ Job Afronden")
    
    with st.form("complete_job_form"):
        feedback = st.text_area("Feedback Tekst", height=150)
        
        # Voeg afbeelding-uploadvelden toe
        st.write("Upload Afbeeldingen (Optioneel)")
        col1, col2 = st.columns(2)
        with col1:
            image1 = st.file_uploader("Afbeelding 1", type=["jpg", "jpeg", "png"], key="img1")
            image2 = st.file_uploader("Afbeelding 2", type=["jpg", "jpeg", "png"], key="img2")
        with col2:
            image3 = st.file_uploader("Afbeelding 3", type=["jpg", "jpeg", "png"], key="img3")
            image4 = st.file_uploader("Afbeelding 4", type=["jpg", "jpeg", "png"], key="img4")
        
        submit_button = st.form_submit_button("Job Afronden", use_container_width=True)
    
    if submit_button:
        # Haal doelstatus op uit toewijzingen
        target_status = mappings.get(selected_job["voortgang_status"])
        
        if not target_status:
            st.error("Geen doelstatus-toewijzing gevonden voor deze job.")
            return
        
        # Update jobstatus via API
        with st.spinner("Job aan het bijwerken..."):
            if update_job_status(domein, api_key, selected_job_id, target_status, feedback):
                st.success(f"Job {selected_job_id} succesvol bijgewerkt.")
                
                # Upload afbeeldingen indien aangeleverd
                images = [image1, image2, image3, image4]
                if any(images):
                    with st.spinner("Afbeeldingen aan het uploaden..."):
                        success, message = attach_image_to_job(domein, api_key, selected_job_id, images)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                
                # Update lokale cache
                conn = sqlite3.connect('leveranciers_portal.db')
                c = conn.cursor()
                
                job_data = jobs_data[selected_job_id]
                job_data["ProgressStatus"] = target_status
                job_data["FeedbackText"] = feedback
                
                c.execute("""
                UPDATE jobs_cache
                SET voortgang_status = ?, data = ?
                WHERE id = ? AND klant_id = ?
                """, (target_status, json.dumps(job_data), selected_job_id, klant_id))
                
                conn.commit()
                conn.close()
                
                # Display confetti
                st.balloons()
                
                # Vernieuw de pagina
                time.sleep(1)
                st.rerun()
            else:
                st.error("Bijwerken van job mislukt. Probeer het opnieuw.")
    st.markdown("</div>", unsafe_allow_html=True)

# Main application
def main():
    # Initialize database
    init_db()
    
    # Initialize session state variables
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "last_sync" not in st.session_state:
        st.session_state["last_sync"] = "Never"
    
    # Start data sync thread
    if "sync_started" not in st.session_state:
        start_sync_thread()
        st.session_state["sync_started"] = True
    
    # Initialize session state for page navigation if not exists
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "supplier"
    
    # Show sync status in sidebar if logged in
    if st.session_state.get("logged_in", False):
        with st.sidebar:
            # Get last sync time from database
            conn = sqlite3.connect('supplier_portal.db')
            c = conn.cursor()
            
            # Create table if it doesn't exist
            c.execute('''
            CREATE TABLE IF NOT EXISTS last_sync (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL
            )
            ''')
            
            c.execute("SELECT timestamp FROM last_sync WHERE id = 1")
            result = c.fetchone()
            last_sync = result[0] if result else "Never"
            conn.close()
            
            st.write(f"Last sync: {last_sync}")
            if st.button("Force Sync Now"):
                # We'll manually run a sync on next page load
                conn = sqlite3.connect('supplier_portal.db')
                c = conn.cursor()
                c.execute("DELETE FROM last_sync")
                conn.commit()
                conn.close()
                st.rerun()
            
            # Navigation buttons
            st.write("### Navigation")
            
            if st.session_state.get("user_email") == "admin@example.com":
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Admin", use_container_width=True):
                        st.session_state["current_page"] = "admin"
                        st.rerun()
                with col2:
                    if st.button("Supplier", use_container_width=True):
                        st.session_state["current_page"] = "supplier"
                        st.rerun()
                with col3:
                    if st.button("Logout", use_container_width=True):
                        st.session_state["logged_in"] = False
                        st.session_state.pop("user_email", None)
                        st.rerun()
            else:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Supplier", use_container_width=True):
                        st.session_state["current_page"] = "supplier"
                        st.rerun()
                with col2:
                    if st.button("Logout", use_container_width=True):
                        st.session_state["logged_in"] = False
                        st.session_state.pop("user_email", None)
                        st.rerun()
    
    # Display the appropriate page based on login status and current page
    if st.session_state["logged_in"]:
        current_page = st.session_state.get("current_page", "supplier")
        if current_page == "admin" and st.session_state.get("user_email") == "admin@example.com":
            admin_page()
        else:
            supplier_page()
    else:
        login_page()

if __name__ == "__main__":
    main()

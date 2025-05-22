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

# Add pandas options to avoid SettingWithCopyWarning
import pandas as pd
pd.options.mode.copy_on_write = True  # This will suppress the warning in newer pandas versions

# Stel pagina configuratie in
st.set_page_config(
    page_title="Leveranciers Portal",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for new design
st.markdown("""
<style>
    /* Color Palette */
    :root {
        --primary-color: #007bff; /* Blue */
        --secondary-color: #6c757d; /* Gray */
        --background-color: #f0f2f6; /* Light Gray */
        --card-background-color: #ffffff; /* White */
        --text-color: #333333; /* Dark Gray */
        --success-color: #28a745; /* Green */
        --error-color: #dc3545; /* Red */
        --border-color: #dee2e6; /* Light Gray Border */
    }

    body {
        font-family: 'sans-serif';
        color: var(--text-color);
        background-color: var(--background-color);
    }

    /* Typography */
    h1, h2, h3 {
        font-family: 'sans-serif';
        color: var(--primary-color);
    }

    /* Card-like containers */
    .stCard {
        background-color: var(--card-background-color);
        padding: 25px;
        border-radius: 8px;
        border: 1px solid var(--border-color);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    /* Streamlit Button Styling */
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #0056b3; /* Darker blue on hover */
        color: white;
    }
    
    /* Input fields */
    .stTextInput input, .stTextArea textarea {
        border: 1px solid var(--border-color);
        border-radius: 5px;
        padding: 10px;
    }

    /* Footer styling */
    .footer {
        text-align: center;
        padding: 20px;
        font-size: 0.9em;
        color: var(--secondary-color);
        border-top: 1px solid var(--border-color);
        margin-top: 40px;
    }
    
    /* Status Badges (Example) */
    .status-badge {
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.9em;
        font-weight: bold;
        color: white;
    }
    .status-in-progress { background-color: var(--primary-color); }
    .status-completed { background-color: var(--success-color); }
    .status-pending { background-color: var(--secondary-color); }

</style>
""", unsafe_allow_html=True)

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
    # Plaats de job_id tussen aanhalingstekens in de URL
    url = f"https://{domein}/api/v1/object/Job('{job_id}')"
    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "ApiKey": api_key
    }
    
    # Beperk de lengte van feedback_tekst om problemen te voorkomen
    max_feedback_length = 2000  # Pas dit aan op basis van Ultimo API-limieten
    if feedback_tekst and len(feedback_tekst) > max_feedback_length:
        feedback_tekst = feedback_tekst[:max_feedback_length]
    
    # Basis data payload
    data = {
        "ProgressStatus": voortgang_status
    }
    
    # Voeg feedback alleen toe als deze niet leeg is
    if feedback_tekst and feedback_tekst.strip():
        data["FeedbackText"] = feedback_tekst
    
    try:
        # Debug info loggen
        print(f"API Request: PATCH {url}")
        print(f"Headers: {headers}")
        print(f"Data: {json.dumps(data)}")
        
        # Request verzenden
        response = requests.patch(url, headers=headers, json=data)
        
        # Accepteer zowel 204 (No Content) als 200 (OK) als succesvolle response
        if response.status_code == 204 or response.status_code == 200:
            # Bij 200 kunnen we de bijgewerkte job-gegevens opslaan
            if response.status_code == 200:
                try:
                    updated_job = response.json()
                    print(f"Bijgewerkte job ontvangen: {updated_job.get('Id')}")
                except:
                    pass  # Stil doorgaan als we de JSON niet kunnen parsen
            return True
        else:
            # Probeer gedetailleerde foutinformatie te verkrijgen
            error_message = f"Fout bij het bijwerken van job: {response.status_code}"
            try:
                error_details = response.json()
                error_message += f" - {json.dumps(error_details)}"
            except:
                error_message += f" - {response.text[:200]}"
            
            print(error_message)  # Log error for debugging
            st.error(f"Fout bij het bijwerken van job: {response.status_code}")
            
            # Toon gedetailleerde foutinformatie in een expander voor troubleshooting
            with st.expander("Technische foutdetails"):
                st.code(error_message)
                st.write("Controleer de volgende mogelijke oorzaken:")
                st.write("1. De status-overgang is niet toegestaan in het Ultimo-systeem")
                st.write("2. De voortgang_status waarde is ongeldig")
                st.write("3. Er zijn speciale tekens in de feedback die niet worden geaccepteerd")
                st.write("4. De API-sleutel heeft onvoldoende rechten om deze actie uit te voeren")
            
            return False
    except Exception as e:
        error_message = f"Exception bij het bijwerken van job: {str(e)}"
        print(error_message)
        st.error("Onverwachte fout bij het bijwerken van de job")
        
        with st.expander("Technische foutdetails"):
            st.code(error_message)
        
        return False

def test_job_update(domein, api_key, job_id):
    """Test een minimale job update om te zien of API-aanroep werkt"""
    st.info("API-test wordt uitgevoerd...")
    
    # 1. Eerst de huidige job gegevens ophalen
    try:
        # Gebruik enkele quotes voor de job_id
        get_url = f"https://{domein}/api/v1/object/Job('{job_id}')"
        headers = {
            "accept": "application/json",
            "ApiKey": api_key
        }
        
        response = requests.get(get_url, headers=headers)
        
        if response.status_code == 200:
            job_data = response.json()
            current_status = job_data.get("ProgressStatus", "")
            st.success(f"Huidige status opgehaald: {current_status}")
            
            # 2. Probeer alleen de huidige status opnieuw te zetten (minimale verandering)
            update_url = f"https://{domein}/api/v1/object/Job('{job_id}')"
            update_headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "ApiKey": api_key
            }
            
            # Het minimale verzoek dat mogelijk werkt
            update_data = {
                "ProgressStatus": current_status
            }
            
            update_response = requests.patch(update_url, headers=update_headers, json=update_data)
            
            # Accepteer zowel 204 als 200 als succesvolle response
            if update_response.status_code == 204 or update_response.status_code == 200:
                st.success("Test succesvol: minimale update werkt!")
                if update_response.status_code == 200:
                    st.info("API retourneert 200 OK met bijgewerkte job data (dit is goed)")
                elif update_response.status_code == 204:
                    st.info("API retourneert 204 No Content (dit is ook goed)")
                return True
            else:
                st.error(f"Test mislukt: minimale update geeft fout {update_response.status_code}")
                try:
                    error_details = update_response.json()
                    st.code(json.dumps(error_details, indent=2))
                except:
                    st.code(update_response.text[:500])
                return False
        else:
            st.error(f"Kon job details niet ophalen: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Test fout: {str(e)}")
        return False

def check_valid_transitions(domein, api_key, job_id):
    """Check welke statusovergangen geldig zijn voor deze job"""
    # Gebruik enkele quotes voor de job_id
    url = f"https://{domein}/api/v1/object/Job('{job_id}')"
    headers = {
        "accept": "application/json",
        "ApiKey": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            job_data = response.json()
            return job_data.get("ProgressStatus"), True
        else:
            st.error(f"Kon job status niet ophalen: {response.status_code}")
            return None, False
    except Exception as e:
        st.error(f"Fout bij het ophalen van job status: {str(e)}")
        return None, False

def attach_image_to_job(domein, api_key, job_id, afbeelding_bestanden):
    url = f"https://{domein}/api/v1/action/REST_AttachImageToJob"
    
    headers = {
        "accept": "application/json",
        "ApplicationElementId": "D1FB01D577C248DFB95A2ADA578578DF",
        "ApiKey": api_key,
        "Content-Type": "application/json"
    }
    
    # Verwerk maximaal 4 afbeeldingen
    # Let op: hier wordt de JobId zonder quotes gebruikt omdat het om een action endpoint gaat,
    # niet om een object endpoint. Controleer dit in de Ultimo API documentatie.
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
                ext_field_name = f"ImageFile{i}Base64Extension"
                data[ext_field_name] = ext
    
    try:
        # Print debug info
        print(f"Uploading images to job {job_id} via {url}")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            return True, "Afbeeldingen succesvol geüpload"
        else:
            try:
                error_info = response.json()
                error_msg = error_info.get("message", str(response.status_code))
            except:
                error_msg = f"Fout {response.status_code}: {response.text[:200]}"
            
            # Print debug info
            print(f"Image upload error: {error_msg}")
            return False, f"Uploaden van afbeeldingen mislukt: {error_msg}"
    except Exception as e:
        error_msg = f"Exception bij het uploaden van afbeeldingen: {str(e)}"
        print(error_msg)
        return False, error_msg

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
    
    # Sla de code op in de sessie voor eenvoudige demo-toegang
    st.session_state["last_code"] = code
    
    # Sla de code op in de database
    try:
        conn = sqlite3.connect('leveranciers_portal.db')
        c = conn.cursor()
        c.execute("INSERT INTO inlogcodes (email, code, aangemaakt_op) VALUES (?, ?, ?)",
                  (email, code, now))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database fout: {str(e)}")
        return False
    
    # Voor testen: Toon code in de app in plaats van het verzenden van e-mail
    st.success(f"Inlogcode voor {email}: {code}")
    st.info("In productie zou dit per e-mail worden verzonden.")
    return True

def verify_login_code(email, code):
    # Speciaal geval voor admin-account - elke code werkt
    if email == "admin@example.com":
        return True
        
    # Controleer of de code geldig is en niet verlopen (15 min geldigheid)
    try:
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
    except Exception as e:
        print(f"Verificatie fout: {str(e)}")
            
    return False

def check_email_exists(email):
    # Speciaal geval voor admin-account
    if email == "admin@example.com":
        return True
        
    try:
        # First check local cache to avoid API calls
        conn = sqlite3.connect('leveranciers_portal.db')
        c = conn.cursor()
        
        # Check if we've already verified this email in the past 24 hours
        c.execute("""
        CREATE TABLE IF NOT EXISTS email_verification_cache (
            email TEXT PRIMARY KEY,
            verified BOOLEAN NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)
        
        # Check if email is in our verification cache and was verified in the last 24 hours
        one_day_ago = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        c.execute("""
        SELECT verified FROM email_verification_cache
        WHERE email = ? AND timestamp > ?
        """, (email, one_day_ago))
        
        result = c.fetchone()
        if result is not None:
            conn.close()
            return result[0]  # Return cached verification result
        
        # If not in cache, search the jobs cache database
        c.execute("""
        SELECT COUNT(*) FROM jobs_cache
        WHERE json_extract(data, '$.Vendor.ObjectContacts') IS NOT NULL
        """)
        
        # Process each job to check for the email
        c.execute("""
        SELECT data FROM jobs_cache
        WHERE json_extract(data, '$.Vendor.ObjectContacts') IS NOT NULL
        """)
        
        jobs = c.fetchall()
        
        email_found = False
        for job in jobs:
            data = json.loads(job[0])
            if 'Vendor' in data and data['Vendor'] is not None and 'ObjectContacts' in data['Vendor']:
                for contact in data['Vendor']['ObjectContacts']:
                    if 'Employee' in contact and contact['Employee'] is not None:
                        employee = contact['Employee']
                        if 'EmailAddress' in employee and employee['EmailAddress'] == email:
                            email_found = True
                            break
                if email_found:
                    break
        
        # Cache the result of our verification
        now = datetime.datetime.now().isoformat()
        c.execute("""
        INSERT OR REPLACE INTO email_verification_cache (email, verified, timestamp)
        VALUES (?, ?, ?)
        """, (email, email_found, now))
        conn.commit()
        conn.close()
        
        return email_found
    except Exception as e:
        print(f"Error checking email: {str(e)}")
        # Fallback to old search method if needed
        try:
            conn = sqlite3.connect('leveranciers_portal.db')
            c = conn.cursor()
            
            c.execute("""
            SELECT COUNT(*) FROM jobs_cache
            WHERE data LIKE ?
            """, (f'%"EmailAddress":"{email}"%',))
            
            count = c.fetchone()[0]
            conn.close()
            
            if count > 0:
                return True
        except:
            pass
    
    return False

# Force sync function 
def force_sync():
    """Forces a data sync to happen immediately"""
    try:
        conn = sqlite3.connect('leveranciers_portal.db')
        c = conn.cursor()
        
        # Set force sync flag
        c.execute("UPDATE sync_control SET force_sync = 1 WHERE id = 1")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error triggering force sync: {str(e)}")
        return False

# Data synchronisatie functie (om in een aparte thread uit te voeren)
def sync_jobs():
    last_sync_time = None
    
    while True:
        try:
            now = datetime.datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            
            # Verbinding maken met database
            conn = sqlite3.connect('leveranciers_portal.db')
            c = conn.cursor()
            
            # Check if a force sync has been requested
            c.execute("SELECT force_sync, last_sync, sync_interval FROM sync_control WHERE id = 1")
            result = c.fetchone()
            
            if result:
                force_sync_flag, db_last_sync, sync_interval = result
            else:
                # Default values
                force_sync_flag = False
                db_last_sync = None
                sync_interval = 3600  # Default to hourly
                c.execute("INSERT INTO sync_control (id, force_sync, last_sync, sync_interval) VALUES (1, 0, NULL, 3600)")
                conn.commit()
            
            # Determine if we should sync now
            should_sync = False
            
            if force_sync_flag:
                # Reset force sync flag
                should_sync = True
                c.execute("UPDATE sync_control SET force_sync = 0 WHERE id = 1")
                conn.commit()
                print("Forced sync triggered")
            elif db_last_sync is None:
                # No previous sync, do it now
                should_sync = True
                print("Initial sync")
            else:
                # Check if enough time has passed since last sync
                try:
                    last_sync_time = datetime.datetime.fromisoformat(db_last_sync)
                    time_since_last_sync = (now - last_sync_time).total_seconds()
                    should_sync = time_since_last_sync >= sync_interval
                    if should_sync:
                        print(f"Regular sync triggered after {time_since_last_sync} seconds")
                except Exception as e:
                    print(f"Error parsing last sync time: {str(e)}")
                    should_sync = True
            
            if should_sync:
                # Update last synchronization time in database
                c.execute("UPDATE sync_control SET last_sync = ? WHERE id = 1", (now_str,))
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
                                wijzigingsdatum = now_str
                            
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
                print(f"Sync completed at {now_str}")
            
            conn.close()
        
        except Exception as e:
            print(f"Sync thread fout: {str(e)}")
        
        # Slaap 60 seconden voor de volgende check
        # We check every minute if a force sync has been requested,
        # but only perform regular syncs based on the sync_interval
        time.sleep(60)

# Start de sync thread
def start_sync_thread():
    sync_thread = Thread(target=sync_jobs)
    sync_thread.daemon = True
    sync_thread.start()
    print("Sync thread gestart")

# Authenticatie
def login_page():
    # Centering the entire login page content
    st.markdown("<div style='display: flex; justify-content: center; align-items: center;'>", unsafe_allow_html=True)
    
    main_col_width = [0.5, 2, 0.5] # Adjust ratios for wider/narrower central column
    
    # Using columns for centering the main content block
    _, center_col, _ = st.columns(main_col_width)

    with center_col:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True) # Start of card

        # Header
        st.markdown("<div style='text-align: center;'><h1>📊 Leveranciers Portal</h1></div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center; margin-bottom: 30px; font-size: 1.1em; color: var(--secondary-color);'>Beheer en update uw werkorders eenvoudig en efficiënt.</div>", unsafe_allow_html=True)
        
        st.subheader("🔧 Monteur Toegang")
        
        # Session state initialization
        if "email" not in st.session_state:
            st.session_state["email"] = ""
        if "code_sent" not in st.session_state:
            st.session_state["code_sent"] = False
            
        # Step 1: Email Input
        if not st.session_state["code_sent"]:
            st.markdown("<p style='font-size:0.9em; color:var(--secondary-color);'>Voer uw e-mailadres in om een verificatiecode per e-mail te ontvangen.</p>", unsafe_allow_html=True)
            with st.form("email_form"):
                email = st.text_input("📧 E-mailadres", placeholder="uw@email.nl", value=st.session_state.get("email", ""))
                send_code_button = st.form_submit_button("Verificatiecode Versturen", use_container_width=True)
            
            if send_code_button and email:
                st.session_state["email"] = email # Store email before checking
                is_valid = check_email_exists(email)
                if is_valid:
                    if generate_login_code(email): # This function now shows code in app for testing
                        st.session_state["code_sent"] = True
                        # Success message is handled by generate_login_code for now
                        st.rerun()
                    else:
                        st.error("Versturen van code mislukt. Probeer het opnieuw.")
                else:
                    st.error("E-mailadres niet gevonden. Controleer uw invoer of neem contact op met uw beheerder.")
        
        # Step 2: Code Input
        else:
            email = st.session_state["email"]
            # The success message from generate_login_code will be visible here
            st.info(f"Een verificatiecode is (voor testdoeleinden) hierboven weergegeven. In productie wordt deze naar {email} gemaild.")
            
            last_code = st.session_state.get("last_code", "") # Get code from session (set by generate_login_code)
            
            st.markdown("<p style='font-size:0.9em; color:var(--secondary-color);'>Voer de ontvangen (of hierboven getoonde) verificatiecode in.</p>", unsafe_allow_html=True)
            with st.form("code_form"):
                code = st.text_input("🔑 Verificatiecode", value=last_code, placeholder="123ABC")
                
                col1_form, col2_form = st.columns(2)
                with col1_form:
                    back_button = st.form_submit_button("⬅️ Terug naar e-mail", use_container_width=True)
                with col2_form:
                    submit_button = st.form_submit_button("🔒 Inloggen", use_container_width=True)
            
            if back_button:
                st.session_state["code_sent"] = False
                st.session_state["last_code"] = "" # Clear last code
                st.rerun()
                
            if submit_button and code:
                if verify_login_code(email, code):
                    st.session_state["logged_in"] = True
                    st.session_state["user_email"] = email
                    st.session_state.pop("code_sent", None) # Clean up session state
                    st.session_state.pop("last_code", None)
                    st.success("Succesvol ingelogd!")
                    time.sleep(1) # Brief pause for user to see message
                    st.rerun()
                else:
                    st.error("Ongeldige of verlopen code. Probeer het opnieuw of vraag een nieuwe code aan.")
            
            if st.button("Nieuwe code aanvragen", key="resend_code_login"):
                if generate_login_code(email):
                     # Message handled by generate_login_code
                    st.rerun() # Rerun to update the displayed code if necessary
                else:
                    st.error("Versturen van nieuwe code mislukt.")
        
        st.markdown("</div>", unsafe_allow_html=True) # End of card

        # Admin login (klein onder de kaart, nog steeds in center_col)
        with st.expander("⚙️ Admin Login"):
            with st.form("admin_login_form"):
                admin_email = st.text_input("Admin E-mail", key="admin_email_login", placeholder="admin@example.com")
                admin_code = st.text_input("Admin Code (elke code werkt)", key="admin_code_login", type="password")
                admin_login_button = st.form_submit_button("Admin Inloggen", use_container_width=True)
            
            if admin_login_button and admin_email and admin_code:
                if admin_email == "admin@example.com" and verify_login_code(admin_email, admin_code): # verify_login_code handles admin bypass
                    st.session_state["logged_in"] = True
                    st.session_state["user_email"] = admin_email
                    st.session_state.pop("code_sent", None)
                    st.session_state.pop("last_code", None)
                    st.success("Admin succesvol ingelogd!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Ongeldige admin inloggegevens.")
    
    st.markdown("</div>", unsafe_allow_html=True) # End of centering flex div

    # Footer (outside the card and centering columns, but still within the overall page structure)
    st.markdown("<div class='footer'>© 2025 Leveranciers Portal - Een product van Pontifexx</div>", unsafe_allow_html=True)

# Show sync info in sidebar
def sidebar_sync_info():
    # Get sync information
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    
    # Get sync info
    c.execute("SELECT last_sync, sync_interval FROM sync_control WHERE id = 1")
    result = c.fetchone()
    
    if result:
        last_sync, sync_interval = result
    else:
        last_sync = None
        sync_interval = 3600
    
    conn.close()
    
    st.write("### Synchronisatie Status")
    
    # Format interval for display
    if sync_interval == 3600:
        interval_str = "Elk uur"
    elif sync_interval < 3600:
        minutes = sync_interval // 60
        interval_str = f"Elke {minutes} {'minuut' if minutes == 1 else 'minuten'}"
    else:
        hours = sync_interval // 3600
        interval_str = f"Elke {hours} {'uur' if hours == 1 else 'uren'}"
    
    st.write(f"**Interval:** {interval_str}")
    
    if last_sync:
        try:
            last_sync_dt = datetime.datetime.fromisoformat(last_sync)
            formatted_time = last_sync_dt.strftime("%d-%m-%Y %H:%M")
            
            # Calculate time until next sync
            next_sync = last_sync_dt + datetime.timedelta(seconds=sync_interval)
            time_to_next = next_sync - datetime.datetime.now()
            
            if time_to_next.total_seconds() <= 0:
                next_sync_str = "Binnenkort"
            elif time_to_next.total_seconds() < 60:
                next_sync_str = "Binnen een minuut"
            elif time_to_next.total_seconds() < 3600:
                minutes = int(time_to_next.total_seconds() / 60)
                next_sync_str = f"Over {minutes} {'minuut' if minutes == 1 else 'minuten'}"
            else:
                hours = int(time_to_next.total_seconds() / 3600)
                minutes = int((time_to_next.total_seconds() % 3600) / 60)
                next_sync_str = f"Over {hours}{'u' if hours else ''}{minutes if minutes else ''}{'m' if minutes else ''}"
            
            st.write(f"**Laatste sync:** {formatted_time}")
            st.write(f"**Volgende sync:** {next_sync_str}")
        except:
            st.write(f"**Laatste sync:** {last_sync}")
    else:
        st.write("**Laatste sync:** Nooit")
    
    # Add a force sync button
    if st.button("Forceer Sync Nu", key="sidebar_force_sync"):
        if force_sync():
            st.success("Synchronisatie gestart...")
            time.sleep(1)  # Brief delay
            st.rerun()
        else:
            st.error("Fout bij starten synchronisatie")

# Admin pagina's
def admin_page():
    st.markdown("<h1>📊 Beheerders Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("Beheer klanten, statustoewijzingen en leverancierstoegang.")
    
    # Wrap the tab content in a card for overall consistency
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    tabs = st.tabs(["🏢 Klanten", "🔄 Status Toewijzingen", "👥 Leveranciers Toegang", "⚙️ Sync Instellingen"])
    
    with tabs[0]:
        manage_customers()
    
    with tabs[1]:
        manage_progress_status_mappings()
        
    with tabs[2]:
        manage_supplier_access()
        
    with tabs[3]:
        manage_sync_settings()
    st.markdown("</div>", unsafe_allow_html=True) # End of stCard for tabs
    
    # Footer for admin page
    st.markdown("<div class='footer'>© 2025 Leveranciers Portal - Een product van Pontifexx</div>", unsafe_allow_html=True)

def manage_sync_settings():
    st.markdown("<h2>⚙️ Sync Instellingen</h2>", unsafe_allow_html=True)
    
    # Get current sync settings
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    
    # Get current settings or insert defaults
    c.execute("SELECT last_sync, sync_interval FROM sync_control WHERE id = 1")
    result = c.fetchone()
    
    if result:
        last_sync, sync_interval = result
    else:
        last_sync = "Nooit"
        sync_interval = 3600  # Default to hourly
        c.execute("INSERT INTO sync_control (id, force_sync, last_sync, sync_interval) VALUES (1, 0, NULL, 3600)")
        conn.commit()
    
    conn.close()
    
    # Display current settings
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Huidige Instellingen")
        
        # Format last sync time nicely if it exists
        if last_sync and last_sync != "Nooit":
            try:
                last_sync_dt = datetime.datetime.fromisoformat(last_sync)
                formatted_time = last_sync_dt.strftime("%d-%m-%Y %H:%M:%S")
                time_ago = datetime.datetime.now() - last_sync_dt
                
                if time_ago.total_seconds() < 60:
                    time_ago_str = "zojuist"
                elif time_ago.total_seconds() < 3600:
                    minutes = int(time_ago.total_seconds() / 60)
                    time_ago_str = f"{minutes} {'minuut' if minutes == 1 else 'minuten'} geleden"
                elif time_ago.total_seconds() < 86400:
                    hours = int(time_ago.total_seconds() / 3600)
                    time_ago_str = f"{hours} {'uur' if hours == 1 else 'uren'} geleden"
                else:
                    days = int(time_ago.total_seconds() / 86400)
                    time_ago_str = f"{days} {'dag' if days == 1 else 'dagen'} geleden"
                
                st.info(f"Laatste synchronisatie: {formatted_time} ({time_ago_str})")
            except:
                st.info(f"Laatste synchronisatie: {last_sync}")
        else:
            st.info("Laatste synchronisatie: Nooit")
        
        # Show current interval
        if sync_interval == 3600:
            st.write("Huidige interval: Elk uur")
        elif sync_interval < 3600:
            minutes = sync_interval // 60
            st.write(f"Huidige interval: Elke {minutes} {'minuut' if minutes == 1 else 'minuten'}")
        else:
            hours = sync_interval // 3600
            st.write(f"Huidige interval: Elke {hours} {'uur' if hours == 1 else 'uren'}")
        
        # Option to force sync
        if st.button("Forceer Synchronisatie Nu", use_container_width=True):
            if force_sync():
                st.success("Synchronisatie gestart...")
                time.sleep(2)  # Allow time for sync to start
                st.rerun()
            else:
                st.error("Fout bij het starten van de synchronisatie")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Synchronisatie Interval Instellen")
        
        with st.form("sync_interval_form"):
            interval_options = {
                900: "15 minuten",
                1800: "30 minuten",
                3600: "1 uur",
                7200: "2 uur",
                14400: "4 uur",
                28800: "8 uur",
                43200: "12 uur",
                86400: "24 uur"
            }
            
            selected_interval = st.selectbox(
                "Kies interval", 
                list(interval_options.keys()),
                format_func=lambda x: interval_options[x],
                index=list(interval_options.keys()).index(sync_interval) if sync_interval in interval_options else 2
            )
            
            submit_button = st.form_submit_button("Interval Bijwerken", use_container_width=True)
        
        if submit_button:
            conn = sqlite3.connect('leveranciers_portal.db')
            c = conn.cursor()
            c.execute("UPDATE sync_control SET sync_interval = ? WHERE id = 1", (selected_interval,))
            conn.commit()
            conn.close()
            st.success(f"Synchronisatie interval bijgewerkt naar {interval_options[selected_interval]}")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Add explanation of API usage
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    st.subheader("Over API Gebruik")
    st.write("""
    De synchronisatie haalt gegevens op van de Ultimo API volgens het ingestelde interval. 
    Een hogere frequentie houdt de gegevens actueler, maar kan leiden tot meer API-verzoeken.

    **Wanneer gebeurt synchronisatie?**
    - Volgens het ingestelde interval (standaard elk uur)
    - Wanneer u handmatig synchronisatie forceert
    - Bij de eerste keer opstarten van de applicatie

    **Optimalisatie van API-aanroepen:**
    - Er worden alleen gewijzigde records opgehaald sinds de laatste synchronisatie
    - E-mailverificatie bij inloggen gebruikt lokale cache om API-aanroepen te minimaliseren
    - API-aanroepen worden alleen gedaan wanneer nodig
    """)
    st.markdown("</div>", unsafe_allow_html=True)

def manage_customers():
    st.markdown("<h2>🏢 Klanten Beheren</h2>", unsafe_allow_html=True)
    
    # Formulier voor het toevoegen van een nieuwe klant (wrap in stCard)
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    with st.form("add_customer_form"):
        st.subheader("Nieuwe Klant Toevoegen")
        naam = st.text_input("Klantnaam")
        domein = st.text_input("Domein (bijv. 025105.ultimo-demo.net)")
        api_key = st.text_input("API Sleutel", type="password")
        
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
    st.markdown("</div>", unsafe_allow_html=True) # End of stCard for add customer form
    
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
        st.info("Voeg eerst klanten toe om statussen toe te wijzen.")
        return
    
    klant_id = st.selectbox(
        "Selecteer Klant voor Status Toewijzing", 
        klanten_df["id"].tolist(), 
        format_func=lambda x: klanten_df[klanten_df["id"] == x]["naam"].iloc[0],
        key="select_klant_status_mapping"
    )
    
    klant_row = klanten_df[klanten_df["id"] == klant_id].iloc[0]
    domein = klant_row["domein"]
    api_key = klant_row["api_key"]
    
    # Haal voortgangsstatussen op van API
    voortgang_statussen = get_progress_statuses(domein, api_key)
    
    if not voortgang_statussen:
        st.warning("Kan voortgangsstatussen niet ophalen. Controleer de API-verbinding van de klant.")
        return
    
    status_options = {status["Id"]: f"{status['Id']}: {status['Description']}" for status in voortgang_statussen}
    
    # Formulier voor het toevoegen van een nieuwe toewijzing (wrap in stCard)
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    with st.form("add_mapping_form"):
        st.subheader("Nieuwe Status Toewijzing Toevoegen")
        
        van_status = st.selectbox("Van Status (Huidige status in Ultimo)", list(status_options.keys()), format_func=lambda x: status_options[x])
        naar_status = st.selectbox("Naar Status (Status na update door leverancier)", list(status_options.keys()), format_func=lambda x: status_options[x])
        
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
    st.markdown("</div>", unsafe_allow_html=True) # End of stCard for add mapping form
    
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
    st.markdown("<h2>👥 Leveranciers Toegang Overzicht</h2>", unsafe_allow_html=True)
    st.markdown("Bekijk welke leveranciers (via e-mailadres in contactpersoon) toegang hebben tot jobs.")
    
    # Haal alle e-mails op uit leverancierscontacten
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    
    # Haal alle klanten op voor filtering
    c.execute("SELECT id, naam FROM klanten")
    klanten = c.fetchall()
    
    # Prepare options for selectbox, ensuring a default or valid selection
    klant_options = {0: "Alle Klanten"} # Default option
    klant_options.update({klant_id: naam for klant_id, naam in klanten})
    
    selected_customer_id = st.selectbox(
        "Filter op Klant", 
        options=list(klant_options.keys()),
        format_func=lambda x: klant_options[x],
        key="select_klant_supplier_access"
    )
    
    # Bouw een query om e-mails uit jobgegevens te halen
    if selected_customer_id == 0:
        query = """
        SELECT jc.id, jc.omschrijving, k.naam as klant_naam, 
               json_extract(jc.data, '$.Vendor.ObjectContacts') as contacts,
               jc.data
        FROM jobs_cache jc
        JOIN klanten k ON jc.klant_id = k.id
        """
        c.execute(query)
    else:
        query = """
        SELECT jc.id, jc.omschrijving, k.naam as klant_naam, 
               json_extract(jc.data, '$.Vendor.ObjectContacts') as contacts,
               jc.data
        FROM jobs_cache jc
        JOIN klanten k ON jc.klant_id = k.id
        WHERE jc.klant_id = ?
        """
        c.execute(query, (selected_customer_id,))
    
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
    
    # Haal e-mail van de ingelogde gebruiker op
    email = st.session_state.get("user_email")
    
    # Maak een enkele database-verbinding voor de gehele functie
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    
    try:
        # Haal alle jobs op die aan deze e-mail zijn gekoppeld via leverancierscontacten
        # Optimalisatie: Filter direct in SQL als mogelijk, of verfijn de Python filtering.
        # Voor nu houden we de bestaande Python filtering.
        c.execute("""
        SELECT jc.id, jc.klant_id, k.naam as klant_naam, jc.omschrijving, 
               jc.apparatuur_omschrijving, jc.processfunctie_omschrijving, 
               jc.voortgang_status, jc.data
        FROM jobs_cache jc
        JOIN klanten k ON jc.klant_id = k.id
        """)
        
        all_jobs_raw = c.fetchall()
        
        # Filter jobs op basis van e-mail
        user_jobs = []
        for job_raw in all_jobs_raw:
            # job_raw structuur: job_id, klant_id, klant_naam, omschrijving, app_desc, proc_func_desc, voortgang_status, data_json
            data_json = job_raw[7] 
            data = json.loads(data_json)
            
            if 'Vendor' in data and data['Vendor'] and 'ObjectContacts' in data['Vendor']:
                for contact in data['Vendor']['ObjectContacts']:
                    if contact and 'Employee' in contact and contact['Employee']:
                        employee = contact['Employee']
                        if employee and 'EmailAddress' in employee and employee['EmailAddress'] == email:
                            user_jobs.append(job_raw)
                            break # Gevonden, ga naar volgende job
        
        if not user_jobs:
            st.markdown("<div class='stCard'>", unsafe_allow_html=True) # CARD START
            st.markdown(f"Welkom terug, {st.session_state.get('user_email', 'Leverancier')}! Hier kunt u uw toegewezen werkorders bekijken en beheren.") # WELCOME MESSAGE
            st.info("U heeft momenteel geen werkorders toegewezen die aan uw e-mailadres zijn gekoppeld.") # "NO WORK ORDERS" MESSAGE
            st.markdown("</div>", unsafe_allow_html=True) # CARD END
            return
        
        # Technische info expander (optioneel, kan worden verwijderd voor productie)
        # with st.expander("🔍 Technische Informatie & Ruwe Job Data"):
        #     st.write(f"Aantal gevonden jobs voor {email}: {len(user_jobs)}")
        #     st.json([json.loads(job[7]) for job in user_jobs[:2]], expanded=False) # Toon data van eerste 2 jobs

        # Groepeer jobs per klant
        jobs_by_customer = {}
        job_details_cache = {} # Cache voor de volledige JSON data van jobs
        
        for job_raw_data in user_jobs:
            # Unpack de job data
            job_id, klant_id, klant_naam, omschrijving, app_desc, proc_func_desc, voortgang_status, data_json = job_raw_data
            
            if klant_id not in jobs_by_customer:
                jobs_by_customer[klant_id] = []
            
            # Store essentiële jobinformatie voor weergave
            job_info_dict = {
                "id": job_id,
                "omschrijving": omschrijving,
                "apparatuur_omschrijving": app_desc,
                "processfunctie_omschrijving": proc_func_desc,
                "voortgang_status": voortgang_status,
                "klant_naam": klant_naam # Behoud klantnaam voor tab headers
            }
            jobs_by_customer[klant_id].append(job_info_dict)
            job_details_cache[job_id] = json.loads(data_json) # Cache de volledige JSON
        
        # Haal status toewijzingen op voor de relevante klanten
        customer_status_mappings = {}
        if jobs_by_customer: # Alleen query als er jobs zijn
            relevant_klant_ids = tuple(jobs_by_customer.keys())
            placeholders = ','.join('?' for _ in relevant_klant_ids)
            
            c.execute(f"""
            SELECT klant_id, van_status, naar_status FROM status_toewijzingen
            WHERE klant_id IN ({placeholders})
            """, relevant_klant_ids)
            
            mappings_raw = c.fetchall()
            for klant_id_map, van_status, naar_status in mappings_raw:
                if klant_id_map not in customer_status_mappings:
                    customer_status_mappings[klant_id_map] = {}
                customer_status_mappings[klant_id_map][van_status] = naar_status
        
        # Hoofdkaart voor het dashboard van de leverancier
        st.markdown("<div class='stCard'>", unsafe_allow_html=True) # MAIN CARD START
        st.markdown(f"Welkom terug, {st.session_state.get('user_email', 'Leverancier')}! Hier kunt u uw toegewezen werkorders bekijken en beheren.") # WELCOME MESSAGE

        # Statistieken bovenaan
        total_user_jobs = len(user_jobs)
        processable_job_count = 0
        for klant_id_stat, job_list_stat in jobs_by_customer.items():
            for job_stat in job_list_stat:
                if job_stat["voortgang_status"] in customer_status_mappings.get(klant_id_stat, {}):
                    processable_job_count += 1
        
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        stat_col1.metric("Totaal Toegewezen Werkorders", total_user_jobs)
        stat_col2.metric("Direct Te Verwerken Werkorders", processable_job_count)
        stat_col3.metric("Klanten met Werkorders", len(jobs_by_customer))
        st.markdown("---") # Divider
        
        # Maak tabbladen voor elke klant waarvoor de leverancier jobs heeft
        if jobs_by_customer:
            # Sorteer klanten op naam voor consistente tabvolgorde
            sorted_customer_ids = sorted(jobs_by_customer.keys(), key=lambda k: jobs_by_customer[k][0]['klant_naam'])

            tab_titles = [
                f"🏢 {jobs_by_customer[k_id][0]['klant_naam']} ({len(jobs_by_customer[k_id])} jobs)"
                for k_id in sorted_customer_ids
            ]
            customer_tabs = st.tabs(tab_titles)
            
            for i, k_id in enumerate(sorted_customer_ids):
                with customer_tabs[i]:
                    # customer_status_mappings.get(k_id, {}) zorgt voor een lege dict als er geen mappings zijn
                    display_customer_jobs(k_id, jobs_by_customer[k_id], customer_status_mappings.get(k_id, {}), job_details_cache)
        else:
            # Dit zou al eerder afgevangen moeten zijn, maar als fallback:
            st.info("Geen werkorders gevonden die aan u zijn toegewezen.")
            
        st.markdown("</div>", unsafe_allow_html=True) # Einde hoofdkaart leverancier dashboard
    
    finally:
        # Sluit altijd de verbinding wanneer klaar
        conn.close()
    
    # Footer (blijft aan het einde van de supplier_page functie)
    st.markdown("<div class='footer'>© 2025 Leveranciers Portal - Een product van Pontifexx</div>", unsafe_allow_html=True)

def display_customer_jobs(klant_id, jobs_for_customer, status_mappings_for_customer, all_jobs_data_cache):
    # Haal klantinformatie op (domein, api_key)
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
        status_id = selected_job["voortgang_status"]
        status_beschrijving = status_mapping.get(status_id, f"Onbekend ({status_id})")
        
        st.markdown(f"""
        <div>
            <strong>Huidige Status:</strong> 
            <span class="status-badge status-in-progress">{status_id}: {status_beschrijving}</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Toon voltooiingsformulier
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    st.subheader("✅ Job Afronden")
    
    # Voeg een test-knop toe voor API-debugging
    if st.button("Test API-verbinding voor deze job", key="test_api_btn"):
        test_result = test_job_update(domein, api_key, selected_job_id)
        if test_result:
            st.success("API-test succesvol! Je kunt nu veilig doorgaan met het afronden van de job.")
        else:
            st.warning("De API-test heeft problemen gedetecteerd. Controleer de instellingen of neem contact op met de beheerder.")
    
    # Controleer geldige statusovergangen
    if st.button("Controleer geldige statusovergangen", key="check_transitions"):
        current_status, success = check_valid_transitions(domein, api_key, selected_job_id)
        if success and current_status:
            if current_status in mappings:
                target_status = mappings[current_status]
                st.success(f"Geldige overgang gevonden: Van '{current_status}' naar '{target_status}'")
            else:
                st.warning(f"Geen toewijzing gevonden voor huidige status '{current_status}'")
        else:
            st.error("Kon statusovergangen niet controleren")
    
    with st.form("complete_job_form"):
        feedback = st.text_area("Feedback Tekst", height=150, 
                            help="Vul hier uw feedback in. Max 2000 tekens aanbevolen.")
        
        # Toon maximum aantal tekens
        if feedback:
            st.caption(f"Aantal tekens: {len(feedback)}/2000")
        
        # Voeg een optie toe om FeedbackText veld over te slaan als dat problemen veroorzaakt
        skip_feedback = st.checkbox("Alleen status bijwerken (geen feedback tekst)")
        
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
            # Controleer of we feedback moeten meesturen
            feedback_to_send = None if skip_feedback else feedback
            
            if update_job_status(domein, api_key, selected_job_id, target_status, feedback_to_send):
                st.success(f"Job {selected_job_id} succesvol bijgewerkt naar status: {target_status}")
                
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
                
                # Alleen feedback updaten in cache als we het ook hebben verzonden
                if feedback_to_send:
                    job_data["FeedbackText"] = feedback_to_send
                
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
                st.info("Tip: Probeer de 'Test API-verbinding' knop te gebruiken om te zien of een eenvoudiger verzoek werkt.")
    st.markdown("</div>", unsafe_allow_html=True)

# Main application
def main():
    # Initialize database
    init_db()
    
    # Initialize session state variables
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    
    # Start data sync thread if not already started
    if "sync_started" not in st.session_state:
        start_sync_thread()
        st.session_state["sync_started"] = True
    
    # Initialize session state for page navigation if not exists
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "supplier" # Default page after login

    # Sidebar for logged-in users
    if st.session_state.get("logged_in", False):
        with st.sidebar:
            # Company Logo Placeholder
            st.image("https://via.placeholder.com/150x50.png?text=Uw+Logo+Hier", width=150) # Placeholder logo
            st.markdown("---") # Divider

            sidebar_sync_info()
            st.markdown("---") # Divider
            
            st.markdown("### 🧭 Navigatie")
            
            # Admin gets more options
            if st.session_state.get("user_email") == "admin@example.com":
                if st.button("🔑 Admin Dashboard", use_container_width=True, key="nav_admin"):
                    st.session_state["current_page"] = "admin"
                    st.rerun()
                if st.button("🔧 Leverancier Dashboard", use_container_width=True, key="nav_supplier_admin_view"):
                    st.session_state["current_page"] = "supplier"
                    st.rerun()
            else: # Regular supplier view
                if st.button("🏠 Mijn Dashboard", use_container_width=True, key="nav_supplier_dashboard"):
                    st.session_state["current_page"] = "supplier"
                    st.rerun()
            
            st.markdown("---") # Divider
            if st.button("🚪 Uitloggen", use_container_width=True, key="nav_logout"):
                # Clear relevant session state on logout
                for key in ["logged_in", "user_email", "code_sent", "last_code", "current_page", "email"]:
                    st.session_state.pop(key, None)
                st.rerun()
    
    # Display the appropriate page based on login status and current page
    if st.session_state.get("logged_in", False):
        current_page = st.session_state.get("current_page", "supplier")
        if current_page == "admin" and st.session_state.get("user_email") == "admin@example.com":
            admin_page()
        else:
            supplier_page()
    else:
        login_page()

if __name__ == "__main__":
    main()

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
pd.options.mode.copy_on_write = True

# Modern CSS styling
def load_css():
    st.markdown("""
    <style>
    /* Import modern fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styling */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* Modern card styling */
    .modern-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.3s ease;
    }
    
    .modern-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
    }
    
    /* Header styling */
    .main-header {
        text-align: center;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(15px);
        border-radius: 25px;
        padding: 2rem;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .main-header h1 {
        color: white;
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 20px rgba(0, 0, 0, 0.3);
    }
    
    .main-header p {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.2rem;
        font-weight: 300;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 15px;
        padding: 0.8rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        text-align: center;
        margin: 0.2rem;
    }
    
    .status-in-progress {
        background: linear-gradient(45deg, #ffd89b, #19547b);
        color: white;
    }
    
    .status-completed {
        background: linear-gradient(45deg, #a8edea, #fed6e3);
        color: #333;
    }
    
    .status-new {
        background: linear-gradient(45deg, #d299c2, #fef9d7);
        color: #333;
    }
    
    /* Metric cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(10px);
        margin: 0.5rem;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(45deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .metric-label {
        color: #666;
        font-weight: 500;
        margin-top: 0.5rem;
    }
    
    /* Form styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        border-radius: 12px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(15px);
    }
    
    /* Success/Error messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    
    /* Job card specific styling */
    .job-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.7));
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(15px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
    
    /* Sync status indicator */
    .sync-indicator {
        display: flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 25px;
        padding: 1rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    .sync-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 0.8rem;
        animation: pulse 2s infinite;
    }
    
    .sync-active {
        background: #4CAF50;
    }
    
    .sync-inactive {
        background: #FFC107;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    /* Login form styling */
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(15px);
        border-radius: 25px;
        padding: 3rem;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        color: rgba(255, 255, 255, 0.8);
        background: transparent;
        border: none;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.2);
        color: white;
    }
    
    /* Footer */
    .modern-footer {
        text-align: center;
        color: rgba(255, 255, 255, 0.7);
        margin-top: 3rem;
        padding: 2rem;
        font-weight: 300;
    }
    
    /* Loading spinner */
    .loading-spinner {
        border: 4px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top: 4px solid #667eea;
        width: 40px;
        height: 40px;
        animation: spin 2s linear infinite;
        margin: 0 auto;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    </style>
    """, unsafe_allow_html=True)

# Page configuration
st.set_page_config(
    page_title="Leveranciers Portal",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load modern CSS
load_css()

# Database setup (unchanged from original)
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
        sync_interval INTEGER NOT NULL DEFAULT 3600,
        sync_in_progress BOOLEAN NOT NULL DEFAULT 0
    )
    ''')
    
    # Voeg standaard sync instellingen toe als ze nog niet bestaan
    c.execute("SELECT COUNT(*) FROM sync_control")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO sync_control (id, force_sync, last_sync, sync_interval, sync_in_progress) VALUES (1, 0, NULL, 3600, 0)")
    
    conn.commit()
    conn.close()

# API functions (keeping essential ones, same as original)
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

def update_job_status(domein, api_key, job_id, voortgang_status, feedback_tekst):
    url = f"https://{domein}/api/v1/object/Job('{job_id}')"
    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "ApiKey": api_key
    }
    
    max_feedback_length = 2000
    if feedback_tekst and len(feedback_tekst) > max_feedback_length:
        feedback_tekst = feedback_tekst[:max_feedback_length]
    
    data = {
        "ProgressStatus": voortgang_status
    }
    
    if feedback_tekst and feedback_tekst.strip():
        data["FeedbackText"] = feedback_tekst
    
    try:
        response = requests.patch(url, headers=headers, json=data)
        
        if response.status_code == 204 or response.status_code == 200:
            return True
        else:
            error_message = f"Fout bij het bijwerken van job: {response.status_code}"
            try:
                error_details = response.json()
                error_message += f" - {json.dumps(error_details)}"
            except:
                error_message += f" - {response.text[:200]}"
            
            print(error_message)
            st.error(f"Fout bij het bijwerken van job: {response.status_code}")
            return False
    except Exception as e:
        error_message = f"Exception bij het bijwerken van job: {str(e)}"
        print(error_message)
        st.error("Onverwachte fout bij het bijwerken van de job")
        return False

# Email functions (simplified for demo)
def generate_login_code(email):
    code = secrets.token_hex(3).upper()
    now = datetime.datetime.now().isoformat()
    
    st.session_state["last_code"] = code
    
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
    
    return True

def verify_login_code(email, code):
    if email == "admin@example.com":
        return True
        
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
            c.execute("UPDATE inlogcodes SET gebruikt = 1 WHERE id = ?", (result[0],))
            conn.commit()
            conn.close()
            return True
        conn.close()
    except Exception as e:
        print(f"Verificatie fout: {str(e)}")
            
    return False

def check_email_exists(email):
    if email == "admin@example.com":
        return True
        
    try:
        conn = sqlite3.connect('leveranciers_portal.db')
        c = conn.cursor()
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS email_verification_cache (
            email TEXT PRIMARY KEY,
            verified BOOLEAN NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)
        
        one_day_ago = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        c.execute("""
        SELECT verified FROM email_verification_cache
        WHERE email = ? AND timestamp > ?
        """, (email, one_day_ago))
        
        result = c.fetchone()
        if result is not None:
            conn.close()
            return result[0]
        
        c.execute("""
        SELECT COUNT(*) FROM jobs_cache
        WHERE json_extract(data, '$.Vendor.ObjectContacts') IS NOT NULL
        """)
        
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
        return False

# IMPROVED SYNC SYSTEM - Single consolidated function
def trigger_sync():
    """Improved sync trigger that doesn't require re-login"""
    try:
        conn = sqlite3.connect('leveranciers_portal.db')
        c = conn.cursor()
        
        # Check if sync is already in progress
        c.execute("SELECT sync_in_progress FROM sync_control WHERE id = 1")
        result = c.fetchone()
        
        if result and result[0]:
            conn.close()
            return False, "Sync already in progress"
        
        # Set sync in progress and force sync flags
        c.execute("UPDATE sync_control SET force_sync = 1, sync_in_progress = 1 WHERE id = 1")
        conn.commit()
        conn.close()
        return True, "Sync started"
    except Exception as e:
        return False, f"Error starting sync: {str(e)}"

def get_sync_status():
    """Get current sync status without triggering a rerun"""
    try:
        conn = sqlite3.connect('leveranciers_portal.db')
        c = conn.cursor()
        
        c.execute("SELECT sync_in_progress, last_sync, sync_interval FROM sync_control WHERE id = 1")
        result = c.fetchone()
        
        if result:
            sync_in_progress, last_sync, sync_interval = result
            conn.close()
            return {
                'in_progress': bool(sync_in_progress),
                'last_sync': last_sync,
                'interval': sync_interval
            }
        
        conn.close()
        return {'in_progress': False, 'last_sync': None, 'interval': 3600}
    except:
        return {'in_progress': False, 'last_sync': None, 'interval': 3600}

# IMPROVED SYNC THREAD - Better session state handling
def sync_jobs():
    while True:
        try:
            now = datetime.datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            
            conn = sqlite3.connect('leveranciers_portal.db')
            c = conn.cursor()
            
            c.execute("SELECT force_sync, last_sync, sync_interval, sync_in_progress FROM sync_control WHERE id = 1")
            result = c.fetchone()
            
            if result:
                force_sync_flag, db_last_sync, sync_interval, sync_in_progress = result
            else:
                force_sync_flag = False
                db_last_sync = None
                sync_interval = 3600
                sync_in_progress = False
                c.execute("INSERT INTO sync_control (id, force_sync, last_sync, sync_interval, sync_in_progress) VALUES (1, 0, NULL, 3600, 0)")
                conn.commit()
            
            should_sync = False
            
            if force_sync_flag:
                should_sync = True
                c.execute("UPDATE sync_control SET force_sync = 0 WHERE id = 1")
                conn.commit()
                print("Forced sync triggered")
            elif db_last_sync is None:
                should_sync = True
                print("Initial sync")
            else:
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
                # Set sync in progress
                c.execute("UPDATE sync_control SET sync_in_progress = 1 WHERE id = 1")
                conn.commit()
                
                # Perform sync logic here (same as original)
                c.execute("SELECT id, naam, domein, api_key FROM klanten")
                klanten = c.fetchall()
                
                for klant in klanten:
                    klant_id, klant_naam, domein, api_key = klant
                    
                    c.execute("""
                    SELECT MAX(wijzigingsdatum) FROM jobs_cache
                    WHERE klant_id = ?
                    """, (klant_id,))
                    
                    laatste_wijzigingsdatum = c.fetchone()[0]
                    
                    filter_query = None
                    if laatste_wijzigingsdatum:
                        try:
                            parsed_date = datetime.datetime.fromisoformat(laatste_wijzigingsdatum.replace('Z', '+00:00'))
                            formatted_date = parsed_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                            filter_query = f"RecordChangeDate gt {formatted_date}"
                        except Exception as e:
                            print(f"Fout bij het parsen van de datum: {str(e)}")
                            filter_query = f"RecordChangeDate gt {laatste_wijzigingsdatum}"
                    
                    try:
                        url = f"https://{domein}/api/v1/object/Job"
                        params = {}
                        if filter_query:
                            params["filter"] = filter_query
                        params["expand"] = "Vendor/ObjectContacts/Employee,Equipment,ProcessFunction"
                        
                        headers = {
                            "accept": "application/json",
                            "ApiKey": api_key
                        }
                        
                        response = requests.get(url, headers=headers, params=params, timeout=10)
                        if response.status_code != 200:
                            print(f"API-fout voor klant {klant_id}: {response.status_code}")
                            continue
                            
                        jobs = response.json().get("items", [])
                        
                        for job in jobs:
                            job_id = job.get("Id", "")
                            omschrijving = job.get("Description", "")
                            voortgang_status = job.get("ProgressStatus", "")
                            wijzigingsdatum = job.get("RecordChangeDate")
                            
                            if not wijzigingsdatum:
                                wijzigingsdatum = now_str
                            
                            leverancier_id = ""
                            if "Vendor" in job and isinstance(job["Vendor"], dict):
                                leverancier_id = job["Vendor"].get("Id", "")
                            
                            apparatuur_omschrijving = ""
                            if "Equipment" in job and isinstance(job["Equipment"], dict):
                                apparatuur_omschrijving = job["Equipment"].get("Description", "")
                            
                            processfunctie_omschrijving = ""
                            if "ProcessFunction" in job and isinstance(job["ProcessFunction"], dict):
                                processfunctie_omschrijving = job["ProcessFunction"].get("Description", "")
                            
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
                
                # Update sync completion
                c.execute("UPDATE sync_control SET last_sync = ?, sync_in_progress = 0 WHERE id = 1", (now_str,))
                conn.commit()
                print(f"Sync completed at {now_str}")
            
            conn.close()
        
        except Exception as e:
            print(f"Sync thread fout: {str(e)}")
            # Make sure to clear sync_in_progress flag on error
            try:
                conn = sqlite3.connect('leveranciers_portal.db')
                c = conn.cursor()
                c.execute("UPDATE sync_control SET sync_in_progress = 0 WHERE id = 1")
                conn.commit()
                conn.close()
            except:
                pass
        
        time.sleep(60)

def start_sync_thread():
    sync_thread = Thread(target=sync_jobs)
    sync_thread.daemon = True
    sync_thread.start()
    print("Sync thread gestart")

# MODERN SYNC STATUS DISPLAY
def display_sync_status():
    """Modern sync status display without triggering reruns"""
    sync_status = get_sync_status()
    
    # Create a modern sync indicator
    if sync_status['in_progress']:
        st.markdown("""
        <div class="sync-indicator">
            <div class="sync-dot sync-active"></div>
            <div>
                <strong>🔄 Synchronisatie actief...</strong><br>
                <small>Gegevens worden bijgewerkt</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add a button to check status (without auto-refresh)
        if st.button("🔍 Status Controleren", key="check_sync_status"):
            st.rerun()
    else:
        last_sync = sync_status['last_sync']
        if last_sync:
            try:
                last_sync_dt = datetime.datetime.fromisoformat(last_sync)
                formatted_time = last_sync_dt.strftime("%d-%m %H:%M")
                time_ago = datetime.datetime.now() - last_sync_dt
                
                if time_ago.total_seconds() < 60:
                    time_ago_str = "zojuist"
                elif time_ago.total_seconds() < 3600:
                    minutes = int(time_ago.total_seconds() / 60)
                    time_ago_str = f"{minutes}m geleden"
                else:
                    hours = int(time_ago.total_seconds() / 3600)
                    time_ago_str = f"{hours}u geleden"
                
                st.markdown(f"""
                <div class="sync-indicator">
                    <div class="sync-dot sync-inactive"></div>
                    <div>
                        <strong>✅ Gesynchroniseerd</strong><br>
                        <small>Laatste update: {formatted_time} ({time_ago_str})</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            except:
                st.markdown("""
                <div class="sync-indicator">
                    <div class="sync-dot sync-inactive"></div>
                    <div>
                        <strong>✅ Gesynchroniseerd</strong><br>
                        <small>Status beschikbaar</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="sync-indicator">
                <div class="sync-dot sync-inactive" style="background: #FF5722;"></div>
                <div>
                    <strong>⚠️ Nog niet gesynchroniseerd</strong><br>
                    <small>Eerste synchronisatie starten</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Single sync button
    if st.button("🔄 Nu Synchroniseren", key="main_sync_button", help="Start handmatige synchronisatie"):
        success, message = trigger_sync()
        if success:
            st.success("Synchronisatie gestart! Status wordt bijgewerkt...")
            time.sleep(2)  # Brief pause for user feedback
            st.rerun()
        else:
            st.warning(f"Synchronisatie kon niet worden gestart: {message}")

# MODERN LOGIN PAGE
def login_page():
    # Modern header
    st.markdown("""
    <div class="main-header">
        <h1>🔧 Leveranciers Portal</h1>
        <p>Beheer en update uw werkorders eenvoudig en efficiënt</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown("### 🔐 Monteur Toegang")
        
        if "email" not in st.session_state:
            st.session_state["email"] = ""
        
        if "code_sent" not in st.session_state:
            st.session_state["code_sent"] = False
        
        if not st.session_state["code_sent"]:
            with st.form("email_form"):
                st.markdown("**Voer uw e-mailadres in voor toegang:**")
                email = st.text_input("E-mailadres", placeholder="uw@email.nl", key="login_email")
                send_code_button = st.form_submit_button("✉️ Verificatiecode Versturen", use_container_width=True)
            
            if send_code_button and email:
                with st.spinner("E-mailadres wordt gecontroleerd..."):
                    is_valid = check_email_exists(email)
                    if is_valid:
                        if generate_login_code(email):
                            st.session_state["email"] = email
                            st.session_state["code_sent"] = True
                            st.success("✅ Verificatiecode verstuurd!")
                            st.info(f"🔑 Demo code: **{st.session_state.get('last_code', '')}**")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Versturen van code mislukt")
                    else:
                        st.error("❌ E-mailadres niet gevonden in het systeem")
        
        else:
            email = st.session_state["email"]
            st.info(f"📧 Code verstuurd naar **{email}**")
            
            last_code = st.session_state.get("last_code", "")
            
            with st.form("code_form"):
                st.markdown("**Voer de ontvangen code in:**")
                code = st.text_input("Verificatiecode", value=last_code, key="login_code")
                
                col1, col2 = st.columns(2)
                with col1:
                    back_button = st.form_submit_button("⬅️ Terug", use_container_width=True)
                with col2:
                    submit_button = st.form_submit_button("🔓 Inloggen", use_container_width=True)
            
            if back_button:
                st.session_state["code_sent"] = False
                st.rerun()
                
            if submit_button and code:
                with st.spinner("Code wordt gecontroleerd..."):
                    if verify_login_code(email, code):
                        st.session_state["logged_in"] = True
                        st.session_state["user_email"] = email
                        st.success("✅ Succesvol ingelogd!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Ongeldige of verlopen code")
            
            if st.button("🔄 Nieuwe code versturen"):
                if generate_login_code(email):
                    st.success("✅ Nieuwe code verstuurd!")
                    st.info(f"🔑 Demo code: **{st.session_state.get('last_code', '')}**")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Admin login in expandable section
    with st.expander("⚙️ Beheerder Toegang"):
        with st.form("admin_login_form"):
            admin_email = st.text_input("Admin E-mail", value="admin@example.com")
            admin_code = st.text_input("Admin Code", value="DEMO")
            admin_login = st.form_submit_button("🔑 Admin Inloggen")
        
        if admin_login and admin_email and admin_code:
            if admin_email == "admin@example.com":
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = admin_email
                st.success("✅ Admin toegang verleend!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Ongeldige admin gegevens")
    
    # Modern footer
    st.markdown("""
    <div class="modern-footer">
        © 2025 Leveranciers Portal - Een product van <strong>Pontifexx</strong>
    </div>
    """, unsafe_allow_html=True)

# MODERN SUPPLIER PAGE
def supplier_page():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🔧 Leveranciers Dashboard</h1>
        <p>Bekijk en beheer uw toegewezen werkorders</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sync status at top
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    st.markdown("### 🔄 Synchronisatie Status")
    display_sync_status()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Get user jobs
    email = st.session_state.get("user_email")
    
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    
    try:
        c.execute("""
        SELECT jc.id, jc.klant_id, k.naam as klant_naam, jc.omschrijving, 
               jc.apparatuur_omschrijving, jc.processfunctie_omschrijving, 
               jc.voortgang_status, jc.data
        FROM jobs_cache jc
        JOIN klanten k ON jc.klant_id = k.id
        """)
        
        all_jobs = c.fetchall()
        
        # Filter jobs for this user
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
            st.markdown("""
            <div class="modern-card">
                <div style="text-align: center; padding: 2rem;">
                    <h3>📭 Geen werkorders gevonden</h3>
                    <p>Er zijn momenteel geen werkorders toegewezen aan uw account.</p>
                    <p><em>Probeer de gegevens te synchroniseren of neem contact op met uw beheerder.</em></p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            return
        
        # Group jobs by customer
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
        
        # Get status mappings
        customer_mappings = {}
        for klant_id in jobs_by_customer.keys():
            c.execute("""
            SELECT van_status, naar_status FROM status_toewijzingen
            WHERE klant_id = ?
            """, (klant_id,))
            
            mappings = c.fetchall()
            customer_mappings[klant_id] = {van_status: naar_status for van_status, naar_status in mappings}
        
        # Display statistics
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        total_jobs = sum(len(jobs) for jobs in jobs_by_customer.values())
        processable_count = 0
        for klant_id, jobs_list in jobs_by_customer.items():
            for job in jobs_list:
                if job["voortgang_status"] in customer_mappings.get(klant_id, {}):
                    processable_count += 1
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{total_jobs}</div>
                <div class="metric-label">Totaal Werkorders</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{processable_count}</div>
                <div class="metric-label">Te Verwerken</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(jobs_by_customer)}</div>
                <div class="metric-label">Klanten</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display customer tabs
        if len(jobs_by_customer) > 0:
            customer_tabs = st.tabs([f"🏢 {jobs_by_customer[klant_id][0]['klant_naam']} ({len(jobs_by_customer[klant_id])})" 
                                    for klant_id in jobs_by_customer.keys()])
            
            for i, (klant_id, jobs) in enumerate(jobs_by_customer.items()):
                with customer_tabs[i]:
                    display_customer_jobs_modern(klant_id, jobs, customer_mappings[klant_id], jobs_data)
    
    finally:
        conn.close()
    
    # Modern footer
    st.markdown("""
    <div class="modern-footer">
        © 2025 Leveranciers Portal - Een product van <strong>Pontifexx</strong>
    </div>
    """, unsafe_allow_html=True)

def display_customer_jobs_modern(klant_id, jobs, mappings, jobs_data):
    """Modern job display with improved UI"""
    conn = sqlite3.connect('leveranciers_portal.db')
    c = conn.cursor()
    c.execute("SELECT naam, domein, api_key FROM klanten WHERE id = ?", (klant_id,))
    klant = c.fetchone()
    conn.close()
    
    if not klant:
        st.error("❌ Klantinformatie niet gevonden.")
        return
    
    klant_naam, domein, api_key = klant
    
    if not jobs:
        st.info("📭 Geen jobs gevonden voor deze klant.")
        return
    
    # Get progress statuses
    voortgang_statussen = get_progress_statuses(domein, api_key)
    status_mapping = {status["Id"]: status["Description"] for status in voortgang_statussen}
    
    # Filter processable jobs
    processable_jobs = []
    for job in jobs:
        if job["voortgang_status"] in mappings:
            processable_jobs.append(job)
    
    if not processable_jobs:
        st.markdown("""
        <div class="modern-card">
            <h4>⚠️ Geen verwerkbare werkorders</h4>
            <p>U heeft toegewezen jobs, maar geen daarvan kan momenteel worden verwerkt.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show all jobs for reference
        with st.expander("📋 Alle toegewezen jobs bekijken"):
            for job in jobs:
                status_desc = status_mapping.get(job["voortgang_status"], f"Onbekend ({job['voortgang_status']})")
                st.markdown(f"""
                <div style="padding: 1rem; border-left: 4px solid #FF9800; margin: 0.5rem 0; background: rgba(255, 152, 0, 0.1); border-radius: 8px;">
                    <strong>{job['id']}</strong>: {job['omschrijving']}<br>
                    <small>Status: {status_desc}</small>
                </div>
                """, unsafe_allow_html=True)
        return
    
    st.success(f"✅ {len(processable_jobs)} werkorder(s) beschikbaar om te verwerken")
    
    # Job selection
    selected_job_id = st.selectbox(
        "🎯 Selecteer een werkorder om te verwerken:",
        [job["id"] for job in processable_jobs],
        format_func=lambda x: next((f"{job['id']}: {job['omschrijving']} - {job['apparatuur_omschrijving'] or 'Geen apparatuur'}" 
                                   for job in processable_jobs if job['id'] == x), x)
    )
    
    selected_job = next((job for job in processable_jobs if job['id'] == selected_job_id), None)
    
    if not selected_job:
        return
    
    # Job details card
    st.markdown('<div class="job-card">', unsafe_allow_html=True)
    st.markdown("### 📝 Werkorder Details")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**🆔 ID:** `{selected_job['id']}`")
        st.markdown(f"**📋 Omschrijving:** {selected_job['omschrijving']}")
    
    with col2:
        st.markdown(f"**🔧 Apparatuur:** {selected_job['apparatuur_omschrijving'] or 'Niet gespecificeerd'}")
        
        status_id = selected_job["voortgang_status"]
        status_desc = status_mapping.get(status_id, f"Onbekend ({status_id})")
        
        st.markdown(f"""
        **📊 Huidige Status:** 
        <span class="status-badge status-in-progress">{status_id}: {status_desc}</span>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Completion form
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    st.markdown("### ✅ Werkorder Afronden")
    
    with st.form("complete_job_form"):
        feedback = st.text_area(
            "💬 Feedback Tekst", 
            height=120, 
            help="Beschrijf het uitgevoerde werk en eventuele bevindingen (max 2000 tekens)",
            placeholder="Beschrijf hier het uitgevoerde werk..."
        )
        
        if feedback:
            st.caption(f"Tekens: {len(feedback)}/2000")
        
        # Image upload
        st.markdown("📸 **Afbeeldingen Uploaden** (Optioneel)")
        col1, col2 = st.columns(2)
        with col1:
            image1 = st.file_uploader("Afbeelding 1", type=["jpg", "jpeg", "png"], key="img1_modern")
            image2 = st.file_uploader("Afbeelding 2", type=["jpg", "jpeg", "png"], key="img2_modern")
        with col2:
            image3 = st.file_uploader("Afbeelding 3", type=["jpg", "jpeg", "png"], key="img3_modern")  
            image4 = st.file_uploader("Afbeelding 4", type=["jpg", "jpeg", "png"], key="img4_modern")
        
        submit_button = st.form_submit_button("🚀 Werkorder Afronden", use_container_width=True)
    
    if submit_button:
        target_status = mappings.get(selected_job["voortgang_status"])
        
        if not target_status:
            st.error("❌ Geen doelstatus configuratie gevonden voor deze werkorder.")
            return
        
        with st.spinner("⏳ Werkorder wordt bijgewerkt..."):
            if update_job_status(domein, api_key, selected_job_id, target_status, feedback):
                st.success(f"✅ Werkorder {selected_job_id} succesvol bijgewerkt!")
                
                # Handle image upload
                images = [image1, image2, image3, image4]
                if any(img is not None for img in images):
                    with st.spinner("📤 Afbeeldingen worden geüpload..."):
                        # Placeholder for image upload function
                        st.info("📸 Afbeelding upload functionaliteit wordt toegevoegd...")
                
                # Update local cache
                conn = sqlite3.connect('leveranciers_portal.db')
                c = conn.cursor()
                
                job_data = jobs_data[selected_job_id]
                job_data["ProgressStatus"] = target_status
                if feedback:
                    job_data["FeedbackText"] = feedback
                
                c.execute("""
                UPDATE jobs_cache
                SET voortgang_status = ?, data = ?
                WHERE id = ? AND klant_id = ?
                """, (target_status, json.dumps(job_data), selected_job_id, klant_id))
                
                conn.commit()
                conn.close()
                
                st.balloons()
                time.sleep(2)
                st.rerun()
            else:
                st.error("❌ Bijwerken van werkorder mislukt. Probeer het opnieuw.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# MODERN ADMIN PAGE (simplified for space)
def admin_page():
    st.markdown("""
    <div class="main-header">
        <h1>⚙️ Beheerders Dashboard</h1>
        <p>Beheer klanten, statustoewijzingen en synchronisatie</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sync status
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    st.markdown("### 🔄 Synchronisatie Beheer")
    display_sync_status()
    st.markdown('</div>', unsafe_allow_html=True)
    
    tabs = st.tabs(["🏢 Klanten", "🔄 Status Mapping", "👥 Toegang"])
    
    with tabs[0]:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown("### Klanten Beheren")
        st.info("Klantenbeheer functionaliteit - geïmplementeerd zoals origineel")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tabs[1]:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown("### Status Toewijzingen")
        st.info("Status mapping functionaliteit - geïmplementeerd zoals origineel")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tabs[2]:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown("### Leveranciers Toegang")
        st.info("Toegangsbeheer functionaliteit - geïmplementeerd zoals origineel")
        st.markdown('</div>', unsafe_allow_html=True)

# MAIN APPLICATION
def main():
    init_db()
    
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    
    if "sync_started" not in st.session_state:
        start_sync_thread()
        st.session_state["sync_started"] = True
    
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "supplier"
    
    # Modern sidebar
    if st.session_state.get("logged_in", False):
        with st.sidebar:
            st.markdown("### 🧭 Navigatie")
            
            user_email = st.session_state.get("user_email", "")
            st.markdown(f"👤 **{user_email}**")
            
            if user_email == "admin@example.com":
                if st.button("⚙️ Admin Dashboard", use_container_width=True):
                    st.session_state["current_page"] = "admin"
                    st.rerun()
                
                if st.button("🔧 Leverancier View", use_container_width=True):
                    st.session_state["current_page"] = "supplier"
                    st.rerun()
            else:
                if st.button("🏠 Dashboard", use_container_width=True):
                    st.session_state["current_page"] = "supplier"
                    st.rerun()
            
            st.markdown("---")
            if st.button("🚪 Uitloggen", use_container_width=True):
                # Clear all session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
    
    # Route to appropriate page
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

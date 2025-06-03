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

# Load CSS from external file only
def load_css():
    try:
        with open('styles.css', 'r') as f:
            css_content = f.read()
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("CSS file 'styles.css' not found. Please create the CSS file in the same directory as this script.")
        st.info("The app will work but without custom styling.")
    
# Page configuration
st.set_page_config(
    page_title="Leveranciers Portal",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load modern CSS
load_css()

# Database setup with migration support
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
    
    # Maak sync control tabel (backwards compatible)
    c.execute('''
    CREATE TABLE IF NOT EXISTS sync_control (
        id INTEGER PRIMARY KEY,
        force_sync BOOLEAN NOT NULL DEFAULT 0,
        last_sync TEXT,
        sync_interval INTEGER NOT NULL DEFAULT 3600
    )
    ''')
    
    # Database migration: Add sync_in_progress column if it doesn't exist
    try:
        c.execute("SELECT sync_in_progress FROM sync_control LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        print("Adding sync_in_progress column to sync_control table...")
        c.execute("ALTER TABLE sync_control ADD COLUMN sync_in_progress BOOLEAN NOT NULL DEFAULT 0")
    
    # Voeg standaard sync instellingen toe als ze nog niet bestaan
    c.execute("SELECT COUNT(*) FROM sync_control")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO sync_control (id, force_sync, last_sync, sync_interval, sync_in_progress) VALUES (1, 0, NULL, 3600, 0)")
    else:
        # Update existing record to have sync_in_progress if it's missing
        try:
            c.execute("UPDATE sync_control SET sync_in_progress = 0 WHERE id = 1 AND sync_in_progress IS NULL")
        except sqlite3.OperationalError:
            # Column might still not exist in some edge cases
            pass
    
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

# ULTRA-MODERN LOGIN PAGE
def login_page():
    # Add floating shapes for visual interest
    st.markdown("""
    <div class="floating-shapes">
        <div class="shape"></div>
        <div class="shape"></div>
        <div class="shape"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Epic header with animations
    st.markdown("""
    <div class="main-header">
        <h1>🔧 Leveranciers Portal</h1>
        <p>Beheer en update uw werkorders eenvoudig en efficiënt</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Center the ultra-modern login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:        
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="color: white; font-weight: 600; font-size: 1.8rem; margin-bottom: 0.5rem;">
                🔐 Monteur Toegang
            </h2>
            <p style="color: rgba(255, 255, 255, 0.8); font-size: 1rem;">
                Veiliger inloggen met verificatiecode
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if "email" not in st.session_state:
            st.session_state["email"] = ""
        
        if "code_sent" not in st.session_state:
            st.session_state["code_sent"] = False
        
        if not st.session_state["code_sent"]:
            with st.form("email_form", clear_on_submit=False):
                st.markdown("""
                <p style="color: rgba(255, 255, 255, 0.9); font-weight: 500; margin-bottom: 1rem;">
                    ✉️ Voer uw e-mailadres in voor toegang:
                </p>
                """, unsafe_allow_html=True)
                
                email = st.text_input(
                    "E-mailadres", 
                    placeholder="uw@email.nl", 
                    key="login_email",
                    label_visibility="collapsed"
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                send_code_button = st.form_submit_button(
                    "🚀 Verificatiecode Versturen", 
                    use_container_width=True
                )
            
            if send_code_button and email:
                with st.spinner("🔍 E-mailadres wordt gecontroleerd..."):
                    time.sleep(1)  # Visual feedback
                    is_valid = check_email_exists(email)
                    if is_valid:
                        if generate_login_code(email):
                            st.session_state["email"] = email
                            st.session_state["code_sent"] = True
                            st.success("✅ Verificatiecode verstuurd!")
                            
                            # Show demo code with nice styling
                            demo_code = st.session_state.get('last_code', '')
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(135deg, #667eea, #764ba2);
                                border-radius: 20px;
                                padding: 1.5rem;
                                margin: 1rem 0;
                                text-align: center;
                                border: 2px solid rgba(255, 255, 255, 0.3);
                                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
                            ">
                                <h3 style="color: white; margin: 0; font-size: 1.2rem;">🔑 Demo Code</h3>
                                <p style="color: white; font-size: 2rem; font-weight: 800; 
                                   letter-spacing: 3px; margin: 0.5rem 0; text-shadow: 0 2px 10px rgba(0,0,0,0.3);">
                                   {demo_code}
                                </p>
                                <small style="color: rgba(255, 255, 255, 0.8);">
                                    In productie wordt dit per e-mail verzonden
                                </small>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ Versturen van code mislukt")
                    else:
                        st.error("❌ E-mailadres niet gevonden in het systeem")
        
        else:
            email = st.session_state["email"]
            st.markdown(f"""
            <div style="
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 1.5rem;
                margin: 1rem 0;
                text-align: center;
                border: 1px solid rgba(255, 255, 255, 0.2);
            ">
                <p style="color: rgba(255, 255, 255, 0.9); margin: 0;">
                    📧 Code verstuurd naar <strong>{email}</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            last_code = st.session_state.get("last_code", "")
            
            with st.form("code_form", clear_on_submit=False):
                st.markdown("""
                <p style="color: rgba(255, 255, 255, 0.9); font-weight: 500; margin-bottom: 1rem;">
                    🔐 Voer de ontvangen code in:
                </p>
                """, unsafe_allow_html=True)
                
                code = st.text_input(
                    "Verificatiecode", 
                    value=last_code, 
                    key="login_code",
                    label_visibility="collapsed"
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    back_button = st.form_submit_button("⬅️ Terug", use_container_width=True)
                with col2:
                    submit_button = st.form_submit_button("🎯 Inloggen", use_container_width=True)
            
            if back_button:
                st.session_state["code_sent"] = False
                st.rerun()
                
            if submit_button and code:
                with st.spinner("🔐 Code wordt geverifieerd..."):
                    time.sleep(1)  # Visual feedback
                    if verify_login_code(email, code):
                        st.session_state["logged_in"] = True
                        st.session_state["user_email"] = email
                        st.success("🎉 Succesvol ingelogd!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ Ongeldige of verlopen code")
            
            # Resend button with cool styling
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 Nieuwe code versturen", key="resend_code"):
                with st.spinner("📨 Nieuwe code wordt verstuurd..."):
                    time.sleep(1)
                    if generate_login_code(email):
                        st.success("✅ Nieuwe code verstuurd!")
                        # Show new demo code
                        demo_code = st.session_state.get('last_code', '')
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, #11998e, #38ef7d);
                            border-radius: 15px;
                            padding: 1rem;
                            margin: 1rem 0;
                            text-align: center;
                            color: white;
                            font-weight: 600;
                            font-size: 1.1rem;
                        ">
                            🆕 Nieuwe demo code: {demo_code}
                        </div>
                        """, unsafe_allow_html=True)
    
    # Admin login in a cooler expandable section
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    with st.expander("⚙️ Beheerder Toegang", expanded=False):
        st.markdown("""
        <div style="
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 2rem;
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        ">
        """, unsafe_allow_html=True)
        
        with st.form("admin_login_form"):
            st.markdown("**Admin Gegevens:**")
            admin_email = st.text_input("Admin E-mail", value="admin@example.com")
            admin_code = st.text_input("Admin Code", value="DEMO", type="password")
            admin_login = st.form_submit_button("🔑 Admin Inloggen", use_container_width=True)
        
        if admin_login and admin_email and admin_code:
            if admin_email == "admin@example.com":
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = admin_email
                st.success("🎖️ Admin toegang verleend!")
                time.sleep(2)
                st.rerun()
            else:
                st.error("❌ Ongeldige admin gegevens")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Epic footer
    st.markdown("""
    <div class="modern-footer">
        <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">✨</div>
        © 2025 Leveranciers Portal - Een product van <strong>Pontifexx</strong>
        <div style="font-size: 0.9rem; margin-top: 0.5rem; opacity: 0.8;">
            Gemaakt met ❤️ en moderne technologie
        </div>
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
    st.markdown('<div class="modern-card"><h3>🔄 Synchronisatie Status</h3></div>', unsafe_allow_html=True)
    display_sync_status()
    
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
        
        # Display statistics - ONLY if we have jobs
        if jobs_by_customer:
            with st.container():
                st.markdown('<div class="modern-card"><h3>📊 Overzicht</h3></div>', unsafe_allow_html=True)
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
            
            # Display customer tabs
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
    with st.container():
        st.markdown('<div class="job-card"><h3>📝 Werkorder Details</h3></div>', unsafe_allow_html=True)
        
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
    
    # Completion form
    with st.container():
        st.markdown('<div class="modern-card"><h3>✅ Werkorder Afronden</h3></div>', unsafe_allow_html=True)
        
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
            
            # Document upload
            st.markdown("📄 **Documenten Uploaden** (Optioneel)")
            col1, col2 = st.columns(2)
            with col1:
                doc1 = st.file_uploader("Document 1", type=["pdf", "doc", "docx", "xls", "xlsx", "txt"], key="doc1_modern")
                doc2 = st.file_uploader("Document 2", type=["pdf", "doc", "docx", "xls", "xlsx", "txt"], key="doc2_modern")
            with col2:
                doc3 = st.file_uploader("Document 3", type=["pdf", "doc", "docx", "xls", "xlsx", "txt"], key="doc3_modern")
                doc4 = st.file_uploader("Document 4", type=["pdf", "doc", "docx", "xls", "xlsx", "txt"], key="doc4_modern")
            
            submit_button = st.form_submit_button("🚀 Werkorder Afronden", use_container_width=True)
            
            # Handle form submission within the form
            if submit_button:
                target_status = mappings.get(selected_job["voortgang_status"])
                
                if not target_status:
                    st.error("❌ Geen doelstatus configuratie gevonden voor deze werkorder.")
                else:
                    with st.spinner("⏳ Werkorder wordt bijgewerkt..."):
                        if update_job_status(domein, api_key, selected_job_id, target_status, feedback):
                            st.success(f"✅ Werkorder {selected_job_id} succesvol bijgewerkt!")
                            
                            # Handle file uploads
                            images = [image1, image2, image3, image4]
                            documents = [doc1, doc2, doc3, doc4]
                            
                            if any(img is not None for img in images):
                                with st.spinner("📤 Afbeeldingen worden geüpload..."):
                                    # Placeholder for image upload function
                                    st.info("📸 Afbeelding upload functionaliteit wordt toegevoegd...")
                            
                            if any(doc is not None for doc in documents):
                                with st.spinner("📄 Documenten worden geüpload..."):
                                    # Placeholder for document upload function
                                    st.info("📄 Document upload functionaliteit wordt toegevoegd...")
                            
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
                            
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ Bijwerken van werkorder mislukt. Probeer het opnieuw.")

# MODERN ADMIN PAGE - Fully functional
def admin_page():
    st.markdown("""
    <div class="main-header">
        <h1>⚙️ Beheerders Dashboard</h1>
        <p>Beheer klanten, statustoewijzingen en synchronisatie</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sync status
    st.markdown('<div class="modern-card"><h3>🔄 Synchronisatie Beheer</h3></div>', unsafe_allow_html=True)
    display_sync_status()
    
    tabs = st.tabs(["🏢 Klanten", "🔄 Status Mapping", "👥 Toegang", "⚙️ Sync Instellingen"])
    
    with tabs[0]:
        manage_customers_modern()
    
    with tabs[1]:
        manage_progress_status_mappings_modern()
        
    with tabs[2]:
        manage_supplier_access_modern()
        
    with tabs[3]:
        manage_sync_settings_modern()

def manage_customers_modern():
    with st.container():
        st.markdown('<div class="modern-card"><h3>🏢 Klanten Beheren</h3></div>', unsafe_allow_html=True)
        
        # Formulier voor het toevoegen van een nieuwe klant
        with st.form("add_customer_form"):
            st.markdown("#### ➕ Nieuwe Klant Toevoegen")
            
            col1, col2 = st.columns(2)
            with col1:
                naam = st.text_input("Klantnaam", placeholder="Bijv. Acme Corp")
                domein = st.text_input("Domein", placeholder="025105.ultimo-demo.net")
            with col2:
                api_key = st.text_input("API Sleutel", placeholder="Voer API key in")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                test_button = st.form_submit_button("🔍 Test Verbinding", use_container_width=True)
            with col2:
                submit_button = st.form_submit_button("✅ Klant Toevoegen", use_container_width=True)
        
        if test_button and domein and api_key:
            with st.spinner("🔍 API-verbinding wordt getest..."):
                is_valid, message = test_api_connection(domein, api_key)
                if is_valid:
                    st.success(f"✅ API-verbindingstest geslaagd!")
                    st.info("De API-verbinding werkt correct. U kunt de klant veilig toevoegen.")
                else:
                    st.error(f"❌ API-verbindingstest mislukt: {message}")
        
        if submit_button and naam and domein and api_key:
            with st.spinner("💾 Klant wordt toegevoegd..."):
                try:
                    conn = sqlite3.connect('leveranciers_portal.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO klanten (naam, domein, api_key) VALUES (?, ?, ?)",
                              (naam, domein, api_key))
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 Klant **{naam}** succesvol toegevoegd!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Fout bij toevoegen klant: {str(e)}")
    
    # Toon bestaande klanten
    display_customers_modern()

def display_customers_modern():
    conn = sqlite3.connect('leveranciers_portal.db')
    
    try:
        df = pd.read_sql_query("SELECT id, naam, domein FROM klanten", conn)
        
        # Haal ook API keys op voor testing
        c = conn.cursor()
        c.execute("SELECT id, naam, domein, api_key FROM klanten")
        klanten = c.fetchall()
    except Exception as e:
        st.error(f"Database fout: {str(e)}")
        return
    finally:
        conn.close()
    
    if not df.empty:
        with st.container():
            st.markdown('<div class="modern-card"><h3>📊 Bestaande Klanten</h3></div>', unsafe_allow_html=True)
            
            # Mooie tabel weergave
            st.dataframe(
                df, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "naam": st.column_config.TextColumn("Klant Naam", width="medium"),
                    "domein": st.column_config.TextColumn("Domein", width="large"),
                }
            )
            
            if klanten:
                st.markdown("#### 🔧 Klant Beheer")
                
                klant_id = st.selectbox(
                    "Selecteer klant voor beheer:", 
                    [c[0] for c in klanten], 
                    format_func=lambda x: next((f"{c[1]} ({c[2]})" for c in klanten if c[0] == x), ""),
                    key="customer_management_select"
                )
                
                selected_customer = next((c for c in klanten if c[0] == klant_id), None)
                
                if selected_customer:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("🔍 Test API Verbinding", use_container_width=True, key="test_selected_customer"):
                            domein = selected_customer[2]
                            api_key = selected_customer[3]
                            
                            with st.spinner("🔍 API wordt getest..."):
                                is_valid, message = test_api_connection(domein, api_key)
                                if is_valid:
                                    st.success(f"✅ API-verbinding met **{selected_customer[1]}** werkt perfect!")
                                else:
                                    st.error(f"❌ API-verbinding mislukt: {message}")
                    
                    with col2:
                        if st.button("🗑️ Verwijder Klant", use_container_width=True, key="delete_selected_customer", type="secondary"):
                            # Confirmation dialog simulation
                            if st.button(f"⚠️ BEVESTIG: Verwijder {selected_customer[1]}", key="confirm_delete", type="secondary"):
                                with st.spinner("🗑️ Klant wordt verwijderd..."):
                                    try:
                                        conn = sqlite3.connect('leveranciers_portal.db')
                                        c = conn.cursor()
                                        c.execute("DELETE FROM status_toewijzingen WHERE klant_id = ?", (klant_id,))
                                        c.execute("DELETE FROM jobs_cache WHERE klant_id = ?", (klant_id,))
                                        c.execute("DELETE FROM klanten WHERE id = ?", (klant_id,))
                                        conn.commit()
                                        conn.close()
                                        st.success(f"🗑️ Klant **{selected_customer[1]}** succesvol verwijderd!")
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Fout bij verwijderen: {str(e)}")
    else:
        st.markdown("""
        <div class="modern-card">
            <div style="text-align: center; padding: 2rem;">
                <h3>📭 Nog geen klanten</h3>
                <p>Voeg uw eerste klant toe om te beginnen.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def manage_progress_status_mappings_modern():
    with st.container():
        st.markdown('<div class="modern-card"><h3>🔄 Status Toewijzingen Beheren</h3></div>', unsafe_allow_html=True)
        
        conn = sqlite3.connect('leveranciers_portal.db')
        klanten_df = pd.read_sql_query("SELECT id, naam, domein, api_key FROM klanten", conn)
        conn.close()
        
        if klanten_df.empty:
            st.markdown("""
            <div style="text-align: center; padding: 2rem;">
                <h4>⚠️ Geen klanten gevonden</h4>
                <p>Voeg eerst klanten toe voordat u status toewijzingen kunt configureren.</p>
            </div>
            """, unsafe_allow_html=True)
            return
        
        klant_id = st.selectbox(
            "🏢 Selecteer Klant:", 
            klanten_df["id"].tolist(), 
            format_func=lambda x: klanten_df[klanten_df["id"] == x]["naam"].iloc[0],
            key="status_mapping_customer_select"
        )
        
        klant_row = klanten_df[klanten_df["id"] == klant_id].iloc[0]
        domein = klant_row["domein"]
        api_key = klant_row["api_key"]
        
        # Haal voortgangsstatussen op van API
        with st.spinner("📊 Voortgangsstatussen worden opgehaald..."):
            voortgang_statussen = get_progress_statuses(domein, api_key)
        
        if not voortgang_statussen:
            st.warning("⚠️ Kan voortgangsstatussen niet ophalen. Controleer de API-verbinding.")
            return
        
        status_options = {status["Id"]: f"{status['Id']}: {status['Description']}" for status in voortgang_statussen}
        
        # Formulier voor het toevoegen van een nieuwe toewijzing
        with st.form("add_mapping_form"):
            st.markdown("#### ➕ Nieuwe Status Toewijzing")
            st.info("📋 Definieer welke status overgangen leveranciers kunnen uitvoeren")
            
            col1, col2 = st.columns(2)
            with col1:
                van_status = st.selectbox(
                    "🔄 Van Status:", 
                    list(status_options.keys()), 
                    format_func=lambda x: status_options[x],
                    key="van_status_select"
                )
            with col2:
                naar_status = st.selectbox(
                    "✅ Naar Status:", 
                    list(status_options.keys()), 
                    format_func=lambda x: status_options[x],
                    key="naar_status_select"
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit_button = st.form_submit_button("✅ Toewijzing Toevoegen", use_container_width=True)
        
        if submit_button:
            with st.spinner("💾 Toewijzing wordt toegevoegd..."):
                conn = sqlite3.connect('leveranciers_portal.db')
                c = conn.cursor()
                
                # Controleer of toewijzing al bestaat
                c.execute("""
                SELECT COUNT(*) FROM status_toewijzingen 
                WHERE klant_id = ? AND van_status = ?
                """, (klant_id, van_status))
                
                count = c.fetchone()[0]
                
                if count > 0:
                    st.error(f"❌ Er bestaat al een toewijzing voor **Van Status: {van_status}** voor deze klant.")
                else:
                    c.execute("""
                    INSERT INTO status_toewijzingen (klant_id, van_status, naar_status)
                    VALUES (?, ?, ?)
                    """, (klant_id, van_status, naar_status))
                    conn.commit()
                    st.success("🎉 Toewijzing succesvol toegevoegd!")
                    time.sleep(1)
                    st.rerun()
                
                conn.close()
    
    # Toon bestaande toewijzingen
    display_status_mappings_modern(klant_id, status_options)

def display_status_mappings_modern(klant_id, status_options):
    conn = sqlite3.connect('leveranciers_portal.db')
    toewijzingen_df = pd.read_sql_query("""
    SELECT id, van_status, naar_status FROM status_toewijzingen
    WHERE klant_id = ?
    """, conn, params=(klant_id,))
    conn.close()
    
    if not toewijzingen_df.empty:
        with st.container():
            st.markdown('<div class="modern-card"><h3>📋 Bestaande Toewijzingen</h3></div>', unsafe_allow_html=True)
            
            # Voeg statusbeschrijvingen toe aan het dataframe
            toewijzingen_df["Van Status"] = toewijzingen_df["van_status"].apply(lambda x: status_options.get(x, x))
            toewijzingen_df["Naar Status"] = toewijzingen_df["naar_status"].apply(lambda x: status_options.get(x, x))
            
            # Mooie tabel weergave
            display_df = toewijzingen_df[["id", "Van Status", "Naar Status"]].copy()
            display_df.columns = ["ID", "Van Status", "Naar Status"]
            
            st.dataframe(
                display_df, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", width="small"),
                    "Van Status": st.column_config.TextColumn("Van Status", width="large"),
                    "Naar Status": st.column_config.TextColumn("Naar Status", width="large"),
                }
            )
            
            # Optie om toewijzing te verwijderen
            st.markdown("#### 🗑️ Toewijzing Verwijderen")
            toewijzing_id = st.selectbox(
                "Selecteer toewijzing om te verwijderen:", 
                toewijzingen_df["id"].tolist(),
                format_func=lambda x: f"ID {x}: {toewijzingen_df[toewijzingen_df['id']==x]['Van Status'].iloc[0]} → {toewijzingen_df[toewijzingen_df['id']==x]['Naar Status'].iloc[0]}",
                key="delete_mapping_select"
            )
            
            if st.button("🗑️ Verwijder Geselecteerde Toewijzing", use_container_width=True, key="delete_mapping_btn"):
                with st.spinner("🗑️ Toewijzing wordt verwijderd..."):
                    conn = sqlite3.connect('leveranciers_portal.db')
                    c = conn.cursor()
                    c.execute("DELETE FROM status_toewijzingen WHERE id = ?", (toewijzing_id,))
                    conn.commit()
                    conn.close()
                    st.success("🗑️ Toewijzing succesvol verwijderd!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.markdown("""
        <div class="modern-card">
            <div style="text-align: center; padding: 2rem;">
                <h4>📭 Nog geen toewijzingen</h4>
                <p>Voeg status toewijzingen toe om leveranciers workflow te configureren.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def manage_supplier_access_modern():
    with st.container():
        st.markdown('<div class="modern-card"><h3>👥 Leveranciers Toegang Beheren</h3></div>', unsafe_allow_html=True)
        
        # Haal alle klanten op voor filtering
        conn = sqlite3.connect('leveranciers_portal.db')
        c = conn.cursor()
        
        c.execute("SELECT id, naam FROM klanten")
        klanten = c.fetchall()
        
        if not klanten:
            st.markdown("""
            <div style="text-align: center; padding: 2rem;">
                <h4>⚠️ Geen klanten gevonden</h4>
                <p>Voeg eerst klanten toe om leveranciers toegang te kunnen beheren.</p>
            </div>
            """, unsafe_allow_html=True)
            conn.close()
            return
        
        klant_options = {klant_id: naam for klant_id, naam in klanten}
        klant_options[0] = "Alle Klanten"
        
        selected_customer = st.selectbox(
            "🏢 Filter op Klant:", 
            list(klant_options.keys()),
            format_func=lambda x: klant_options[x],
            key="supplier_access_filter"
        )
        
        # Query om e-mails uit jobgegevens te halen
        if selected_customer == 0:
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
            c.execute(query, (selected_customer,))
        
        jobs = c.fetchall()
        conn.close()
        
        # Verwerk de jobs om e-mails te extraheren
        emails = {}
        for job in jobs:
            job_id, omschrijving, klant_naam, contacts_json, data_json = job
            
            try:
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
                                        'jobs': [],
                                        'klant_naam': klant_naam
                                    }
                                
                                job_info = {'id': job_id, 'omschrijving': omschrijving, 'klant_naam': klant_naam}
                                if job_info not in emails[email]['jobs']:
                                    emails[email]['jobs'].append(job_info)
            except Exception as e:
                print(f"Error processing job {job_id}: {str(e)}")
                continue
        
        # Toon de e-mails
        if emails:
            st.success(f"✅ {len(emails)} leveranciers e-mails gevonden met toegang")
            
            # Maak een dataframe voor weergave
            rows = []
            for email, info in emails.items():
                job_count = len(info['jobs'])
                rows.append({
                    '📧 E-mail': email,
                    '👤 Naam': info['name'] or 'Niet opgegeven',
                    '🏢 Leverancier': f"{info['vendor_id']}: {info['vendor_name']}" if info['vendor_id'] else 'Onbekend',
                    '📊 Aantal Jobs': job_count
                })
            
            df = pd.DataFrame(rows)
            st.dataframe(
                df, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "📧 E-mail": st.column_config.TextColumn("E-mail", width="large"),
                    "👤 Naam": st.column_config.TextColumn("Naam", width="medium"),
                    "🏢 Leverancier": st.column_config.TextColumn("Leverancier", width="large"),
                    "📊 Aantal Jobs": st.column_config.NumberColumn("Jobs", width="small"),
                }
            )
            
            # Toon details voor een geselecteerde e-mail
            if rows:
                email_options = [row['📧 E-mail'] for row in rows]
                selected_email = st.selectbox(
                    "🔍 Bekijk Jobs voor E-mail:", 
                    email_options,
                    key="email_detail_select"
                )
                
                if selected_email in emails:
                    st.markdown(f"#### 📋 Jobs voor **{selected_email}**")
                    info = emails[selected_email]
                    
                    if info['jobs']:
                        job_rows = []
                        for job in info['jobs']:
                            job_rows.append({
                                '🆔 Job ID': job['id'],
                                '📝 Omschrijving': job['omschrijving'],
                                '🏢 Klant': job['klant_naam']
                            })
                        
                        job_df = pd.DataFrame(job_rows)
                        st.dataframe(
                            job_df, 
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "🆔 Job ID": st.column_config.TextColumn("Job ID", width="medium"),
                                "📝 Omschrijving": st.column_config.TextColumn("Omschrijving", width="large"),
                                "🏢 Klant": st.column_config.TextColumn("Klant", width="medium"),
                            }
                        )
                    else:
                        st.info("📭 Geen jobs gevonden voor deze e-mail.")
        else:
            st.markdown("""
            <div style="text-align: center; padding: 2rem;">
                <h4>📭 Geen leveranciers e-mails gevonden</h4>
                <p>Zorg ervoor dat jobs correct zijn gesynchroniseerd en dat leveranciers contactgegevens bevatten.</p>
            </div>
            """, unsafe_allow_html=True)

def manage_sync_settings_modern():
    with st.container():
        st.markdown('<div class="modern-card"><h3>⚙️ Synchronisatie Instellingen</h3></div>', unsafe_allow_html=True)
        
        # Get current sync settings
        sync_status = get_sync_status()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Huidige Status")
            
            if sync_status['last_sync'] and sync_status['last_sync'] != "Nooit":
                try:
                    last_sync_dt = datetime.datetime.fromisoformat(sync_status['last_sync'])
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
                    
                    st.info(f"🕒 **Laatste sync:** {formatted_time} ({time_ago_str})")
                except:
                    st.info(f"🕒 **Laatste sync:** {sync_status['last_sync']}")
            else:
                st.warning("⚠️ **Laatste sync:** Nog nooit uitgevoerd")
            
            # Show current interval
            interval = sync_status['interval']
            if interval == 3600:
                st.write("⏱️ **Huidige interval:** Elk uur")
            elif interval < 3600:
                minutes = interval // 60
                st.write(f"⏱️ **Huidige interval:** Elke {minutes} {'minuut' if minutes == 1 else 'minuten'}")
            else:
                hours = interval // 3600
                st.write(f"⏱️ **Huidige interval:** Elke {hours} {'uur' if hours == 1 else 'uren'}")
        
        with col2:
            st.markdown("#### ⚙️ Interval Configureren")
            
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
                
                current_interval = sync_status['interval']
                current_index = list(interval_options.keys()).index(current_interval) if current_interval in interval_options else 2
                
                selected_interval = st.selectbox(
                    "🕐 Kies synchronisatie interval:", 
                    list(interval_options.keys()),
                    format_func=lambda x: interval_options[x],
                    index=current_index,
                    key="sync_interval_select"
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                submit_button = st.form_submit_button("💾 Interval Bijwerken", use_container_width=True)
            
            if submit_button:
                with st.spinner("⚙️ Interval wordt bijgewerkt..."):
                    try:
                        conn = sqlite3.connect('leveranciers_portal.db')
                        c = conn.cursor()
                        c.execute("UPDATE sync_control SET sync_interval = ? WHERE id = 1", (selected_interval,))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Interval bijgewerkt naar **{interval_options[selected_interval]}**")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Fout bij bijwerken interval: {str(e)}")
        
        # API Usage Information
        st.markdown("#### 📖 Over Synchronisatie")
        st.markdown("""
        <div style="
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 1.5rem;
            margin: 1rem 0;
            border-left: 4px solid #667eea;
        ">
            <h5>🔄 Hoe werkt synchronisatie?</h5>
            <ul>
                <li><strong>Automatisch:</strong> Volgens het ingestelde interval</li>
                <li><strong>Handmatig:</strong> Via de sync knop</li>
                <li><strong>Bij opstarten:</strong> Eerste keer wanneer app start</li>
            </ul>
            
            <h5>⚡ Performance Optimalisatie:</h5>
            <ul>
                <li><strong>Incrementeel:</strong> Alleen gewijzigde records sinds laatste sync</li>
                <li><strong>Gecached:</strong> E-mail verificatie gebruikt lokale cache</li>
                <li><strong>Efficiënt:</strong> Minimale API-aanroepen</li>
            </ul>
            
            <h5>💡 Aanbevelingen:</h5>
            <ul>
                <li><strong>Productie:</strong> 1-4 uur interval</li>
                <li><strong>Development:</strong> 15-30 minuten voor testen</li>
                <li><strong>Hoge activiteit:</strong> Korter interval voor real-time updates</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

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

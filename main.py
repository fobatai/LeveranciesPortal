import streamlit as st
import requests
import json
import pandas as pd
import sqlite3
import base64
import os
import random
import string
from datetime import datetime, timezone

# Database setup
def init_db():
    conn = sqlite3.connect('portal.db')
    c = conn.cursor()
    
    # Maak tabellen aan met unieke beperkingen
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS erp_systems (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            domain TEXT NOT NULL UNIQUE,
            api_key TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS status_mappings (
            id INTEGER PRIMARY KEY,
            erp_system_id INTEGER,
            from_status TEXT NOT NULL,
            to_status TEXT NOT NULL,
            FOREIGN KEY (erp_system_id) REFERENCES erp_systems (id),
            UNIQUE(erp_system_id)
        )
    ''')
    
    # Voeg standaard admin-gebruiker toe als deze nog niet bestaat
    c.execute('''
        INSERT OR IGNORE INTO admin_users (email, is_admin)
        VALUES (?, ?)
    ''', ('admin@example.com', 1))
    
    # Voeg standaard ERP-systeem toe als deze nog niet bestaat
    c.execute('''
        INSERT OR IGNORE INTO erp_systems (name, domain, api_key)
        VALUES (?, ?, ?)
    ''', ('Ultimo Demo', '025105.ultimo-demo.net', 'E7BFA8ADE2AF4A3FB49962F54AAFB5A6'))
    
    conn.commit()
    conn.close()

# API functies
def get_progress_statuses(domain, api_key):
    url = f"https://{domain}/api/v1/object/ProgressStatus"
    headers = {
        'accept': 'application/json',
        'ApiKey': api_key
    }
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            st.error(f"API Fout: {response.status_code} - {response.text}")
            return []
            
        data = response.json()
        if not isinstance(data, dict) or 'items' not in data:
            st.error("Ongeldige API respons structuur")
            return []
            
        return data.get('items', [])
    except Exception as e:
        st.error(f"Fout bij ophalen statussen: {str(e)}")
        return []

def get_jobs_for_vendor(domain, api_key, email):
    url = f"https://{domain}/api/v1/object/Job"
    headers = {
        'accept': 'application/json',
        'ApiKey': api_key
    }
    
    params = {
        'expand': 'Vendor/ObjectContacts/Employee'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            st.error(f"API Fout: {response.status_code} - {response.text}")
            return []
            
        data = response.json()
        if not isinstance(data, dict) or 'items' not in data:
            st.error("Ongeldige API respons structuur")
            return []
            
        all_jobs = data.get('items', [])
        if not all_jobs:
            st.warning("Geen jobs gevonden in het systeem")
            return []
        
        filtered_jobs = []
        for job in all_jobs:
            if not isinstance(job, dict):
                st.warning("Ongeldige job structuur")
                continue
                
            vendor = job.get('Vendor', {})
            if not isinstance(vendor, dict):
                continue
                
            object_contacts = vendor.get('ObjectContacts', [])
            if not isinstance(object_contacts, list):
                continue
                
            for contact in object_contacts:
                if not isinstance(contact, dict):
                    continue
                    
                employee = contact.get('Employee', {})
                if not isinstance(employee, dict):
                    continue
                    
                if employee.get('EmailAddress') == email:
                    try:
                        if 'Equipment' in job and job['Equipment']:
                            equip_url = f"https://{domain}/api/v1/object/Equipment('{job['Equipment']}')"
                            equip_response = requests.get(equip_url, headers=headers)
                            if equip_response.status_code == 200:
                                job['Equipment'] = equip_response.json()
                            else:
                                st.warning(f"Fout bij ophalen Equipment details voor {job['Equipment']}: {equip_response.status_code} - {equip_response.text}")
                            
                        if 'ProcessFunction' in job and job['ProcessFunction']:
                            proc_url = f"https://{domain}/api/v1/object/ProcessFunction('{job['ProcessFunction']}')"
                            proc_response = requests.get(proc_url, headers=headers)
                            if proc_response.status_code == 200:
                                job['ProcessFunction'] = proc_response.json()
                            else:
                                st.warning(f"Fout bij ophalen ProcessFunction details voor {job['ProcessFunction']}: {proc_response.status_code} - {proc_response.text}")
                    except Exception as e:
                        st.warning(f"Extra details ophalen mislukt voor job {job.get('Id', 'onbekend')}: {str(e)}")
                    
                    filtered_jobs.append(job)
                    break
        
        if not filtered_jobs:
            st.info(f"Geen jobs gevonden voor {email}")
        return filtered_jobs
        
    except Exception as e:
        st.error(f"Fout bij ophalen jobs: {str(e)}")
        return []
    
def update_job_status(domain, api_key, job_id, feedback_text, new_progress_status):
    # Gebruik de door de API verwachte URL-syntaxis voor de job
    job_url = f"https://{domain}/api/v1/object/Job('{job_id}')"
    st.write("DEBUG: PATCH URL:", job_url)
    
    # Stel StatusCompletedDate in op de huidige datum/tijd in ISO-formaat (UTC)
    status_completed_date = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # Maak een payload met alleen de te wijzigen velden, inclusief de nieuwe ProgressStatus
    payload = {
        "FeedbackText": feedback_text,
        "StatusCompletedDate": status_completed_date,
        "ProgressStatus": new_progress_status
    }
    
    st.write("DEBUG: PATCH Payload:", payload)
    
    headers = {
        'accept': 'application/json',
        'ApiKey': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.patch(job_url, headers=headers, json=payload)
        st.write("DEBUG: PATCH Response status:", response.status_code)
        st.write("DEBUG: PATCH Response body:", response.text)
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Fout bij updaten job status: {str(e)}")
        return False

def attach_image_to_job(domain, api_key, job_id, image_file):
    """
    Verzendt een base64-gecodeerde afbeelding naar de API om deze aan een job te koppelen.
    """
    url = f"https://{domain}/api/v1/action/REST_AttachImageToJob"
    headers = {
        'accept': 'application/json',
        'ApplicationElementId': 'D1FB01D577C248DFB95A2ADA578578DF',
        'ApiKey': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        # Lees de inhoud van het bestand en codeer deze naar base64
        file_bytes = image_file.read()
        encoded_string = base64.b64encode(file_bytes).decode('utf-8')
        
        # Bepaal de bestandsextensie (zonder punt)
        extension = os.path.splitext(image_file.name)[1].lower()
        if extension.startswith('.'):
            extension = extension[1:]
        
        # Bouw de payload op
        payload = {
            "JobId": job_id,
            "ImageFileBase64": encoded_string,
            "ImageFileBase64Extension": extension
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Fout bij het koppelen van de afbeelding: {str(e)}")
        return False

# Admin pagina
def admin_page():
    st.title("Admin Configuratie")
    
    tab1, tab2 = st.tabs(["Voeg Systeem toe", "Bekijk Configuraties"])
    
    with tab1:
        st.header("Voeg ERP-systeem toe")
        with st.form("add_erp"):
            name = st.text_input("Systeemnaam", value="Ultimo Demo")
            domain = st.text_input("Domein", value="025105.ultimo-demo.net")
            api_key = st.text_input("API Key", value="E7BFA8ADE2AF4A3FB49962F54AAFB5A6")
            
            submitted = st.form_submit_button("Voeg systeem toe")
            if submitted:
                conn = sqlite3.connect('portal.db')
                c = conn.cursor()
                
                try:
                    c.execute("SELECT id FROM erp_systems WHERE domain = ?", (domain,))
                    if c.fetchone():
                        st.error("Er bestaat al een systeem met dit domein!")
                    else:
                        c.execute("INSERT INTO erp_systems (name, domain, api_key) VALUES (?, ?, ?)",
                                  (name, domain, api_key))
                        conn.commit()
                        st.success("Systeem succesvol toegevoegd!")
                except sqlite3.IntegrityError:
                    st.error("Er bestaat al een systeem met dit domein!")
                except Exception as e:
                    st.error(f"Fout bij toevoegen systeem: {str(e)}")
                finally:
                    conn.close()

    with tab2:
        st.header("Systeem Configuraties")
        
        conn = sqlite3.connect('portal.db')
        c = conn.cursor()
        systems = c.execute("SELECT * FROM erp_systems").fetchall()
        
        if systems:
            for system in systems:
                st.subheader(f"📋 {system[1]}")
                st.write(f"Domein: {system[2]}")
                
                mappings = c.execute("""
                    SELECT from_status, to_status 
                    FROM status_mappings 
                    WHERE erp_system_id = ?
                """, (system[0],)).fetchall()
                
                if mappings:
                    statuses = get_progress_statuses(system[2], system[3])
                    status_dict = {s['Id']: s['Description'] for s in statuses}
                    
                    st.write("Huidige Status Configuratie:")
                    for from_status, to_status in mappings:
                        st.info(f"Van: {from_status} - {status_dict.get(from_status, 'Onbekend')} → Naar: {to_status} - {status_dict.get(to_status, 'Onbekend')}")
                    
                    col1, col2 = st.columns([3,1])
                    with col2:
                        if st.button("Verwijder Systeem en Configuratie", key=f"delete_{system[0]}"):
                            try:
                                c.execute("DELETE FROM status_mappings WHERE erp_system_id = ?", 
                                          (system[0],))
                                c.execute("DELETE FROM erp_systems WHERE id = ?", 
                                          (system[0],))
                                conn.commit()
                                st.success("Systeem en configuratie verwijderd!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fout bij verwijderen configuratie: {str(e)}")
                else:
                    st.warning("Geen status mappings geconfigureerd voor dit systeem")
                
                st.divider()
        else:
            st.info("Geen ERP-systemen geconfigureerd. Voeg eerst een systeem toe.")
        
        if systems:
            st.header("Configureer Status Mappings")
            selected_system = st.selectbox(
                "Selecteer ERP-systeem",
                options=systems,
                format_func=lambda x: x[1],
                key="system_select"
            )

            if selected_system:
                statuses = get_progress_statuses(selected_system[2], selected_system[3])
                
                if not statuses:
                    st.error("Kon statussen niet ophalen van het systeem")
                    return

                existing_mapping = c.execute("""
                    SELECT from_status, to_status 
                    FROM status_mappings 
                    WHERE erp_system_id = ?
                """, (selected_system[0],)).fetchone()
                
                if existing_mapping:
                    st.warning(f"Dit systeem heeft al een status mapping: {existing_mapping[0]} → {existing_mapping[1]}")
                    
                    if st.button("Verwijder Bestaande Configuratie"):
                        try:
                            c.execute("DELETE FROM status_mappings WHERE erp_system_id = ?", 
                                      (selected_system[0],))
                            conn.commit()
                            st.success("Configuratie succesvol verwijderd!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fout bij verwijderen: {str(e)}")
                else:
                    st.subheader("Voeg Status Mapping toe")
                    
                    form = st.form("status_mapping_form")
                    col1, col2 = form.columns(2)
                    
                    with col1:
                        from_status = form.selectbox(
                            "Van Status",
                            options=statuses,
                            format_func=lambda x: f"{x['Id']} - {x['Description']}"
                        )
                    
                    with col2:
                        to_status = form.selectbox(
                            "Naar Status",
                            options=statuses,
                            format_func=lambda x: f"{x['Id']} - {x['Description']}"
                        )
                    
                    if form.form_submit_button("Voeg Mapping toe"):
                        try:
                            c.execute("""
                                INSERT INTO status_mappings (erp_system_id, from_status, to_status)
                                VALUES (?, ?, ?)
                            """, (selected_system[0], from_status['Id'], to_status['Id']))
                            conn.commit()
                            st.success("Status mapping succesvol toegevoegd!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fout bij toevoegen mapping: {str(e)}")
        
        conn.close()

# Supplier pagina
def supplier_page(email):
    st.title("Jouw Jobs")
    
    conn = sqlite3.connect('portal.db')
    c = conn.cursor()
    systems = c.execute("SELECT * FROM erp_systems").fetchall()
    
    all_jobs = []
    for system in systems:
        jobs = get_jobs_for_vendor(system[2], system[3], email)
        for job in jobs:
            job['ERP_System'] = system[1]
            job['System_Domain'] = system[2]
            job['System_API_Key'] = system[3]
            all_jobs.append(job)
    
    available_jobs = []
    for job in all_jobs:
        c.execute("""
            SELECT to_status 
            FROM status_mappings 
            WHERE erp_system_id = (SELECT id FROM erp_systems WHERE domain = ?) 
            AND from_status = ?
        """, (job['System_Domain'], job['ProgressStatus']))
        
        if c.fetchone():
            available_jobs.append(job)
    
    if available_jobs:
        job_data = []
        for job in available_jobs:
            equipment_desc = job['Equipment'].get('Description') if isinstance(job['Equipment'], dict) else job['Equipment']
            process_func_desc = job['ProcessFunction'].get('Description') if isinstance(job['ProcessFunction'], dict) else job['ProcessFunction']
            
            job_data.append({
                'Id': job['Id'],
                'Beschrijving': job['Description'],
                'Equipment': equipment_desc,
                'ProcessFunction': process_func_desc,
                'Status': job['ProgressStatus']
            })
        
        df = pd.DataFrame(job_data)
        st.write("Beschikbare Jobs:")
        st.dataframe(df)
        
        st.header("Job gereed melden")
        selected_job_id = st.selectbox(
            "Selecteer de job die je wilt gereed melden",
            options=[job['Id'] for job in available_jobs],
            format_func=lambda x: f"{x} - {next(job['Description'] for job in available_jobs if job['Id'] == x)}"
        )
        
        selected_job = next(job for job in available_jobs if job['Id'] == selected_job_id)
        if selected_job:
            with st.form("complete_job"):
                feedback = st.text_area("Feedback", height=150)
                image_file = st.file_uploader("Kies een afbeelding (optioneel)", type=["jpg", "jpeg", "png"])
                
                c.execute("""
                    SELECT to_status 
                    FROM status_mappings 
                    WHERE erp_system_id = (SELECT id FROM erp_systems WHERE domain = ?) 
                    AND from_status = ?
                """, (selected_job['System_Domain'], selected_job['ProgressStatus']))
                
                mapping = c.fetchone()
                submitted = st.form_submit_button("Job gereed melden")
                if submitted:
                    if mapping:
                        target_status = mapping[0]
                        # Update de jobstatus: meegeven van de feedback en de target ProgressStatus
                        if update_job_status(
                            selected_job['System_Domain'],
                            selected_job['System_API_Key'],
                            selected_job['Id'],
                            feedback,
                            target_status
                        ):
                            st.success("Job succesvol gecomplete!")
                            # Als er een afbeelding is geüpload, koppel deze aan de job
                            if image_file:
                                if attach_image_to_job(
                                    selected_job['System_Domain'],
                                    selected_job['System_API_Key'],
                                    selected_job['Id'],
                                    image_file
                                ):
                                    st.success("Afbeelding succesvol toegevoegd!")
                            st.rerun()
                    else:
                        st.error("Geen status mapping gevonden voor de huidige status van deze job")
    else:
        st.write("Geen jobs beschikbaar om gereed te melden")
    
    conn.close()

# Functie om een login code te genereren (voor demonstratiedoeleinden)
def generate_login_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

# Login pagina
def login_page():
    st.title("Portal Inloggen")
    
    login_type = st.radio("Log in als:", ["Supplier", "Admin"], key="login_type")
    
    if login_type == "Admin":
        email = st.text_input("E-mailadres", value="admin@example.com", key="admin_email")
        auth_code = st.text_input("Voer code in", value="123456", key="admin_code")
        
        if st.button("Login", key="admin_login"):
            if email == "admin@example.com" and auth_code == "123456":
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("Ongeldige admin gegevens")
    else:
        # Supplier inlogproces met code
        email = st.text_input("Wat is je e-mailadres?", key="supplier_email")
        if not st.session_state.get("code_verstuurd", False):
            if st.button("Verstuur code"):
                if email:
                    code = generate_login_code()
                    st.session_state.supplier_code = code
                    st.session_state.code_verstuurd = True
                    st.session_state.temp_email = email
                    st.info(f"Code verstuurd naar {email}. (Voor demo: code is {code})")
                else:
                    st.error("Vul een geldig e-mailadres in")
        else:
            st.info(f"Er is een code verstuurd naar {st.session_state.temp_email}.")
            ingevoerde_code = st.text_input("Voer de ontvangen code in", key="supplier_ingave_code")
            if st.button("Login"):
                if ingevoerde_code == st.session_state.supplier_code:
                    st.session_state.authenticated = True
                    st.session_state.user_email = st.session_state.temp_email
                    st.session_state.is_admin = False
                    # Reset tijdelijke variabelen
                    st.session_state.code_verstuurd = False
                    st.session_state.supplier_code = None
                    st.rerun()
                else:
                    st.error("Ongeldige code. Probeer het opnieuw.")

# Main applicatie
def main():
    init_db()
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        login_page()
    else:
        # Voor admin zien we beide opties, suppliers alleen "Jobs"
        if st.session_state.is_admin:
            nav_options = ["Jobs", "Admin"]
        else:
            nav_options = ["Jobs"]
        page = st.sidebar.radio("Navigatie", nav_options, key="nav_radio")
        
        if page == "Admin":
            admin_page()
        else:
            supplier_page(st.session_state.user_email)

        if st.sidebar.button("Logout", key="logout_button"):
            st.session_state.authenticated = False
            st.session_state.is_admin = False
            st.session_state.user_email = None
            st.rerun()

if __name__ == "__main__":
    main()

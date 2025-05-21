import unittest
from unittest.mock import patch, MagicMock, call
import sqlite3
import json
import datetime
import os

# Mock Streamlit before importing from Leverancierv2
# This is a common pattern to prevent Streamlit's magic from interfering with tests
mock_st = MagicMock()
# Mock specific streamlit functions that might be called at import time or by tested functions
mock_st.session_state = MagicMock()
mock_st.secrets = MagicMock() 
mock_st.set_page_config = MagicMock()
mock_st.markdown = MagicMock()
mock_st.error = MagicMock()
mock_st.success = MagicMock()
mock_st.info = MagicMock()
mock_st.warning = MagicMock()


import sys
sys.modules['streamlit'] = mock_st
sys.modules['streamlit.secrets'] = mock_st.secrets # if Leverancierv2 uses st.secrets

# Now import the functions from Leverancierv2
# We need to ensure Leverancierv2.py can be imported.
# Assuming Leverancierv2.py is in the same directory or PYTHONPATH is set up.
from Leverancierv2 import (
    generate_login_code,
    verify_login_code,
    check_email_exists,
    test_api_connection,
    force_sync
)

# Helper to reset Streamlit mocks between tests if needed
def reset_streamlit_mocks():
    mock_st.reset_mock()
    mock_st.session_state = MagicMock() # Re-initialize session_state for clean tests
    mock_st.error.reset_mock()
    mock_st.success.reset_mock()
    mock_st.info.reset_mock()
    mock_st.warning.reset_mock()

class TestLeverancierv2(unittest.TestCase):

    def setUp(self):
        # Reset mocks before each test
        reset_streamlit_mocks()

        # Set up any environment variables if necessary (e.g., for email functions if they were tested)
        # For the current scope, not strictly needed but good practice if functions rely on os.getenv
        os.environ["EMAIL_SENDER"] = "test@example.com"
        os.environ["EMAIL_PASSWORD"] = "password"
    
    # --- Tests for generate_login_code ---
    @patch('Leverancierv2.sqlite3.connect')
    def test_generate_login_code_success(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        test_email = "test@example.com"
        result = generate_login_code(test_email)

        self.assertTrue(result)
        mock_sqlite_connect.assert_called_once_with('leveranciers_portal.db')
        mock_conn.cursor.assert_called_once()
        # Check if execute was called for INSERT
        self.assertIn(call("INSERT INTO inlogcodes (email, code, aangemaakt_op) VALUES (?, ?, ?)", 
                           (test_email, mock_st.session_state.__getitem__.call_args[0][0], unittest.mock.ANY)), 
                      mock_cursor.execute.call_args_list) # A bit complex due to code being set in st.session_state first
        mock_cursor.execute.assert_any_call("INSERT INTO inlogcodes (email, code, aangemaakt_op) VALUES (?, ?, ?)",
                                            (test_email, mock_st.session_state['last_code'], unittest.mock.ANY))
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
        self.assertIsNotNone(mock_st.session_state['last_code'])
        self.assertEqual(len(mock_st.session_state['last_code']), 6) # Assuming 6 char code
        mock_st.success.assert_called_once() # generate_login_code calls st.success
        mock_st.info.assert_called_once()


    @patch('Leverancierv2.sqlite3.connect')
    def test_generate_login_code_db_error(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.side_effect = sqlite3.Error("Test DB Error")

        test_email = "error@example.com"
        result = generate_login_code(test_email)

        self.assertFalse(result)
        mock_st.error.assert_called_with("Database fout: Test DB Error")

    # --- Tests for verify_login_code ---
    @patch('Leverancierv2.sqlite3.connect')
    def test_verify_login_code_admin_bypass(self, mock_sqlite_connect):
        self.assertTrue(verify_login_code("admin@example.com", "ANY_CODE"))
        mock_sqlite_connect.assert_not_called() # DB should not be called for admin

    @patch('Leverancierv2.sqlite3.connect')
    def test_verify_login_code_valid(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,) # Simulate finding a code

        email = "user@example.com"
        code = "VALIDC"
        result = verify_login_code(email, code)

        self.assertTrue(result)
        mock_cursor.execute.assert_any_call(unittest.mock.ANY, (email, code, unittest.mock.ANY))
        mock_cursor.execute.assert_any_call("UPDATE inlogcodes SET gebruikt = 1 WHERE id = ?", (1,))
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('Leverancierv2.sqlite3.connect')
    def test_verify_login_code_invalid(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None # Simulate code not found

        self.assertFalse(verify_login_code("user@example.com", "INVALIDC"))
        mock_conn.close.assert_called_once() # Ensure DB connection closed even on failure


    @patch('Leverancierv2.sqlite3.connect')
    def test_verify_login_code_expired(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        # Simulate code not found (which is how expired codes manifest due to time check in query)
        mock_cursor.fetchone.return_value = None 
        
        email = "user@example.com"
        code = "EXPIRED"
        # To make it expired, the query compares aangemaakt_op > fifteen_min_ago
        # If fetchone is None, it means no record matched, implying it might be expired or invalid
        self.assertFalse(verify_login_code(email, code))

    @patch('Leverancierv2.sqlite3.connect')
    def test_verify_login_code_used(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        # First call, code is valid
        mock_cursor.fetchone.return_value = (1,)
        self.assertTrue(verify_login_code("user@example.com", "USEDCODE"))
        
        # Second call, simulate code now marked as used (or simply not found again)
        mock_cursor.fetchone.return_value = None 
        self.assertFalse(verify_login_code("user@example.com", "USEDCODE"))


    # --- Tests for check_email_exists ---
    @patch('Leverancierv2.sqlite3.connect')
    def test_check_email_exists_admin_bypass(self, mock_sqlite_connect):
        self.assertTrue(check_email_exists("admin@example.com"))
        mock_sqlite_connect.assert_not_called()

    @patch('Leverancierv2.sqlite3.connect')
    def test_check_email_exists_in_verification_cache(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        # Simulate found in email_verification_cache
        mock_cursor.fetchone.return_value = (True,) 

        self.assertTrue(check_email_exists("cached@example.com"))
        # Check that the first query to email_verification_cache was made
        mock_cursor.execute.assert_any_call(unittest.mock.ANY, ("cached@example.com", unittest.mock.ANY))
        mock_conn.close.assert_called_once()

    @patch('Leverancierv2.sqlite3.connect')
    @patch('Leverancierv2.json.loads')
    def test_check_email_exists_in_jobs_cache(self, mock_json_loads, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Simulate not in email_verification_cache (first fetchone), then data from jobs_cache
        mock_cursor.fetchone.side_effect = [
            None, # Not in verification cache
            # fetchall for jobs_cache data
            [('{"Vendor": {"ObjectContacts": [{"Employee": {"EmailAddress": "job@example.com"}}]}}',)], 
        ]
        mock_json_loads.return_value = {"Vendor": {"ObjectContacts": [{"Employee": {"EmailAddress": "job@example.com"}}]}}

        self.assertTrue(check_email_exists("job@example.com"))
        mock_json_loads.assert_called_once()
        # Check that INSERT OR REPLACE into email_verification_cache was called
        mock_cursor.execute.assert_any_call("INSERT OR REPLACE INTO email_verification_cache (email, verified, timestamp) VALUES (?, ?, ?)",
                                            ("job@example.com", True, unittest.mock.ANY))
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()


    @patch('Leverancierv2.sqlite3.connect')
    @patch('Leverancierv2.json.loads') # Mock json.loads even if not expected to be called for this path
    def test_check_email_exists_not_found(self, mock_json_loads, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simulate not in email_verification_cache and no jobs in jobs_cache or email not in jobs
        mock_cursor.fetchone.side_effect = [
            None, # Not in verification cache
            []    # No jobs from jobs_cache (fetchall returns empty list)
        ]
        # If the jobs_cache query for data returns empty, json.loads won't be called.
        # If it returns jobs without the email, json.loads would be called.
        # For simplicity here, assuming jobs_cache returns no relevant job data.

        self.assertFalse(check_email_exists("notfound@example.com"))
        mock_json_loads.assert_not_called() # Or assert called if jobs_cache had non-matching entries
        mock_cursor.execute.assert_any_call("INSERT OR REPLACE INTO email_verification_cache (email, verified, timestamp) VALUES (?, ?, ?)",
                                            ("notfound@example.com", False, unittest.mock.ANY))
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    # --- Tests for test_api_connection ---
    @patch('Leverancierv2.requests.get')
    def test_api_connection_success(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response

        is_valid, message = test_api_connection("test.domain.com", "test_api_key")
        self.assertTrue(is_valid)
        self.assertEqual(message, "Verbinding succesvol")
        mock_requests_get.assert_called_once_with(
            "https://test.domain.com/api/v1/object/ProgressStatus",
            headers={"accept": "application/json", "ApiKey": "test_api_key"},
            timeout=10
        )

    @patch('Leverancierv2.requests.get')
    def test_api_connection_failure_401(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Unauthorized"}
        mock_requests_get.return_value = mock_response

        is_valid, message = test_api_connection("test.domain.com", "invalid_key")
        self.assertFalse(is_valid)
        self.assertEqual(message, "Fout 401: Unauthorized")

    @patch('Leverancierv2.requests.get')
    def test_api_connection_failure_no_json(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error Text"
        # Simulate json() raising an error
        mock_response.json.side_effect = json.JSONDecodeError("Error", "doc", 0)
        mock_requests_get.return_value = mock_response

        is_valid, message = test_api_connection("test.domain.com", "key")
        self.assertFalse(is_valid)
        self.assertTrue("Fout 500: Internal Server Error Text" in message)


    @patch('Leverancierv2.requests.get')
    def test_api_connection_request_exception(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.RequestException("Connection Timeout")

        is_valid, message = test_api_connection("test.domain.com", "key")
        self.assertFalse(is_valid)
        self.assertEqual(message, "Uitzondering: Connection Timeout")

    # --- Tests for force_sync ---
    @patch('Leverancierv2.sqlite3.connect')
    def test_force_sync_success(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        result = force_sync()
        self.assertTrue(result)
        mock_cursor.execute.assert_called_once_with("UPDATE sync_control SET force_sync = 1 WHERE id = 1")
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('Leverancierv2.sqlite3.connect')
    def test_force_sync_db_error(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.side_effect = sqlite3.Error("DB Error on force_sync")

        result = force_sync()
        self.assertFalse(result)
        # You might want to add a print to stderr or log in the original function for such errors
        # For now, just asserting the False return based on current implementation

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

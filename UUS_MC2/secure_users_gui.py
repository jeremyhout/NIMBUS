"""
Secure Users Service GUI Client with Authentication
A graphical interface for managing user accounts with login functionality.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import zmq
import json
import threading
from datetime import datetime
import queue
from typing import Optional


class SecureUsersGUI:
    """GUI client for the Secure Users Service with authentication."""
    
    def __init__(self, root):
        """Initialize the GUI."""
        self.root = root
        self.root.title("Secure Users Management System")
        self.root.geometry("900x700")
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # ZMQ setup
        self.context = zmq.Context()
        self.socket = None
        self.connected = False
        self.port = 5556
        
        # Authentication state
        self.session_token = None
        self.current_user = None
        
        # Message queue for thread-safe GUI updates
        self.message_queue = queue.Queue()
        
        # Create main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Start with login screen
        self.show_login_screen()
        
        # Start message processing
        self.process_messages()
        
        # Auto-connect on startup
        self.root.after(100, self.auto_connect)
    
    def auto_connect(self):
        """Auto-connect to service on startup."""
        try:
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)
            self.socket.connect(f"tcp://localhost:{self.port}")
            self.connected = True
            self.add_log("Connected to Secure Users Service", "success")
        except Exception as e:
            self.add_log(f"Connection failed: {str(e)}", "error")
    
    def reconnect(self):
        """Reconnect to the service (reset socket)."""
        try:
            # Close existing socket if any
            if self.socket:
                self.socket.close()
            
            # Create new socket
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)
            self.socket.connect(f"tcp://localhost:{self.port}")
            self.connected = True
            self.add_log("Reconnected to service", "success")
        except Exception as e:
            self.connected = False
            self.add_log(f"Reconnection failed: {str(e)}", "error")
    
    def clear_container(self):
        """Clear all widgets from main container."""
        for widget in self.main_container.winfo_children():
            widget.destroy()
    
    def show_login_screen(self):
        """Display the login/register screen."""
        self.clear_container()
        
        # Create login frame
        login_frame = ttk.Frame(self.main_container)
        login_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Title
        title = ttk.Label(login_frame, text="Secure User Management", 
                         font=('Helvetica', 20, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=30)
        
        # Tab control for Login/Register
        tab_control = ttk.Notebook(login_frame)
        
        # Login Tab
        login_tab = ttk.Frame(tab_control, padding="20")
        tab_control.add(login_tab, text='Login')
        
        ttk.Label(login_tab, text="Username/Email:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.login_username = ttk.Entry(login_tab, width=25)
        self.login_username.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(login_tab, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.login_password = ttk.Entry(login_tab, width=25, show="*")
        self.login_password.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Button(login_tab, text="Login", command=self.login, 
                  width=20).grid(row=2, column=0, columnspan=2, pady=15)
        
        # Register Tab
        register_tab = ttk.Frame(tab_control, padding="20")
        tab_control.add(register_tab, text='Register')
        
        ttk.Label(register_tab, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.reg_username = ttk.Entry(register_tab, width=25)
        self.reg_username.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(register_tab, text="Email:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.reg_email = ttk.Entry(register_tab, width=25)
        self.reg_email.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(register_tab, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.reg_password = ttk.Entry(register_tab, width=25, show="*")
        self.reg_password.grid(row=2, column=1, pady=5, padx=5)
        
        ttk.Label(register_tab, text="Confirm Password:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.reg_confirm_password = ttk.Entry(register_tab, width=25, show="*")
        self.reg_confirm_password.grid(row=3, column=1, pady=5, padx=5)
        
        ttk.Label(register_tab, text="Full Name:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.reg_fullname = ttk.Entry(register_tab, width=25)
        self.reg_fullname.grid(row=4, column=1, pady=5, padx=5)
        
        ttk.Button(register_tab, text="Register", command=self.register, 
                  width=20).grid(row=5, column=0, columnspan=2, pady=15)
        
        tab_control.grid(row=1, column=0, columnspan=2)
        
        # Status/Log area
        log_frame = ttk.LabelFrame(login_frame, text="Status", padding="10")
        log_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        self.login_log = scrolledtext.ScrolledText(log_frame, height=5, width=50, wrap=tk.WORD)
        self.login_log.grid(row=0, column=0)
        
        # Bind Enter key
        self.login_password.bind('<Return>', lambda e: self.login())
        self.reg_confirm_password.bind('<Return>', lambda e: self.register())
    
    def show_dashboard(self):
        """Display the main dashboard after login."""
        self.clear_container()
        
        # Main dashboard frame
        dashboard_frame = ttk.Frame(self.main_container, padding="10")
        dashboard_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(dashboard_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="User Account Management", 
                 font=('Helvetica', 16, 'bold')).pack(side=tk.LEFT)
        
        # User info and logout
        user_info_frame = ttk.Frame(header_frame)
        user_info_frame.pack(side=tk.RIGHT)
        
        self.user_label = ttk.Label(user_info_frame, 
                                   text=f"Logged in as: {self.current_user.get('username', '')}")
        self.user_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(user_info_frame, text="Logout", 
                  command=self.logout).pack(side=tk.LEFT)
        
        # Tab control for different sections
        tab_control = ttk.Notebook(dashboard_frame)
        tab_control.pack(fill=tk.BOTH, expand=True)
        
        # Profile Tab
        profile_tab = ttk.Frame(tab_control)
        tab_control.add(profile_tab, text='My Profile')
        self.create_profile_tab(profile_tab)
        
        # Update Credentials Tab
        credentials_tab = ttk.Frame(tab_control)
        tab_control.add(credentials_tab, text='Update Credentials')
        self.create_credentials_tab(credentials_tab)
        
        # Users List Tab (if admin)
        if self.current_user.get('role') == 'admin':
            users_tab = ttk.Frame(tab_control)
            tab_control.add(users_tab, text='All Users')
            self.create_users_tab(users_tab)
        
        # Settings Tab
        settings_tab = ttk.Frame(tab_control)
        tab_control.add(settings_tab, text='Settings')
        self.create_settings_tab(settings_tab)
        
        # Status bar
        status_frame = ttk.Frame(dashboard_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def create_profile_tab(self, parent):
        """Create the profile tab content."""
        profile_frame = ttk.Frame(parent, padding="20")
        profile_frame.pack(fill=tk.BOTH, expand=True)
        
        # Profile form
        form_frame = ttk.LabelFrame(profile_frame, text="Profile Information", padding="15")
        form_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create form fields
        fields = [
            ('Username:', 'username', True),
            ('Email:', 'email', False),
            ('Full Name:', 'full_name', False),
            ('Phone:', 'phone', False),
            ('Address:', 'address', False),
            ('City:', 'city', False),
            ('Country:', 'country', False),
            ('Postal Code:', 'postal_code', False),
            ('Date of Birth:', 'date_of_birth', False),
        ]
        
        self.profile_entries = {}
        for i, (label, field, readonly) in enumerate(fields):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=3)
            
            entry = ttk.Entry(form_frame, width=30)
            if readonly:
                entry.config(state='readonly')
            
            # Populate with current user data
            value = self.current_user.get(field, '')
            if value:
                entry.insert(0, value)
            
            entry.grid(row=i, column=1, pady=3, padx=10)
            self.profile_entries[field] = entry
        
        # Notes field
        ttk.Label(form_frame, text="Notes:").grid(row=len(fields), column=0, sticky=(tk.W, tk.N), pady=3)
        self.profile_notes = tk.Text(form_frame, width=35, height=4)
        self.profile_notes.grid(row=len(fields), column=1, pady=3, padx=10)
        notes = self.current_user.get('notes', '')
        if notes:
            self.profile_notes.insert(1.0, notes)
        
        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=15)
        
        ttk.Button(button_frame, text="Update Profile", 
                  command=self.update_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh", 
                  command=self.refresh_profile).pack(side=tk.LEFT, padx=5)
        
        # Account info
        info_frame = ttk.LabelFrame(profile_frame, text="Account Information", padding="15")
        info_frame.pack(fill=tk.X)
        
        info_text = f"""
Account Status: {self.current_user.get('status', 'Unknown')}
Role: {self.current_user.get('role', 'user')}
Created: {self.current_user.get('created_at', 'Unknown')[:10]}
Last Updated: {self.current_user.get('updated_at', 'Unknown')[:10]}
Last Login: {self.current_user.get('last_login', 'Never')[:19] if self.current_user.get('last_login') else 'Never'}
        """
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack()
    
    def create_credentials_tab(self, parent):
        """Create the credentials update tab."""
        cred_frame = ttk.Frame(parent, padding="20")
        cred_frame.pack()
        
        # Username change section
        username_frame = ttk.LabelFrame(cred_frame, text="Change Username", padding="15")
        username_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(username_frame, text="New Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.new_username = ttk.Entry(username_frame, width=25)
        self.new_username.grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Button(username_frame, text="Update Username", 
                  command=self.update_username).grid(row=1, column=0, columnspan=2, pady=10)
        
        # Email change section
        email_frame = ttk.LabelFrame(cred_frame, text="Change Email", padding="15")
        email_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(email_frame, text="New Email:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.new_email = ttk.Entry(email_frame, width=25)
        self.new_email.grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Button(email_frame, text="Update Email", 
                  command=self.update_email).grid(row=1, column=0, columnspan=2, pady=10)
        
        # Password change section
        password_frame = ttk.LabelFrame(cred_frame, text="Change Password", padding="15")
        password_frame.pack(fill=tk.X)
        
        ttk.Label(password_frame, text="Current Password:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.current_password = ttk.Entry(password_frame, width=25, show="*")
        self.current_password.grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Label(password_frame, text="New Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.new_password = ttk.Entry(password_frame, width=25, show="*")
        self.new_password.grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Label(password_frame, text="Confirm Password:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.confirm_new_password = ttk.Entry(password_frame, width=25, show="*")
        self.confirm_new_password.grid(row=2, column=1, pady=5, padx=10)
        
        ttk.Button(password_frame, text="Update Password", 
                  command=self.update_password).grid(row=3, column=0, columnspan=2, pady=10)
    
    def create_users_tab(self, parent):
        """Create the users list tab (admin only)."""
        users_frame = ttk.Frame(parent, padding="10")
        users_frame.pack(fill=tk.BOTH, expand=True)
        
        # Refresh button
        ttk.Button(users_frame, text="Refresh Users List", 
                  command=self.load_users_list).pack(pady=10)
        
        # Users treeview
        columns = ('Username', 'Email', 'Full Name', 'Role', 'Status', 'Created')
        self.users_tree = ttk.Treeview(users_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(users_frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=scrollbar.set)
        
        self.users_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load users on tab creation
        self.root.after(100, self.load_users_list)
    
    def create_settings_tab(self, parent):
        """Create the settings tab."""
        settings_frame = ttk.Frame(parent, padding="20")
        settings_frame.pack()
        
        # Account deletion section
        delete_frame = ttk.LabelFrame(settings_frame, text="Delete Account", padding="15")
        delete_frame.pack(fill=tk.X)
        
        warning_text = """
⚠️ Warning: This action is permanent and cannot be undone.
All your data will be permanently deleted.
        """
        
        ttk.Label(delete_frame, text=warning_text, foreground="red").pack(pady=10)
        
        ttk.Label(delete_frame, text="Enter password to confirm:").pack()
        
        self.delete_password = ttk.Entry(delete_frame, width=25, show="*")
        self.delete_password.pack(pady=5)
        
        ttk.Button(delete_frame, text="Delete My Account", 
                  command=self.delete_account,
                  style="Danger.TButton").pack(pady=10)
    
    def login(self):
        """Handle user login."""
        username = self.login_username.get().strip()
        password = self.login_password.get()
        
        if not username or not password:
            self.add_log("Please enter username/email and password", "error")
            return
        
        request = {
            'action': 'login',
            'credentials': {
                'username': username,
                'password': password
            }
        }
        
        def callback(response):
            if response['status'] == 'success':
                self.session_token = response['session_token']
                self.current_user = response['user']
                self.add_log(f"Welcome, {self.current_user['username']}!", "success")
                self.show_dashboard()
            else:
                self.add_log(response.get('message', 'Login failed'), "error")
                messagebox.showerror("Login Failed", response.get('message'))
        
        self.send_request(request, callback)
    
    def register(self):
        """Handle user registration."""
        username = self.reg_username.get().strip().lower()
        email = self.reg_email.get().strip().lower()
        password = self.reg_password.get()
        confirm = self.reg_confirm_password.get()
        full_name = self.reg_fullname.get().strip()
        
        # Validation
        if not username:
            self.add_log("Username is required", "error")
            messagebox.showerror("Invalid Input", "Please enter a username")
            return
            
        if not email:
            self.add_log("Email is required", "error")
            messagebox.showerror("Invalid Input", "Please enter an email address")
            return
            
        if '@' not in email or '.' not in email:
            self.add_log("Invalid email format", "error")
            messagebox.showerror("Invalid Input", "Please enter a valid email address")
            return
            
        if not password:
            self.add_log("Password is required", "error")
            messagebox.showerror("Invalid Input", "Please enter a password")
            return
            
        if len(password) < 6:
            self.add_log("Password must be at least 6 characters", "error")
            messagebox.showerror("Invalid Input", "Password must be at least 6 characters long")
            return
        
        if password != confirm:
            self.add_log("Passwords do not match", "error")
            messagebox.showerror("Password Mismatch", "The passwords you entered do not match")
            return
        
        request = {
            'action': 'create_user',
            'user_data': {
                'username': username,
                'email': email,
                'password': password,
                'full_name': full_name
            }
        }
        
        def callback(response):
            if response['status'] == 'success':
                self.add_log("Registration successful! Please login.", "success")
                messagebox.showinfo("Success", "Account created successfully! Please login.")
                # Clear registration form
                self.reg_username.delete(0, tk.END)
                self.reg_email.delete(0, tk.END)
                self.reg_password.delete(0, tk.END)
                self.reg_confirm_password.delete(0, tk.END)
                self.reg_fullname.delete(0, tk.END)
            else:
                self.add_log(response.get('message', 'Registration failed'), "error")
                messagebox.showerror("Registration Failed", response.get('message'))
        
        self.send_request(request, callback)
    
    def logout(self):
        """Handle user logout."""
        if not self.session_token:
            return
        
        request = {
            'action': 'logout',
            'session_token': self.session_token
        }
        
        def callback(response):
            self.session_token = None
            self.current_user = None
            self.show_login_screen()
            self.add_log("Logged out successfully", "info")
        
        self.send_request(request, callback)
    
    def update_profile(self):
        """Update user profile information."""
        update_data = {}
        
        for field, entry in self.profile_entries.items():
            if field != 'username':  # Username handled separately
                value = entry.get().strip()
                if value != self.current_user.get(field, ''):
                    update_data[field] = value
        
        # Get notes
        notes = self.profile_notes.get(1.0, tk.END).strip()
        if notes != self.current_user.get('notes', ''):
            update_data['notes'] = notes
        
        if not update_data:
            messagebox.showinfo("No Changes", "No changes to update")
            return
        
        request = {
            'action': 'update_user',
            'session_token': self.session_token,
            'update_data': update_data
        }
        
        def callback(response):
            if response['status'] == 'success':
                self.current_user = response['user']
                self.set_status("Profile updated successfully")
                messagebox.showinfo("Success", "Profile updated successfully")
            else:
                self.set_status(f"Update failed: {response.get('message')}")
                messagebox.showerror("Update Failed", response.get('message'))
        
        self.send_request(request, callback)
    
    def update_username(self):
        """Update username."""
        new_username = self.new_username.get().strip()
        
        if not new_username:
            messagebox.showwarning("Invalid Input", "Please enter a new username")
            return
        
        if new_username == self.current_user.get('username'):
            messagebox.showinfo("No Change", "New username is the same as current")
            return
        
        request = {
            'action': 'update_user',
            'session_token': self.session_token,
            'update_data': {'username': new_username}
        }
        
        def callback(response):
            if response['status'] == 'success':
                self.current_user = response['user']
                self.user_label.config(text=f"Logged in as: {self.current_user['username']}")
                self.profile_entries['username'].config(state='normal')
                self.profile_entries['username'].delete(0, tk.END)
                self.profile_entries['username'].insert(0, self.current_user['username'])
                self.profile_entries['username'].config(state='readonly')
                self.new_username.delete(0, tk.END)
                messagebox.showinfo("Success", "Username updated successfully")
            else:
                messagebox.showerror("Update Failed", response.get('message'))
        
        self.send_request(request, callback)
    
    def update_email(self):
        """Update email."""
        new_email = self.new_email.get().strip()
        
        if not new_email:
            messagebox.showwarning("Invalid Input", "Please enter a new email")
            return
        
        request = {
            'action': 'update_user',
            'session_token': self.session_token,
            'update_data': {'email': new_email}
        }
        
        def callback(response):
            if response['status'] == 'success':
                self.current_user = response['user']
                self.profile_entries['email'].delete(0, tk.END)
                self.profile_entries['email'].insert(0, self.current_user['email'])
                self.new_email.delete(0, tk.END)
                messagebox.showinfo("Success", "Email updated successfully")
            else:
                messagebox.showerror("Update Failed", response.get('message'))
        
        self.send_request(request, callback)
    
    def update_password(self):
        """Update password."""
        current = self.current_password.get()
        new = self.new_password.get()
        confirm = self.confirm_new_password.get()
        
        if not all([current, new, confirm]):
            messagebox.showwarning("Invalid Input", "Please fill in all password fields")
            return
        
        if new != confirm:
            messagebox.showerror("Password Mismatch", "New passwords do not match")
            return
        
        request = {
            'action': 'update_user',
            'session_token': self.session_token,
            'update_data': {
                'current_password': current,
                'password': new
            }
        }
        
        def callback(response):
            if response['status'] == 'success':
                self.current_password.delete(0, tk.END)
                self.new_password.delete(0, tk.END)
                self.confirm_new_password.delete(0, tk.END)
                messagebox.showinfo("Success", "Password updated successfully")
            else:
                messagebox.showerror("Update Failed", response.get('message'))
        
        self.send_request(request, callback)
    
    def refresh_profile(self):
        """Refresh profile data from server."""
        request = {
            'action': 'get_user',
            'session_token': self.session_token
        }
        
        def callback(response):
            if response['status'] == 'success':
                self.current_user = response['user']
                # Update profile fields
                for field, entry in self.profile_entries.items():
                    if field != 'username':
                        entry.delete(0, tk.END)
                        value = self.current_user.get(field, '')
                        if value:
                            entry.insert(0, value)
                
                # Update notes
                self.profile_notes.delete(1.0, tk.END)
                notes = self.current_user.get('notes', '')
                if notes:
                    self.profile_notes.insert(1.0, notes)
                
                self.set_status("Profile refreshed")
            else:
                self.set_status(f"Refresh failed: {response.get('message')}")
        
        self.send_request(request, callback)
    
    def load_users_list(self):
        """Load list of all users (admin only)."""
        request = {
            'action': 'list_users',
            'session_token': self.session_token
        }
        
        def callback(response):
            if response['status'] == 'success':
                # Clear tree
                for item in self.users_tree.get_children():
                    self.users_tree.delete(item)
                
                # Add users
                for user in response['users']:
                    self.users_tree.insert('', 'end', values=(
                        user.get('username', ''),
                        user.get('email', ''),
                        user.get('full_name', ''),
                        user.get('role', ''),
                        user.get('status', ''),
                        user.get('created_at', '')[:10]
                    ))
                
                self.set_status(f"Loaded {response['count']} users")
        
        self.send_request(request, callback)
    
    def delete_account(self):
        """Delete user account."""
        password = self.delete_password.get()
        
        if not password:
            messagebox.showwarning("Password Required", "Please enter your password to confirm")
            return
        
        if not messagebox.askyesno("Confirm Deletion", 
                                   "Are you sure you want to delete your account?\n\n"
                                   "This action cannot be undone!"):
            return
        
        request = {
            'action': 'delete_user',
            'session_token': self.session_token,
            'password': password
        }
        
        def callback(response):
            if response['status'] == 'success':
                messagebox.showinfo("Account Deleted", "Your account has been deleted")
                self.session_token = None
                self.current_user = None
                self.show_login_screen()
            else:
                messagebox.showerror("Deletion Failed", response.get('message'))
        
        self.send_request(request, callback)
    
    def send_request(self, request_data, callback=None):
        """Send request to the service."""
        if not self.connected:
            self.add_log("Not connected to service", "error")
            return
        
        def worker():
            try:
                request_json = json.dumps(request_data)
                self.socket.send_string(request_json)
                response_json = self.socket.recv_string()
                response_data = json.loads(response_json)
                
                self.message_queue.put(('response', response_data, callback))
                
            except zmq.error.Again:
                # Timeout occurred - need to reset the socket
                self.message_queue.put(('error', 'Request timeout - reconnecting...', None))
                self.message_queue.put(('reconnect', None, None))
            except Exception as e:
                self.message_queue.put(('error', f'Request failed: {str(e)}', None))
                # Try to reconnect on any socket error
                if "cannot be accomplished" in str(e).lower():
                    self.message_queue.put(('reconnect', None, None))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def process_messages(self):
        """Process messages from the queue."""
        try:
            while not self.message_queue.empty():
                msg_type, msg_data, callback = self.message_queue.get_nowait()
                
                if msg_type == 'response' and callback:
                    callback(msg_data)
                elif msg_type == 'error':
                    self.add_log(msg_data, 'error')
                elif msg_type == 'reconnect':
                    self.reconnect()
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_messages)
    
    def add_log(self, message, msg_type='info'):
        """Add a message to the current log area."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_msg = f"[{timestamp}] {message}\n"
        
        # Try to add to login log if it exists
        try:
            self.login_log.insert(tk.END, formatted_msg)
            self.login_log.see(tk.END)
        except:
            pass
    
    def set_status(self, message):
        """Set status bar message."""
        try:
            self.status_label.config(text=message)
        except:
            pass
    
    def exit_app(self):
        """Exit the application."""
        if self.session_token:
            self.logout()
        
        if self.socket:
            self.socket.close()
        
        if self.context:
            self.context.term()
        
        self.root.quit()


def main():
    """Main entry point."""
    root = tk.Tk()
    app = SecureUsersGUI(root)
    
    def on_closing():
        app.exit_app()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

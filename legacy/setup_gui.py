import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import zipfile
from legacy.installer_support import brand, register_install


def validate_setup(folder, username, password, confirmation):
    target = Path(folder)
    if not target.is_absolute() or str(target).startswith('\\\\') or target == Path(target.anchor):
        raise ValueError('Choose a local folder on this computer, not a drive root or network share.')
    if not username.strip() or len(username.strip()) > 80:
        raise ValueError('Enter an administrator username of 1–80 characters.')
    if len(password) < 6:
        raise ValueError('Use a password with at least 6 characters.')
    if password != confirmation:
        raise ValueError('The passwords do not match.')
    if target.exists() and any(target.iterdir()) and not (target / 'gui-setup-pending.txt').exists():
        raise ValueError('This folder already contains files. Choose a new empty folder. Existing company data must be restored after setup, or updated using COMPANY-INSTALL.md.')
    return target


def extract_payload(payload, target):
    with zipfile.ZipFile(payload) as archive:
        for member in archive.infolist():
            destination = (target / member.filename).resolve()
            if target.resolve() not in destination.parents:
                raise ValueError('Invalid installer archive path.')
            if member.filename.replace('\\', '/').split('/')[0].casefold() in ('data', 'backups', 'restore-recovery'):
                raise ValueError('Installer archive must not contain company data.')
        archive.extractall(target)


def run_logged_setup(command, target, environment, log_name='setup-install.log'):
    log_path = target / log_name
    with log_path.open('wb') as output:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=output,
            stderr=subprocess.STDOUT, cwd=str(target), env=environment,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        detail = log_path.read_bytes().decode('utf-8', errors='replace').strip()
        raise RuntimeError('Setup did not finish. Your files and account are preserved. You can retry with the same folder.\n\n' + detail[-1800:])


def run_install(folder, username, password, payload, progress):
    target = validate_setup(folder, username, password, password)
    target.mkdir(parents=True, exist_ok=True)
    pending = target / 'gui-setup-pending.txt'
    pending.write_text('Installation incomplete; retry setup in this folder.', encoding='utf-8')
    progress('Copying application files…', 20)
    extract_payload(payload, target)
    (target / 'company-installation.txt').write_text('Company setup; preserve data.', encoding='utf-8')
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('KYS_') and key != 'PORT'}
    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    progress('Creating your administrator account…', 45)
    result = subprocess.run([str(target / 'KYS Finance Server.exe'), '--configure-admin-json'],
        input=json.dumps({'username': username.strip(), 'password': password}), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(target), env=environment,
        creationflags=creationflags, timeout=90)
    if result.returncode:
        raise RuntimeError('Administrator setup could not start. On Windows 7, install KB2999226 and KB3063858 and restart. Your files are preserved; retry setup afterwards.')
    progress('Approve the Windows network permission prompt. Creating shortcuts…', 65)
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    run_logged_setup([str(powershell), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        str(target / 'Install Company Server.ps1'), '-AccountConfigured'], target, environment)
    with zipfile.ZipFile(payload) as archive:
        payload_names = [item.filename for item in archive.infolist() if not item.is_dir()]
    register_install(target, 'server', target, payload_names=payload_names)
    pending.unlink()
    progress('Installation complete. Your browser is opening.', 100)


def validate_repair_target(folder):
    target = Path(folder)
    if not target.is_absolute() or not (target / 'KYS Finance Server.exe').is_file():
        raise ValueError('Choose an existing KYS Finance Server folder.')
    if (target / 'setup-complete.txt').is_file():
        return target, False
    manifest_path = target / 'kys-install.json'
    if not (target / 'company-installation.txt').is_file() or not manifest_path.is_file():
        raise ValueError('This is not a recognized installed server. No files were changed.')
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        recognized = (manifest.get('kind') == 'server' and
            os.path.normcase(str(Path(manifest.get('root', '')).resolve())) ==
            os.path.normcase(str(target.resolve())))
    except (ValueError, OSError, TypeError, AttributeError):
        recognized = False
    if not recognized:
        raise ValueError('The server installation manifest does not match this folder. No files were changed.')
    return target, True


def repair_shortcuts(folder, script, progress):
    target, unfinished = validate_repair_target(folder)
    created_marker = False
    marker = target / 'setup-complete.txt'
    if unfinished:
        progress('Checking the administrator account in the unfinished setup…', 25)
        result = subprocess.run([str(target / 'KYS Finance Server.exe'), '--check-admin'],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(target), timeout=90,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError('The unfinished server has no active administrator account. Finish account setup first; no shortcuts or data were changed.')
        marker.write_text('Configured; recovered shortcut setup.', encoding='utf-8')
        created_marker = True
    progress('Repairing shared Desktop and sign-in Startup shortcuts…', 50)
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    try:
        run_logged_setup([str(powershell), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            str(script), '-InstallDirectory', str(target)], target, os.environ.copy(), 'shortcut-repair.log')
    except Exception:
        if created_marker:
            marker.unlink()
        raise
    progress('Shortcuts repaired. Company data and backup files were untouched.', 100)


def main():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    window = tk.Tk()
    window.title('K.Y.S. Finance — Server Setup')
    window.geometry('700x690')
    window.minsize(700, 690)
    window.configure(bg='#F8F7F4')
    style = ttk.Style(window)
    style.theme_use('clam')
    style.configure('TFrame', background='#F8F7F4')
    style.configure('TLabel', background='#F8F7F4', foreground='#243B4A', font=('Segoe UI', 10))
    style.configure('Title.TLabel', font=('Segoe UI', 22, 'bold'))
    style.configure('TButton', font=('Segoe UI', 10), padding=9)
    style.configure('Accent.TButton', background='#4D6878', foreground='white', font=('Segoe UI', 11, 'bold'))
    style.configure('TEntry', padding=7)
    body = ttk.Frame(window, padding=30)
    body.pack(fill='both', expand=True)
    body.columnconfigure(0, weight=1)
    brand(window, body)
    ttk.Label(body, text='K.Y.S. FINANCE  /  COMPANY SERVER', font=('Segoe UI', 10, 'bold')).grid(sticky='w')
    ttk.Label(body, text='Let’s set up your server', style='Title.TLabel').grid(sticky='w', pady=(8, 10))
    ttk.Label(body, text='Install the application and create your private administrator account.\nUse this setup on the server computer.', wraplength=620).grid(sticky='w', pady=(0, 18))
    folder = tk.StringVar(value=str(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'KYS Finance Server'))
    username = tk.StringVar()
    password = tk.StringVar()
    confirmation = tk.StringVar()
    ttk.Label(body, text='Installation folder').grid(sticky='w')
    path_row = ttk.Frame(body)
    path_row.grid(sticky='ew', pady=(5, 12))
    path_row.columnconfigure(0, weight=1)
    path_entry = ttk.Entry(path_row, textvariable=folder)
    path_entry.grid(row=0, column=0, sticky='ew')
    def browse():
        chosen = filedialog.askdirectory(parent=window, title='Choose parent folder')
        if chosen:
            folder.set(str(Path(chosen) / 'KYS Finance Server'))
    browse_button = ttk.Button(path_row, text='Browse…', command=browse)
    browse_button.grid(row=0, column=1, padx=(8, 0))
    controls = [path_entry, browse_button]
    for label, variable, masked in [('Admin username', username, False), ('Password · at least 6 characters', password, True), ('Confirm password', confirmation, True)]:
        ttk.Label(body, text=label).grid(sticky='w')
        field = ttk.Entry(body, textvariable=variable, show='●' if masked else '')
        field.grid(sticky='ew', pady=(5, 10))
        controls.append(field)
    ttk.Label(body, text='Included: Desktop shortcuts · Sign-in auto-start\nPrivate LAN access requires Windows administrator approval.\nIf an existing server works but icons are missing, use Repair shortcuts below.', wraplength=620).grid(sticky='w', pady=(4, 12))
    status = tk.StringVar(value='Ready to install. No default password is created.')
    ttk.Label(body, textvariable=status, wraplength=620).grid(sticky='w', pady=(2, 8))
    bar = ttk.Progressbar(body, maximum=100)
    bar.grid(sticky='ew', pady=(0, 12))
    messages = queue.Queue()
    running = False
    finished = False
    def install():
        nonlocal running
        if finished:
            window.destroy()
            return
        try:
            validate_setup(folder.get(), username.get(), password.get(), confirmation.get())
        except (ValueError, OSError) as error:
            messagebox.showerror('Check setup details', str(error), parent=window)
            return
        arguments = (folder.get(), username.get(), password.get())
        password.set('')
        confirmation.set('')
        running = True
        for control in controls + [install_button, repair_button]:
            control.configure(state='disabled')
        def worker():
            try:
                resource = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'server-payload.zip'
                run_install(*arguments, resource, lambda text, value: messages.put(('progress', text, value)))
                messages.put(('done', '', 100))
            except Exception as error:
                messages.put(('error', str(error), 0))
        threading.Thread(target=worker, daemon=True).start()
    install_button = ttk.Button(body, text='Install K.Y.S. Finance', style='Accent.TButton', command=install)
    install_button.grid(sticky='ew')
    def repair():
        nonlocal running
        if running or finished:
            return
        try:
            target, _ = validate_repair_target(folder.get())
        except (ValueError, OSError) as error:
            messagebox.showerror('Check server folder', str(error), parent=window)
            return
        running = True
        for control in controls + [install_button, repair_button]:
            control.configure(state='disabled')
        def worker():
            try:
                script = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'Create Company Shortcuts.ps1'
                repair_shortcuts(str(target), script, lambda text, value: messages.put(('progress', text, value)))
                messages.put(('repaired', '', 100))
            except Exception as error:
                messages.put(('error', str(error), 0))
        threading.Thread(target=worker, daemon=True).start()
    repair_button = ttk.Button(body, text='Repair existing server shortcuts', command=repair)
    repair_button.grid(sticky='ew', pady=(8, 0))
    def process_messages():
        nonlocal running, finished
        try:
            while True:
                kind, text, value = messages.get_nowait()
                if kind == 'progress':
                    status.set(text)
                    bar['value'] = value
                else:
                    running = False
                    install_button.configure(state='normal')
                    repair_button.configure(state='normal')
                    if kind == 'done':
                        finished = True
                        install_button.configure(text='Finish')
                        status.set('Setup complete. Use Open KYS Finance on your desktop. Auto-start runs after this Windows user signs in.')
                    elif kind == 'repaired':
                        finished = True
                        install_button.configure(text='Finish')
                        repair_button.configure(state='disabled')
                        status.set('Shortcuts repaired. Server data and backups were not changed.')
                    else:
                        status.set('Setup needs attention. Read the message, then retry.')
                        for control in controls:
                            control.configure(state='normal')
                        messagebox.showerror('Setup needs attention', text, parent=window)
        except queue.Empty:
            pass
        window.after(150, process_messages)
    def close():
        if running:
            messagebox.showinfo('Setup is running', 'Please finish the permission prompt and wait for setup to complete.', parent=window)
        else:
            window.destroy()
    window.protocol('WM_DELETE_WINDOW', close)
    process_messages()
    window.mainloop()


if __name__ == '__main__':
    main()

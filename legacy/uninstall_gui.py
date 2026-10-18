"""Manifest-scoped uninstaller; company data is retained unless explicitly selected."""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from legacy.installer_support import brand, PROTECTED

def checked_manifest(folder):
    root = Path(folder).resolve()
    if root == Path(root.anchor) or root == Path.home().resolve():
        raise ValueError('Invalid installation folder.')
    manifest = json.loads((root / 'kys-install.json').read_text(encoding='utf-8'))
    if Path(manifest['root']).resolve() != root or manifest.get('kind') not in ('server', 'client'):
        raise ValueError('Installation identity does not match this folder.')
    files = []
    for name in manifest['files']:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or root not in path.resolve().parents:
            raise ValueError('Unsafe installation manifest.')
        if not relative.parts or ':' in str(relative) or relative.parts[0].casefold() in PROTECTED:
            raise ValueError('Company data cannot be listed as an application file.')
        files.append(path)
    # Reject junctions/symlinks before any cleanup, including data deletion.
    for path in [root] + list(root.rglob('*')):
        if getattr(path.lstat(), 'st_file_attributes', 0) & 1024 or path.is_symlink():
            raise ValueError('Linked folders were found. Uninstall requires manual review.')
    return root, manifest, files

def remove_install(folder, purge=False):
    root, manifest, files = checked_manifest(folder)
    ps = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    script = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'uninstall_cleanup.ps1'
    result = subprocess.run([str(ps), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        str(script), '-InstallDirectory', str(root), '-Kind', manifest['kind'], '-Phase', 'Stop'],
        capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=90)
    if result.returncode:
        raise RuntimeError('Cleanup stopped. Your data is retained.\n' + result.stderr[-1200:])
    # Remove the executable first: a denied/locked server must not leave a
    # partially removed runtime. Preserve manifest and registration on failure.
    files.sort(key=lambda p: p.name.lower() != 'kys finance server.exe')
    for path in files:
        for attempt in range(20):
            try:
                if path.is_file():
                    path.unlink()
                break
            except PermissionError:
                if attempt == 19:
                    raise RuntimeError('Windows cannot remove {}. Close the Finance server, then right-click this uninstaller and choose Run as administrator. Company data has not been selected for deletion yet. The uninstall manifest is retained for retry.'.format(path))
                time.sleep(0.25)
    if purge and manifest['kind'] == 'server':
        for name in PROTECTED:
            target = root / name
            if target.exists():
                shutil.rmtree(str(target))
        target = root / 'backup-target.txt'
        if target.exists():
            target.unlink()
    result = subprocess.run([str(ps), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        str(script), '-InstallDirectory', str(root), '-Kind', manifest['kind'], '-Phase', 'Finalize'],
        capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=90)
    if result.returncode:
        raise RuntimeError('Files removed, but shortcut cleanup needs retry. ' + result.stderr[-1200:])
    (root / 'kys-install.json').unlink()
    for folder in sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if folder.relative_to(root).parts[0].casefold() not in PROTECTED:
            try:
                folder.rmdir()
            except OSError:
                pass
    try:
        root.rmdir()
    except OSError:
        pass

def main():
    import tkinter as tk
    from tkinter import ttk, messagebox
    if '--target' not in sys.argv:
        root = Path(sys.executable).resolve().parent
        checked_manifest(root)
        temporary = Path(tempfile.mkdtemp(prefix='KYS-Uninstall-'))
        launcher = temporary / 'KYS Finance Uninstall.exe'
        shutil.copy2(sys.executable, str(launcher))
        subprocess.Popen([str(launcher), '--target', str(root)], creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return
    root, manifest, _ = checked_manifest(sys.argv[sys.argv.index('--target') + 1])
    time.sleep(1)
    window = tk.Tk()
    window.title('K.Y.S. Finance P&L — Uninstall')
    window.geometry('680x650')
    window.configure(bg='#F8F7F4')
    style = ttk.Style(window)
    style.theme_use('clam')
    for widget in ('TFrame', 'TLabel', 'TCheckbutton'):
        style.configure(widget, background='#F8F7F4', foreground='#243B4A', font=('Segoe UI', 11))
    style.configure('Accent.TButton', background='#4B6575', foreground='white', padding=12)
    body = ttk.Frame(window, padding=30)
    body.pack(fill='both', expand=True)
    body.columnconfigure(0, weight=1)
    brand(window, body)
    ttk.Label(body, text='Uninstall ' + manifest['kind'].title(), font=('Segoe UI', 23, 'bold')).grid(sticky='w', pady=12)
    ttk.Label(body, text='Remove the application, its shortcuts and automatic startup.', wraplength=600).grid(sticky='w')
    ttk.Label(body, text=str(root), wraplength=600).grid(sticky='w', pady=12)
    purge = tk.BooleanVar(value=False)
    if manifest['kind'] == 'server':
        ttk.Checkbutton(body, text='Also delete company data and local backups', variable=purge).grid(sticky='w', pady=16)
        ttk.Label(body, text='Leave unchecked to keep your records. Selecting this permanently removes data, backups and restore-recovery inside this installation. Copies on other PCs or shared folders are not removed.', wraplength=600).grid(sticky='w')
    else:
        ttk.Label(body, text='Your company server and all company records remain available.', wraplength=600).grid(sticky='w', pady=16)
    status = tk.StringVar(value='Ready. Close any open Finance work before continuing.')
    ttk.Label(body, textvariable=status, wraplength=600).grid(sticky='w', pady=20)
    messages = queue.Queue()
    running = False
    finished = False
    def retry_elevated():
        import ctypes
        arguments = subprocess.list2cmdline(['--target', str(root)])
        # Reopen confirmation with purge UNCHECKED; never carry deletion consent
        # silently across a Windows account/elevation boundary.
        result = ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, arguments, str(root), 1)
        if result > 32:
            window.destroy()
        else:
            messagebox.showerror('Windows approval', 'Administrator approval was cancelled or unavailable. No further files were removed.', parent=window)
    def uninstall():
        nonlocal running
        if finished:
            window.destroy()
            return
        if not messagebox.askyesno('Confirm uninstall', 'Uninstall this application?' + ('\n\nPERMANENTLY DELETE all company data and local backups in this folder?' if purge.get() else '\nCompany data and backups will be kept.'), parent=window, default='no'):
            return
        selected = purge.get()
        running = True
        button.configure(state='disabled')
        status.set('Removing application…')
        def worker():
            try:
                remove_install(root, selected)
                messages.put(None)
            except Exception as exc:
                messages.put(str(exc))
        threading.Thread(target=worker, daemon=True).start()
    button = ttk.Button(body, text='Uninstall', style='Accent.TButton', command=uninstall)
    button.grid(sticky='ew')
    elevate_button = ttk.Button(body, text='Retry with Windows administrator approval', command=retry_elevated)
    def poll():
        nonlocal running, finished
        try:
            error = messages.get_nowait()
            running = False
            button.configure(state='normal')
            if error:
                status.set('Uninstall needs attention. You can retry.')
                elevate_button.grid(sticky='ew', pady=8)
                messagebox.showerror('Uninstall', error, parent=window)
            else:
                finished = True
                button.configure(text='Finish')
                status.set('Uninstalled. ' + ('Selected local data was removed.' if purge.get() else 'Company data and backups were retained at ' + str(root)))
        except queue.Empty:
            pass
        window.after(150, poll)
    window.protocol('WM_DELETE_WINDOW', lambda: None if running else window.destroy())
    poll()
    window.mainloop()

if __name__ == '__main__':
    main()

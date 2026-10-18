import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from legacy.installer_support import brand, register_install


def install_client(resources, target, desktop=None, startup=None, skip_monitor=False):
    target.mkdir(parents=True, exist_ok=True)
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    command = [str(powershell), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        str(resources / 'Install KYS Finance Client.ps1'), '-InstallDirectory', str(target)]
    if desktop is not None:
        command.extend(['-DesktopDirectory', str(desktop)])
    if startup is not None:
        command.extend(['-StartupDirectory', str(startup)])
    if skip_monitor:
        command.append('-SkipMonitor')
    log_path = target / 'client-setup.log'
    with log_path.open('wb') as output:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=output,
            stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=60)
    if result.returncode:
        detail = log_path.read_bytes().decode('utf-8', errors='replace')
        raise RuntimeError('Client setup did not finish. You can retry.\n\n' + detail[-1600:])
    if not (target / 'KYS Client.ps1').is_file():
        raise RuntimeError('The client launcher was not installed. Please retry setup.')
    register_install(target, 'client', resources)


def main():
    import tkinter as tk
    from tkinter import messagebox, ttk
    window = tk.Tk()
    window.title('K.Y.S. Finance — Client Setup')
    window.geometry('650x510')
    window.minsize(650, 510)
    window.configure(bg='#F8F7F4')
    style = ttk.Style(window)
    style.theme_use('clam')
    style.configure('TFrame', background='#F8F7F4')
    style.configure('TLabel', background='#F8F7F4', foreground='#243B4A', font=('Segoe UI', 10))
    style.configure('Title.TLabel', font=('Segoe UI', 22, 'bold'))
    style.configure('Accent.TButton', background='#4D6878', foreground='white', font=('Segoe UI', 11, 'bold'), padding=12)
    body = ttk.Frame(window, padding=30)
    body.pack(fill='both', expand=True)
    body.columnconfigure(0, weight=1)
    brand(window, body)
    ttk.Label(body, text='K.Y.S. FINANCE  /  COMPANY CLIENT', font=('Segoe UI', 10, 'bold')).grid(sticky='w')
    ttk.Label(body, text='Connect this computer', style='Title.TLabel').grid(sticky='w', pady=(12, 15))
    ttk.Label(body, text='Use this setup on staff computers connected to the company LAN or Wi-Fi.\nYour company server must be switched on when you open Finance.', wraplength=575).grid(sticky='w', pady=(0, 20))
    ttk.Label(body, text='✓  KYS Finance desktop shortcut\n\n✓  Automatic server discovery\n\n✓  Discovery starts after Windows sign-in', font=('Segoe UI', 11)).grid(sticky='w', pady=(0, 20))
    ttk.Label(body, text='Sign in using the account provided by your administrator.\nAll entries are saved on the company server.\nNo server database or administrator account is created on this PC.', wraplength=575).grid(sticky='w', pady=(0, 20))
    status = tk.StringVar(value='Ready. Windows administrator permission is not required.')
    ttk.Label(body, textvariable=status, wraplength=575).grid(sticky='w', pady=(0, 10))
    progress = ttk.Progressbar(body, mode='indeterminate')
    progress.grid(sticky='ew', pady=(0, 12))
    messages = queue.Queue()
    running = False
    finished = False
    def install():
        nonlocal running
        if finished:
            window.destroy()
            return
        running = True
        button.configure(state='disabled')
        status.set('Installing launcher and creating your shortcuts…')
        progress.start(12)
        def worker():
            try:
                resources = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
                install_client(resources, Path(os.environ['LOCALAPPDATA']) / 'KYS Finance Client')
                messages.put(None)
            except Exception as error:
                messages.put(str(error))
        threading.Thread(target=worker, daemon=True).start()
    button = ttk.Button(body, text='Install K.Y.S. Finance Client', style='Accent.TButton', command=install)
    button.grid(sticky='ew')
    def check_messages():
        nonlocal running, finished
        try:
            error = messages.get_nowait()
            running = False
            progress.stop()
            button.configure(state='normal')
            if error is None:
                finished = True
                progress.configure(mode='determinate', value=100)
                status.set('Ready! Open KYS Finance on your desktop. If the server is off, connect again when it is available.')
                button.configure(text='Finish')
            else:
                status.set('Setup needs attention. Read the message and retry.')
                messagebox.showerror('Client setup', error, parent=window)
        except queue.Empty:
            pass
        window.after(150, check_messages)
    def close():
        if running:
            messagebox.showinfo('Setup is running', 'Please wait for setup to finish.', parent=window)
        else:
            window.destroy()
    window.protocol('WM_DELETE_WINDOW', close)
    check_messages()
    window.mainloop()


if __name__ == '__main__':
    main()

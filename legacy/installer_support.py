"""Shared installer branding and per-user uninstall registration."""
import json
import os
from pathlib import Path
import shutil
import sys

PROTECTED = {'data', 'backups', 'restore-recovery'}

def resources():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1] / 'assets'))

def brand(window, body):
    import tkinter as tk
    from tkinter import ttk
    root = resources()
    icon = root / 'kys-finance-pl.ico'
    if icon.exists():
        window.iconbitmap(str(icon))
    logo = root / 'kys-finance-pl.png'
    if logo.exists():
        picture = tk.PhotoImage(file=str(logo)).subsample(16, 16)
        window.brand_picture = picture
        ttk.Label(body, image=picture).place(relx=1.0, x=-2, y=0, anchor='ne')

def register_install(target, kind, source, payload_names=None):
    import winreg
    target = Path(target).resolve()
    for name in ('KYS Finance Uninstall.exe', 'kys-finance-pl.ico', 'kys-finance-pl.png'):
        origin = Path(source) / name
        if origin.resolve() != (target / name).resolve():
            shutil.copy2(str(origin), str(target / name))
    client_files = {'KYS Client.ps1', 'KYS Finance Uninstall.exe', 'kys-finance-pl.ico',
                    'kys-finance-pl-blue-20261019.ico', 'kys-finance-pl.png', 'client-setup.log'}
    if kind == 'server' and payload_names is None:
        raise ValueError('Server registration requires the shipped payload file list.')
    owned = set(payload_names or client_files)
    owned.update({'KYS Finance Uninstall.exe', 'kys-finance-pl.ico', 'kys-finance-pl.png'})
    files = []
    for name in sorted(owned):
        relative = Path(name)
        if (relative.is_absolute() or '..' in relative.parts or not relative.parts
                or ':' in str(relative) or relative.parts[0].casefold() in PROTECTED):
            raise ValueError('Unsafe application payload path.')
        if (target / relative).is_file():
            files.append(str(relative))
    manifest = {'root': str(target), 'kind': kind, 'files': files}
    (target / 'kys-install.json').write_text(json.dumps(manifest), encoding='utf-8')
    key_name = 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KYSFinance' + kind.title()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_name) as key:
        for name, value in {'DisplayName': 'K.Y.S. Finance P&L — ' + kind.title(),
                            'Publisher': 'K.Y.S. Finance', 'InstallLocation': str(target),
                            'DisplayIcon': str(target / 'kys-finance-pl.ico'),
                            'UninstallString': '"' + str(target / 'KYS Finance Uninstall.exe') + '"'}.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.SetValueEx(key, 'NoModify', 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, 'NoRepair', 0, winreg.REG_DWORD, 1)

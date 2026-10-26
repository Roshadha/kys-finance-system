# KYS Finance — Backup / Restore

## දවසේ වැඩ අවසානයේ backup එකක් ගන්න

1. Administrator account එකෙන් login වෙන්න.
2. Overview → Quick actions → **Back up database** click කරන්න.
3. ඉහළින් එන success/error message එක බලන්න. External backup failed කියලා තිබුණොත් USB/NAS connection එක පරීක්ෂා කරලා නැවත click කරන්න.

මෙය backup copy එකක් ගන්නවා පමණයි. ඇතුළත් කළ data delete හෝ replace වෙන්නේ නැහැ. Backup button එක භාවිත කරන්න company server එක run වෙලා තිබිය යුතුයි.

## Server එකට හානියක් වුණොත් ආරක්ෂාව සඳහා

1. Server PC එකට external USB drive එකක් connect කරන්න, නැත්නම් company NAS share එකක් සූදානම් කරන්න.
2. එහි folder එකක් හදන්න. උදාහරණයක්: `E:\KYS-Backups` (ඔබේ drive letter එක වෙනස් විය හැක).
3. Installed server folder එකේ **Configure External Backup.cmd** open කරන්න.
4. Folder එකේ full path එක ඇතුළත් කරන්න. NAS සඳහා උදාහරණයක්: `\\NAS\FinanceBackups`.
5. App එකේ **Back up database** click කරන්න. External location එකේ `KYS-Finance-Backups` යටතේ අලුත් dated folder එකක් ඇති බව බලන්න.
6. එහි `kys_finance.db` සහ `backup-complete.txt` තිබෙනවාද බලන්න. මුළු dated folder එකම ආරක්ෂිතව තබන්න; hidden `.secret_key` file එකත් confidential ය.

දැනට real USB/NAS destination එකක් ස්වයංක්‍රීයව තෝරා දී නැහැ. ඔබේ company destination එක configure කළ යුතුයි. Server disk එකේම වෙන folder එකක් disaster backup එකක් නොවේ. Server එකත් එක්ක නිතර connect කරලා තියෙන drive එකටත් ransomware හෝ විදුලි හානි බලපාන්න පුළුවන්; වෙන් කරලා තබන දෙවැනි copy එකක් company IT සමඟ සලකා බලන්න.

## Automatic backups වෙන විදිහ

Server installation එකේදී local backup ක්‍රමය ඇතුළත් වේ. වෙන PC එකක shared folder එකට පිටපතක් යැවීමට `Configure External Backup.cmd` හරහා ඒ folder path එක සකස් කළ යුතුයි. Server desktop එකේ **Stop KYS Finance Server** click කළ විට confirmation එකක් පෙන්වා, අලුත් verified backup එකක් ගෙන server එක නවත්වයි. Configured external folder එකක් තිබී එයට backup යැවීම අසාර්ථක වුණොත් server එක නවත්වන්නේ නැහැ. නැවත ආරම්භ කරන්න **KYS Finance Server** shortcut එක භාවිත කරන්න. Windows user නැවත sign in කළ විට auto-start ක්‍රියා කරයි.

- Server ආරම්භයේ සහ default විනාඩි 15කට වරක් local backup ගනී. Adminගේ **Backups** page එකෙන් interval එක විනාඩි 5–1440 අතර වෙනස් කළ හැක.
- `backups` තුළ පසුගිය දින 30ක copies සහ අලුත්ම copies 60 තබයි.
- වෙන PC/shared folder destination එක configure කරලා available නම්, සෑම automatic backup එකකදීම එදින dated folder එක අලුත් data වලින් refresh වේ.
- **Back up database** button එකෙන් වෙනම timestamp සහිත අලුත් external snapshot එකක් ලැබේ. ඒ නිසා දවසේ වැඩ අවසානයේ මේ button එක භාවිත කරන්න.
- External copies දැනට ස්වයංක්‍රීයව මැකෙන්නේ නැහැ; drive එකේ free space පරීක්ෂා කරන්න.
- Server off නම් backup worker එක run නොවේ. Scheduled failures server error log එකේ ලියවේ; manual backup එකේ external failure screen එකේත් පෙන්වයි.

## Backup එකක් restore කරන්න

**Restore කිරීම දැනට තිබෙන data සහ users replace කරයි. Merge කිරීමක් නොවේ.** Backup එක ගත් පසු කළ entries එම snapshot එකේ නැත.

1. Staff සියලු දෙනාට වැඩ නවත්වන්න කියන්න. දැනට තිබෙන data අවශ්‍ය නම් මුලින් backup එකක් ගන්න.
2. Server desktop එකේ **Restore KYS Backup** shortcut එක open කරන්න. නැත්නම් installed folder එකේ **Restore KYS Backup.cmd** run කරන්න.
3. දැනට installed system එකේ Admin username/password ඇතුළත් කරන්න.
4. අවශ්‍ය dated backup folder එකේ `kys_finance.db` තෝරන්න. Local timestamp සහිත `.db` backup එකක්ද තෝරාගත හැක.
5. පෙන්වන transaction count සහ latest transaction date පරීක්ෂා කර Confirm කරන්න.
6. Wizard එක මේ installation එකේ server නවත්වලා, දැනට තිබෙන data වල safety copy එකක් `restore-recovery` යටතේ තබලා restore කරයි.
7. Success message එක close කළ පසු server නැවත ආරම්භ වේ. Backup එකේ තිබුණු username/password වලින් login වෙන්න.
8. Overview, Cash ledger සහ P&L totals පරීක්ෂා කරන්න. Staff නැවත login විය යුතුයි.

Server machine එක නැතිවුණොත්: replacement PC එකේ compatible company package එක install කර අලුත් local admin account එක සකස් කරන්න. External backup එක එම PC එකට ලබාදී ඉහත Restore ක්‍රමය භාවිත කරන්න. වෙන database version එකක් නම් wizard එක refuse කළ හැක; migration අවශ්‍ය වේ. `.secret_key` අතින් copy කිරීම අවශ්‍ය නැහැ.

## මේ release එකේ පරීක්ෂා කළේ මොනවාද?

2026-10-14: isolated automated checks වලින් simultaneous HTTP clients 4ක් entries 12ක් (Rs. 1,200.00) එකතු කිරීම, verified external-folder simulation backup එකක් ගැනීම, restore engine එකෙන් වෙනම database එකකට restore කිරීම, login සහ report/Excel totals නැවත Rs. 1,200.00 බව පරීක්ෂා කරයි. Corrupt backup rejection, safety copies සහ restore failure rollback tests ද ඇත.

මෙය real USB/NAS, company PCs කිහිපයක්, හෝ Windows 7 GUI installer/reboot acceptance test එකකට සමාන නොවේ. Company handover එකට පෙර ඒ tests තවම අවශ්‍යයි. Windows startup shortcut එක ක්‍රියාත්මක වන්නේ configured Windows user **sign in කළ පසුවයි**, sign-in කිරීමට පෙර නොවේ.

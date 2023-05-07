from PyInstaller.utils.hooks import collect_all

all = collect_all('xgridfit')
datas = all[0]
hiddenimports = all[2]
hiddenimports += ['yaml']

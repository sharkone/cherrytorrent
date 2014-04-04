# -*- mode: python -*-
a = Analysis(['cherrytorrent.py'],
             pathex=['/Users/sharkone/Documents/Code/cherrytorrent'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='cherrytorrent',
          debug=False,
          strip=None,
          upx=True,
          console=True )

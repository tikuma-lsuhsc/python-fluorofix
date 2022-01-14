# -*- mode: python ; coding: utf-8 -*-

import os

# gather dependent binary files
from ffmpegio.ffmpeg import FFMPEG_BIN as FFmpegBinary, FFPROBE_BIN as FFprobeBinary
print(FFmpegBinary)

block_cipher = None
Key = ['mkl', 'libopenblas']

# binaries = [*[(p, ".") for p in (FFmpegBinary,FFprobeBinary)]]
#binaries = [(p, ".") for p in (FFmpegBinary,FFprobeBinary)]
binaries = []
print(binaries)

def remove_from_list(input, keys):
    outlist = []
    for item in input:
        name, _, _ = item
        flag = 0
        for key_word in keys:
            if name.find(key_word) > -1:
                flag = 1
        if flag != 1 or name == 'mkl_intel_thread.dll':
            outlist.append(item)
    return outlist


a = Analysis(['fluorofix.py'],
             pathex=['C:\\Users\\tikum\\Documents\\Research\\fluorofix'],
             binaries=binaries,
             datas=[],
             hiddenimports=['pkg_resources.py2_warn'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['mkl'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

#a.binaries = remove_from_list(a.binaries, Key)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='fluorofix',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          #upx_exclude=['vcruntime140.dll'],
          runtime_tmpdir=None,
          console=True)

@SET name=fluorofix
@SET opt=onefile
REM @SET opt=onedir
pyinstaller --clean --noconfirm %name%.%opt%.spec

import PyInstaller.__main__

PyInstaller.__main__.run([
    'main.py',
    '--name=QuanQuan VFP', # Name for .exe
    '--distpath=dist',  
    '--add-data=./bg.png;.//assets/img/bg.png', # Icon to replace tkinter feather
    '--add-data=./applogo.png;.//assets/img/applogo.png', # An image used in the app
    '--clean',
    '--onefile',
    '--windowed',
    '--noconsole',
], )
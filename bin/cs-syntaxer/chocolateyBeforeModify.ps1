$packageName = 'CS-Syntaxer'

# stop "syntaxer" first so it does not interfere with the installation
Stop-Process -Name "syntaxer" -ErrorAction SilentlyContinue

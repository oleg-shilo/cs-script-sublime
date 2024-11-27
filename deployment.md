*************** CS-Script ******************
.NET:      v9.0.100
CS-Script: v4.8.18.0
Syntaxer:  v3.1.1.0
---
CS-Script (script engine): C:\Users\oleg\AppData\Roaming\Sublime Text 3\Packages\User\cs-script\cs-script_v1.4.0\cscs.dll
Syntaxer (C# syntax server): C:\Users\oleg\AppData\Roaming\Sublime Text 3\Packages\User\cs-script\syntaxer_v1.4.0\syntaxer.dll
---

Environment requirements and setup instructions:
  https://github.com/oleg-shilo/cs-script/wiki/CLI-Environment-Specification

Use "right-click > CS-Script > Settings > Plugin Config" if you need to change the location of the integrated CS-Script engine and syntaxer manually.

======================

It is recommended that you install CS-Script so you can manage its updates independently from 
the plugin releases (e.g. update with new .NET version).

Installation:
1. Install tools
  - Script engine: `dotnet tool install --global cs-script.cli`
  - Syntaxer: `dotnet tool install --global cs-syntaxer`

2. Configure tools
   Execute plugin command "cs-script: Detect external CS-Script"

Note: you need to have .NET SDK installed for using CS-Script (see https://dotnet.microsoft.com/en-us/download) 

**********************************************
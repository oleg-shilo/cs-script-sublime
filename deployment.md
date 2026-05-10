*************** CS-Script ******************
.NET:      v10.0.203
CS-Script: v4.14.5.0
Syntaxer:  v3.2.7.0
---
CS-Script (script engine): C:\Users\<user>\.dotnet\tools\.store\cs-script.cli\4.14.5\cs-script.cli\4.14.5\tools\net10.0\any\cscs.dll
Syntaxer (C# syntax server): C:\Users\<user>\.dotnet\tools\.store\cs-syntaxer\3.2.7\cs-syntaxer\3.2.7\tools\net10.0\any\syntaxer.dll
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
  If the binaries are locked you can release them by these commands:
  css -list kill *
  syntaxer -list kill *

2. Configure tools
   Execute plugin command "cs-script: Detect external CS-Script"

Note: you need to have .NET SDK installed for using CS-Script (see https://dotnet.microsoft.com/en-us/download) 

**********************************************
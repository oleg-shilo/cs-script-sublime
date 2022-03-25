$packageName = 'CS-Syntaxer'
$url = 'https://github.com/oleg-shilo/syntaxer.core/releases/download/v3.1.0.0-choco-updatate/syntaxer.7z'

Stop-Process -Name "syntaxer" -ErrorAction SilentlyContinue

$installDir = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
Install-ChocolateyEnvironmentVariable 'CSSYNTAXER_ROOT' $installDir User

$checksum = '4FA01054B3091A4068F829459BF29B80052ECDFDC86A797E9A4CE42DE38131E3'
$checksumType = "sha256"

# Download and unpack a zip file
Install-ChocolateyZipPackage "$packageName" "$url" "$installDir" -checksum $checksum -checksumType $checksumType

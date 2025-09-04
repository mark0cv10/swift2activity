$antlr = "antlr-4.13.2-complete.jar"
if (-not (Test-Path $antlr)) {
  Invoke-WebRequest -Uri https://www.antlr.org/download/antlr-4.13.2-complete.jar -OutFile $antlr
}
New-Item -ItemType Directory -Force generated | Out-Null

Push-Location grammars
java -Xmx500M -cp "..\$antlr" org.antlr.v4.Tool `
  -Dlanguage=Python3 -visitor -o "..\generated" Swift3.g4
Pop-Location

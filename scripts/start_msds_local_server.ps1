param(
  [string]$Page = "index.html",
  [int]$Port = 8765,
  [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$allowedPages = @("index.html", "review.html")
if ($allowedPages -notcontains $Page) {
  throw "Unsupported page: $Page"
}

function Get-FreePort {
  param([int]$StartPort)

  for ($candidate = $StartPort; $candidate -lt ($StartPort + 50); $candidate++) {
    $listener = $null
    try {
      $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Parse("127.0.0.1"), $candidate)
      $listener.Start()
      return $candidate
    } catch {
      continue
    } finally {
      if ($listener) {
        $listener.Stop()
      }
    }
  }

  throw "No free local port found."
}

function Get-ContentType {
  param([string]$Path)

  switch ([System.IO.Path]::GetExtension($Path).ToLowerInvariant()) {
    ".html" { return "text/html; charset=utf-8" }
    ".css" { return "text/css; charset=utf-8" }
    ".js" { return "text/javascript; charset=utf-8" }
    ".json" { return "application/json; charset=utf-8" }
    ".pdf" { return "application/pdf" }
    ".png" { return "image/png" }
    ".jpg" { return "image/jpeg" }
    ".jpeg" { return "image/jpeg" }
    ".svg" { return "image/svg+xml" }
    ".ico" { return "image/x-icon" }
    default { return "application/octet-stream" }
  }
}

function Write-Ascii {
  param(
    [System.IO.Stream]$Stream,
    [string]$Text
  )

  $bytes = [System.Text.Encoding]::ASCII.GetBytes($Text)
  $Stream.Write($bytes, 0, $bytes.Length)
}

function Send-TextResponse {
  param(
    [System.IO.Stream]$Stream,
    [string]$Method,
    [int]$StatusCode,
    [string]$StatusText,
    [string]$Text
  )

  $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
  $header = "HTTP/1.1 $StatusCode $StatusText`r`nContent-Type: text/plain; charset=utf-8`r`nContent-Length: $($bytes.Length)`r`nCache-Control: no-store`r`nConnection: close`r`n`r`n"
  Write-Ascii -Stream $Stream -Text $header
  if ($Method -ne "HEAD") {
    $Stream.Write($bytes, 0, $bytes.Length)
  }
}

function Send-FileResponse {
  param(
    [System.IO.Stream]$Stream,
    [string]$Method,
    [string]$Path
  )

  $fileInfo = Get-Item -LiteralPath $Path
  $header = "HTTP/1.1 200 OK`r`nContent-Type: $(Get-ContentType $Path)`r`nContent-Length: $($fileInfo.Length)`r`nCache-Control: no-store`r`nConnection: close`r`n`r`n"
  Write-Ascii -Stream $Stream -Text $header

  if ($Method -ne "HEAD") {
    $fileStream = [System.IO.File]::OpenRead($Path)
    try {
      $buffer = New-Object byte[] 65536
      while (($read = $fileStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
        $Stream.Write($buffer, 0, $read)
      }
    } finally {
      $fileStream.Close()
    }
  }
}

function Get-LocalPathFromRequest {
  param([string]$Target)

  $targetPath = ($Target -split "\?")[0]
  $requestPath = [System.Uri]::UnescapeDataString($targetPath.TrimStart("/"))
  if ([string]::IsNullOrWhiteSpace($requestPath)) {
    $requestPath = $Page
  }

  $requestPath = $requestPath -replace "/", [System.IO.Path]::DirectorySeparatorChar
  $localPath = [System.IO.Path]::GetFullPath((Join-Path $root $requestPath))
  $rootPath = [System.IO.Path]::GetFullPath($root).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
  $rootPrefix = $rootPath + [System.IO.Path]::DirectorySeparatorChar

  if (
    -not $localPath.Equals($rootPath, [System.StringComparison]::OrdinalIgnoreCase) -and
    -not $localPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)
  ) {
    return $null
  }

  if (Test-Path -LiteralPath $localPath -PathType Container) {
    $localPath = Join-Path $localPath "index.html"
  }

  return $localPath
}

$Port = Get-FreePort -StartPort $Port
$server = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Parse("127.0.0.1"), $Port)
$server.Start()

$url = "http://127.0.0.1:$Port/$Page"
Write-Host ""
Write-Host "MSDS local site is running."
Write-Host "Open page: $url"
Write-Host "Project root: $root"
Write-Host ""
Write-Host "Keep this window open while using the MSDS site."
Write-Host "Close this window or press Ctrl+C to stop."
Write-Host ""
if (-not $NoOpen) {
  Start-Process $url
}

try {
  while ($true) {
    $client = $server.AcceptTcpClient()
    try {
      $stream = $client.GetStream()
      $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::ASCII, $false, 8192, $true)
      $requestLine = $reader.ReadLine()

      if ([string]::IsNullOrWhiteSpace($requestLine)) {
        Send-TextResponse -Stream $stream -Method "GET" -StatusCode 400 -StatusText "Bad Request" -Text "Bad request"
        continue
      }

      while (($line = $reader.ReadLine()) -ne $null -and $line -ne "") {
        # Drain request headers.
      }

      $parts = $requestLine -split " "
      if ($parts.Count -lt 2) {
        Send-TextResponse -Stream $stream -Method "GET" -StatusCode 400 -StatusText "Bad Request" -Text "Bad request"
        continue
      }

      $method = $parts[0].ToUpperInvariant()
      $target = $parts[1]
      if ($method -ne "GET" -and $method -ne "HEAD") {
        Send-TextResponse -Stream $stream -Method $method -StatusCode 405 -StatusText "Method Not Allowed" -Text "Method not allowed"
        continue
      }

      $localPath = Get-LocalPathFromRequest -Target $target
      if (-not $localPath) {
        Send-TextResponse -Stream $stream -Method $method -StatusCode 403 -StatusText "Forbidden" -Text "Forbidden"
        continue
      }

      if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
        Send-TextResponse -Stream $stream -Method $method -StatusCode 404 -StatusText "Not Found" -Text "Not found"
        continue
      }

      Send-FileResponse -Stream $stream -Method $method -Path $localPath
    } catch {
      try {
        if ($stream) {
          Send-TextResponse -Stream $stream -Method "GET" -StatusCode 500 -StatusText "Internal Server Error" -Text "Local server error"
        }
      } catch {
        # Client may have disconnected.
      }
    } finally {
      $client.Close()
    }
  }
} finally {
  $server.Stop()
}

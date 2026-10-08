# Dual-Mode Networking & Connection Architecture

Song Chord Analyzer features a **dual-mode networking architecture** allowing Android devices to communicate with the host laptop server seamlessly in any environment.

```mermaid
flowchart TD
    subgraph MobileDevice["Android Phone (Flutter App)"]
        ClientService["ServerConfigService"]
    end

    subgraph Modes["Connection Modes"]
        LocalMode["1. Local LAN Mode (Home Wi-Fi / Hotspot)"]
        RemoteMode["2. Remote Internet Mode (Cellular 4G/5G)"]
        AutoMode["3. Auto Failover Mode"]
    end

    subgraph HostLaptop["Host Laptop / PC (FastAPI Server)"]
        LocalPort["http://192.168.x.x:8000 (LAN Listener)"]
        TunnelClient["tools/cloudflared.exe (Encrypted Proxy)"]
        FastAPICore["FastAPI REST Engine (127.0.0.1:8000)"]
    end

    ClientService -->|User Selects| LocalMode
    ClientService -->|User Selects| RemoteMode
    ClientService -->|User Selects| AutoMode

    LocalMode -->|Direct HTTP Traffic| LocalPort
    RemoteMode -->|Public HTTPS (*.trycloudflare.com)| TunnelClient
    AutoMode -->|1.5s Probe: Success| LocalPort
    AutoMode -->|1.5s Probe: Timeout| TunnelClient

    LocalPort --> FastAPICore
    TunnelClient --> FastAPICore
```

---

## 1. Connection Mode Technical Details

### 1.1 Mode 1: Local Network Mode (LAN / Wi-Fi)
- **Transport:** Standard HTTP over local IPv4 private addresses (`http://192.168.x.x:8000`).
- **Use Case:** Home, rehearsal space, or studio where phone and laptop share the same Wi-Fi router or phone mobile hotspot.
- **Internet Requirement:** **Zero Internet Required.** Operates 100% offline as long as the local network links phone and PC.
- **Latency:** Extremely low ($5 	ext{ ms} - 25 	ext{ ms}$).
- **Upload Speed:** Maximum local Wi-Fi throughput (a 10 MB audio file transfers in $< 1 	ext{ second}$).
- **Windows Firewall Configuration:**
  If connection is blocked, allow inbound TCP traffic on port 8000:
  ```powershell
  netsh advfirewall firewall add rule name="Song Chord Analyzer Backend" dir=in action=allow protocol=TCP localport=8000
  ```

### 1.2 Mode 2: Remote Internet Mode (Cloudflare Tunnel)
- **Transport:** Encrypted TLS (HTTPS) over Cloudflare's global edge network (`https://*.trycloudflare.com`).
- **Use Case:** Away from home, traveling, or using mobile cellular data (4G/5G).
- **Tool:** Bundled static binary [`tools/cloudflared.exe`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/tools/cloudflared.exe).
- **Execution Script:** [`scripts/start_tunnel.bat`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/scripts/start_tunnel.bat).
  ```cmd
  cloudflared.exe tunnel --url http://127.0.0.1:8000
  ```
- **How It Works:** `cloudflared` creates an outbound encrypted QUIC/HTTP2 tunnel from the laptop to Cloudflare's nearest edge node and assigns an ephemeral public URL. Requests to this URL are routed over the tunnel directly to the laptop's local port 8000 without requiring port forwarding, static IPs, or router changes.
- **Security & Privacy:** No router ports are opened to the public internet. All traffic is encrypted end-to-end. Optional `X-API-Key` authentication prevents unauthorized compute usage.
- **Crucial Fact:** **The laptop still performs 100% of the computation.** Cloudflare acts purely as an encrypted transport layer. If the laptop is asleep or disconnected, remote requests fail.

### 1.3 Mode 3: Auto Connection Mode
- **Mechanism:**
  1. The app issues an asynchronous probe request to `GET /api/health` at the configured Local URL with a **1.5-second timeout**.
  2. If the local server responds with HTTP 200, the app binds to the Local LAN connection (prioritizing high speed and zero internet dependency).
  3. If the local probe times out or fails (indicating the user has left the home network), the app seamlessly switches to the Remote Tunnel URL.
  4. The active connection mode is displayed as a visual badge on the home screen banner.

---

## 2. Real-Time Connection Diagnostics

In the mobile **Settings Screen** (`mobile/flutter_app/lib/screens/settings_screen.dart`):
- Tapping **"Test Connection"** executes a round-trip diagnostic against `/api/health`.
- The app measures exact network latency in milliseconds.
- Displays hardware telemetry returned by the server:
  - Host GPU model (e.g. `NVIDIA GeForce RTX 3050 Laptop GPU`).
  - VRAM available (`5,161 MB / 6,143 MB`).
  - Device analysis engine status (`WindowsAnalysisEngine`).

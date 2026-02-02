# ZKTeco C2-260 API FUNCTIONS

## 🌐 API Endpoints

### 📥 PUSH SDK (Device → Server)

| Method | Endpoint | Description |
|--------|---------|-------------|
| `GET/POST` | `/iclock/cdata` | Device data synchronization |
| `POST` | `/iclock/registry` | Device registration |
| `GET/POST` | `/iclock/push` | Push configuration |
| `GET` | `/iclock/getrequest` | Get pending commands |
| `POST` | `/iclock/devicecmd` | Command execution result |
| `GET` | `/iclock/ping` | Device heartbeat |
| `POST` | `/iclock/querydata` | Data query response |

### 🚀 API (Server → Device)

| Method | Endpoint | Description | Parameters |
|--------|---------|-------------|------------|
| `GET` | `/` | API health check | — |
| `GET` | `/status` | Get SDK status | — |
| `GET` | `/check-users` | Fetch all users & cards | `sn` (device serial number) |
| `POST` | `/open/` | Open turnstile | `sn`, `seconds`, `door` |
| `POST` | `/cmd` | Send raw command | `sn`, `cmd` |
| `POST` | `/passage` | Toggle passage mode | `sn`, `mode=on/off` |
| `POST` | `/add-card` | Add user & card | `sn`, `cardno`, `starttime`, `endtime`, `name`, `pin` (optional) |
| `POST` | `/delete-user` | Delete user(s) | `sn`, `pin` (optional, `None` = delete all) |

## 📝 Notes
- Devices must register first via `/iclock/registry` before communication.
- Commands are queued and pulled by devices using `/iclock/getrequest`.
- Card numbers in hex must be 8 characters (zero-padded if needed).


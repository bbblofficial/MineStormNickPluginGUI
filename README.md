# MineStormJoinBook

Shows a clickable **GUI book** on join. Built for **Spigot 1.8.x**.

**Created by Muvixo.**

## Features
- Opens a written book GUI on join (default: every join)
- Clickable buttons that run commands + hover tooltips
- `/minestormjoinbook` (`/msjb`, `/joinbook`) admin command
- LuckPerms-friendly permissions; **OP = full perm bypass**
- `messages.yml` + `gui.yml` for full text customization
- `/msjb creator` prints `Created by Muvixo`
- Auto-built on GitHub Actions for JDK 8, 17, 21, 25

## Commands
| Command | Description |
|---|---|
| `/msjb help` | Show help |
| `/msjb reload` | Reload config, messages.yml, gui.yml |
| `/msjb open [player]` | Open the book (self or other) |
| `/msjb reset <player>` | Reset a player |
| `/msjb resetall` | Reset all tracked players |
| `/msjb list` | List players who've seen the book |
| `/msjb info` | Plugin info |
| `/msjb creator` | Show plugin creator |

## Permissions
| Node | Default |
|---|---|
| `minestormjoinbook.admin` | op |
| `minestormjoinbook.reload` | op |
| `minestormjoinbook.open` | true |
| `minestormjoinbook.open.other` | op |
| `minestormjoinbook.reset` | op |
| `minestormjoinbook.resetall` | op |
| `minestormjoinbook.list` | op |
| `minestormjoinbook.info` | true |
| `minestormjoinbook.creator` | true |
| `minestormjoinbook.see` | true |

## Build locally
```bash
mvn clean package
```
Output: `target/MineStormJoinBook-1.0.0.jar`

## GitHub Actions
Push to GitHub; workflow builds for JDK 8, 17, 21, 25 and uploads jars as
artifacts.

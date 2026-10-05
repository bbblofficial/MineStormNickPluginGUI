# MineStormJoinBook

Clickable GUI book on join for Spigot **1.8.x**. **Created by Muvixo.**

## Features
- Book GUI on join (default: every join)
- Clickable buttons + hover tooltips
- `/minestormjoinbook` (`/msjb`, `/joinbook`) admin command
- LuckPerms-friendly permissions; **OP = full perm bypass**
- `messages.yml` + `gui.yml` fully customizable
- `/msjb creator` → `Created by Muvixo`
- Built on GitHub Actions for **JDK 8, 17, 21, 25**

## Build (local)
You must have Spigot 1.8.8 in your local Maven repo. Easiest way:
```bash
java -jar BuildTools.jar --rev 1.8.8
mvn clean package
```
Output: `target/MineStormJoinBook-1.0.0.jar`

## Build (GitHub Actions)
Just push. The workflow:
1. Builds Spigot 1.8.8 once with **BuildTools** (cached between runs).
2. Builds the plugin on **JDK 8, 17, 21, 25** and uploads a jar for each.

## Why BuildTools?
Spigot doesn't distribute prebuilt 1.8.8 jars publicly, and the community
mirrors that used to host them are no longer reliably resolvable from
GitHub-hosted runners. BuildTools produces the exact artifact locally,
and we cache it so the CI stays fast.

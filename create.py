
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fixer.py — Rebuild MineStormJoinBook to work with a CI that uses BuildTools
===========================================================================

WHY
---
Spigot does NOT publish prebuilt 1.8.8 jars on their public Nexus, and the
community mirrors we tried (minebench, neylz) are NOT resolvable from
GitHub-hosted runners ("Name or service not known").

SOLUTION
--------
Build Spigot 1.8.8 locally with BuildTools inside the GitHub Actions job,
install it into the local Maven repo, and depend on it as `provided`.
This is the standard, 100%-offline-after-cache way to compile a 1.8.8
NMS plugin on CI.

WHAT THIS SCRIPT DOES
---------------------
1. Rewrites `pom.xml` to:
   - Not declare any custom repositories for spigot (only Maven Central).
   - Depend on `org.spigotmc:spigot:1.8.8-R0.1-SNAPSHOT` (installed by CI).
2. Rewrites `.github/workflows/build.yml` to:
   - Run once with JDK 8 to build Spigot 1.8.8 via BuildTools.
   - Cache the built jar in ~/.m2 between runs.
   - Build the plugin on JDK 8 / 17 / 21 / 25 using that cached Spigot.
3. Re-writes all resources and Java source with the full feature set.
"""

import os
import shutil

ROOT = "."
PACKAGE = "com.muvixo.minestormjoinbook"
PACKAGE_PATH = PACKAGE.replace(".", "/")
SRC = os.path.join("src", "main", "java", PACKAGE_PATH)
RES = os.path.join("src", "main", "resources")
WF = os.path.join(".github", "workflows")

# ============================================================
# pom.xml (no custom repos for Spigot — CI installs it locally)
# ============================================================
POM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.muvixo</groupId>
    <artifactId>MineStormJoinBook</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>

    <properties>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <maven.compiler.source>1.8</maven.compiler.source>
        <maven.compiler.target>1.8</maven.compiler.target>
    </properties>

    <dependencies>
        <!-- Installed by BuildTools in CI (or locally) into ~/.m2 -->
        <dependency>
            <groupId>org.spigotmc</groupId>
            <artifactId>spigot</artifactId>
            <version>1.8.8-R0.1-SNAPSHOT</version>
            <scope>provided</scope>
        </dependency>
        <dependency>
            <groupId>io.netty</groupId>
            <artifactId>netty-all</artifactId>
            <version>4.0.23.Final</version>
            <scope>provided</scope>
        </dependency>
    </dependencies>

    <build>
        <finalName>${project.artifactId}-${project.version}</finalName>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.13.0</version>
                <configuration>
                    <source>1.8</source>
                    <target>1.8</target>
                    <encoding>UTF-8</encoding>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-jar-plugin</artifactId>
                <version>3.4.2</version>
            </plugin>
        </plugins>
        <resources>
            <resource>
                <directory>src/main/resources</directory>
                <filtering>true</filtering>
            </resource>
        </resources>
    </build>
</project>
"""

# ============================================================
# plugin.yml
# ============================================================
PLUGIN_YML = """name: MineStormJoinBook
version: 1.0.0
main: com.muvixo.minestormjoinbook.MineStormJoinBookPlugin
author: Muvixo
description: Shows a clickable GUI book on join. Created by Muvixo.
api-version: 1.8
commands:
  minestormjoinbook:
    description: MineStormJoinBook admin command
    usage: /minestormjoinbook <reload|open|reset|resetall|list|info|creator|help>
    aliases: [msjb, joinbook]
permissions:
  minestormjoinbook.admin:
    description: Full admin access
    default: op
    children:
      minestormjoinbook.reload: true
      minestormjoinbook.open: true
      minestormjoinbook.open.other: true
      minestormjoinbook.reset: true
      minestormjoinbook.resetall: true
      minestormjoinbook.list: true
      minestormjoinbook.info: true
      minestormjoinbook.creator: true
  minestormjoinbook.reload: { default: op }
  minestormjoinbook.open: { default: true }
  minestormjoinbook.open.other: { default: op }
  minestormjoinbook.reset: { default: op }
  minestormjoinbook.resetall: { default: op }
  minestormjoinbook.list: { default: op }
  minestormjoinbook.info: { default: true }
  minestormjoinbook.creator: { default: true }
  minestormjoinbook.see: { default: true }
"""

# ============================================================
# config.yml
# ============================================================
CONFIG_YML = """only-once: false
open-delay-ticks: 20
open-sound: "ITEM_BOOK_PAGE_TURN"
manual-open-ignores-once: true
respect-see-permission: true
"""

# ============================================================
# messages.yml
# ============================================================
MESSAGES_YML = """prefix: "&8[&6MineStorm&8] &r"
no-permission: "%prefix%&cYou don't have permission."
player-only: "%prefix%&cOnly players can use this."
player-not-found: "%prefix%&cPlayer &e%player% &cnot found."
unknown-command: "%prefix%&cUnknown subcommand. Try &e/msjb help&c."
invalid-usage: "%prefix%&cUsage: &e%usage%"
reload-success: "%prefix%&aConfiguration reloaded."
reload-failed: "%prefix%&cReload failed: &e%error%"
open-self: "%prefix%&aOpening the book GUI..."
open-other: "%prefix%&aOpened the book for &e%player%&a."
open-target: "%prefix%&aA book GUI was opened for you."
open-failed: "%prefix%&cCould not open the book for &e%player%&c."
reset-success: "%prefix%&e%player% &awill see the book again."
reset-not-seen: "%prefix%&e%player% &ehas not seen it yet."
resetall-success: "%prefix%&aReset &e%count% &aplayer(s)."
resetall-empty: "%prefix%&eNo players to reset."
list-header: "%prefix%&6Seen (&e%count%&6):"
list-entry: "&8 - &e%player%"
list-empty: "%prefix%&eNobody has seen the book yet."
info-header: "%prefix%&6MineStormJoinBook &7v%version%"
info-line: "&7Author: &e%author%"
info-seen: "&7Tracked: &e%count%"
info-once: "&7Only once: &e%once%"
info-delay: "&7Delay: &e%delay% &7ticks"
creator: "%prefix%&6Created by &e&lMuvixo"
help-header: "%prefix%&6MineStormJoinBook commands:"
help-line: "&e%usage% &7- %description%"
usage-reload: "/msjb reload"
usage-open: "/msjb open [player]"
usage-reset: "/msjb reset <player>"
usage-resetall: "/msjb resetall"
usage-list: "/msjb list"
usage-info: "/msjb info"
usage-creator: "/msjb creator"
usage-help: "/msjb help"
desc-reload: "Reload config, messages.yml and gui.yml"
desc-open: "Open the book GUI (self or others)"
desc-reset: "Reset a player"
desc-resetall: "Reset all tracked players"
desc-list: "List players who have seen the book"
desc-info: "Show plugin info"
desc-creator: "Show the plugin creator"
desc-help: "Show this help"
"""

# ============================================================
# gui.yml
# ============================================================
GUI_YML = """book:
  title: "&6Gamemodes"
  author: "Server"
  header: "&6&lWELCOME"
  subtitle: "&7Choose a gamemode:"
  button-format: "&0&r%display%"

gamemodes:
  survival:
    display: "&a&lSurvival"
    command: "server survival"
    hover: "&7Join &aSurvival&7!"
  skyblock:
    display: "&b&lSkyblock"
    command: "server skyblock"
    hover: "&7Join &bSkyblock&7!"
  creative:
    display: "&e&lCreative"
    command: "server creative"
    hover: "&7Join &eCreative&7!"
  pvp:
    display: "&c&lPvP Arena"
    command: "server pvp"
    hover: "&7Join &cPvP&7!"
  minigames:
    display: "&d&lMinigames"
    command: "server minigames"
    hover: "&7Join &dMinigames&7!"
  parkour:
    display: "&6&lParkour"
    command: "server parkour"
    hover: "&7Join &6Parkour&7!"
  factions:
    display: "&4&lFactions"
    command: "server factions"
    hover: "&7Join &4Factions&7!"
  prison:
    display: "&8&lPrison"
    command: "server prison"
    hover: "&7Join &8Prison&7!"
  bedwars:
    display: "&5&lBedWars"
    command: "server bedwars"
    hover: "&7Join &5BedWars&7!"
  skywars:
    display: "&9&lSkyWars"
    command: "server skywars"
    hover: "&7Join &9SkyWars&7!"
"""

# ============================================================
# Java source
# ============================================================
JAVA_SRC = r'''package com.muvixo.minestormjoinbook;

import io.netty.buffer.Unpooled;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import net.minecraft.server.v1_8_R3.ItemStack;
import net.minecraft.server.v1_8_R3.NBTBase;
import net.minecraft.server.v1_8_R3.NBTTagCompound;
import net.minecraft.server.v1_8_R3.NBTTagList;
import net.minecraft.server.v1_8_R3.NBTTagString;
import net.minecraft.server.v1_8_R3.Packet;
import net.minecraft.server.v1_8_R3.PacketDataSerializer;
import net.minecraft.server.v1_8_R3.PacketPlayOutCustomPayload;
import org.bukkit.ChatColor;
import org.bukkit.Material;
import org.bukkit.Sound;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.craftbukkit.v1_8_R3.entity.CraftPlayer;
import org.bukkit.craftbukkit.v1_8_R3.inventory.CraftItemStack;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.plugin.Plugin;
import org.bukkit.plugin.java.JavaPlugin;

public final class MineStormJoinBookPlugin extends JavaPlugin implements Listener {

    private static final int ENTRIES_PER_PAGE = 8;
    private final Set<UUID> seen = new HashSet<UUID>();
    private File dataFile;
    private FileConfiguration messages;
    private FileConfiguration gui;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        saveResourceIfMissing("messages.yml");
        saveResourceIfMissing("gui.yml");
        loadMessages();
        loadGui();
        loadSeen();
        getServer().getPluginManager().registerEvents(this, (Plugin) this);
        getLogger().info("MineStormJoinBook enabled. Created by Muvixo.");
    }

    @Override
    public void onDisable() {
        saveSeen();
        getLogger().info("MineStormJoinBook disabled.");
    }

    private void saveResourceIfMissing(String name) {
        File f = new File(getDataFolder(), name);
        if (!f.exists()) { f.getParentFile().mkdirs(); saveResource(name, false); }
    }

    private FileConfiguration loadYaml(File file) {
        if (!file.exists()) {
            file.getParentFile().mkdirs();
            try { file.createNewFile(); } catch (IOException ignored) {}
        }
        return YamlConfiguration.loadConfiguration(file);
    }

    private void loadMessages() {
        File f = new File(getDataFolder(), "messages.yml");
        if (!f.exists()) saveResourceIfMissing("messages.yml");
        this.messages = loadYaml(f);
        InputStream def = getResource("messages.yml");
        if (def != null) {
            this.messages.setDefaults(YamlConfiguration.loadConfiguration(
                    new InputStreamReader(def, StandardCharsets.UTF_8)));
        }
    }

    private void loadGui() {
        File f = new File(getDataFolder(), "gui.yml");
        if (!f.exists()) saveResourceIfMissing("gui.yml");
        this.gui = loadYaml(f);
        InputStream def = getResource("gui.yml");
        if (def != null) {
            this.gui.setDefaults(YamlConfiguration.loadConfiguration(
                    new InputStreamReader(def, StandardCharsets.UTF_8)));
        }
    }

    private void loadSeen() {
        this.dataFile = new File(getDataFolder(), "data.yml");
        this.seen.clear();
        if (!this.dataFile.exists()) return;
        for (String id : YamlConfiguration.loadConfiguration(this.dataFile).getStringList("seen")) {
            try { this.seen.add(UUID.fromString(id)); } catch (IllegalArgumentException ignored) {}
        }
    }

    private void saveSeen() {
        List<String> ids = new ArrayList<String>();
        for (UUID id : this.seen) ids.add(id.toString());
        YamlConfiguration yml = new YamlConfiguration();
        yml.set("seen", ids);
        try { yml.save(this.dataFile); }
        catch (IOException e) { getLogger().warning("Could not save data.yml: " + e.getMessage()); }
    }

    @EventHandler
    public void onJoin(final PlayerJoinEvent event) {
        final Player player = event.getPlayer();
        if (getConfig().getBoolean("respect-see-permission", true)
                && !hasPerm(player, "minestormjoinbook.see")) return;
        final boolean onlyOnce = getConfig().getBoolean("only-once", false);
        if (onlyOnce && this.seen.contains(player.getUniqueId())) return;
        long delay = Math.max(1L, getConfig().getLong("open-delay-ticks", 20L));
        getServer().getScheduler().runTaskLater((Plugin) this, new Runnable() {
            public void run() {
                if (!player.isOnline()) return;
                if (onlyOnce) {
                    if (!seen.add(player.getUniqueId())) return;
                    saveSeen();
                }
                openBook(player);
            }
        }, delay);
    }

    @Override
    public boolean onCommand(CommandSender sender, Command cmd, String label, String[] args) {
        if (args.length == 0) { sendHelp(sender); return true; }
        String sub = args[0].toLowerCase();
        if (sub.equals("help")) { sendHelp(sender); return true; }

        if (sub.equals("creator")) {
            if (!requirePerm(sender, "minestormjoinbook.creator")) return true;
            msg(sender, "creator", null, null);
            return true;
        }
        if (sub.equals("reload")) {
            if (!requirePerm(sender, "minestormjoinbook.reload")) return true;
            try {
                reloadConfig(); loadMessages(); loadGui();
                msg(sender, "reload-success", null, null);
            } catch (Exception e) {
                msg(sender, "reload-failed", "%error%", e.getMessage() == null ? "unknown" : e.getMessage());
            }
            return true;
        }
        if (sub.equals("open")) {
            if (args.length >= 2) {
                if (!requirePerm(sender, "minestormjoinbook.open.other")) return true;
                Player target = getServer().getPlayerExact(args[1]);
                if (target == null) { msg(sender, "player-not-found", "%player%", args[1]); return true; }
                try {
                    openBook(target);
                    msg(sender, "open-other", "%player%", target.getName());
                    msg(target, "open-target", null, null);
                } catch (Exception e) { msg(sender, "open-failed", "%player%", target.getName()); }
                return true;
            }
            if (!(sender instanceof Player)) { msg(sender, "player-only", null, null); return true; }
            if (!requirePerm(sender, "minestormjoinbook.open")) return true;
            try {
                openBook((Player) sender);
                msg(sender, "open-self", null, null);
            } catch (Exception e) { msg(sender, "open-failed", "%player%", sender.getName()); }
            return true;
        }
        if (sub.equals("reset")) {
            if (!requirePerm(sender, "minestormjoinbook.reset")) return true;
            if (args.length < 2) { msg(sender, "invalid-usage", "%usage%", msgRaw("usage-reset")); return true; }
            UUID id = getServer().getOfflinePlayer(args[1]).getUniqueId();
            if (this.seen.remove(id)) {
                saveSeen();
                msg(sender, "reset-success", "%player%", args[1]);
            } else {
                msg(sender, "reset-not-seen", "%player%", args[1]);
            }
            return true;
        }
        if (sub.equals("resetall")) {
            if (!requirePerm(sender, "minestormjoinbook.resetall")) return true;
            int count = this.seen.size();
            if (count == 0) { msg(sender, "resetall-empty", null, null); return true; }
            this.seen.clear();
            saveSeen();
            msg(sender, "resetall-success", "%count%", String.valueOf(count));
            return true;
        }
        if (sub.equals("list")) {
            if (!requirePerm(sender, "minestormjoinbook.list")) return true;
            if (this.seen.isEmpty()) { msg(sender, "list-empty", null, null); return true; }
            msg(sender, "list-header", "%count%", String.valueOf(this.seen.size()));
            for (UUID id : this.seen) {
                String name = getServer().getOfflinePlayer(id).getName();
                if (name == null) name = id.toString();
                msg(sender, "list-entry", "%player%", name);
            }
            return true;
        }
        if (sub.equals("info")) {
            if (!requirePerm(sender, "minestormjoinbook.info")) return true;
            msg(sender, "info-header", "%version%", getDescription().getVersion());
            msg(sender, "info-line", "%author%", getDescription().getAuthors().isEmpty()
                    ? "Muvixo" : getDescription().getAuthors().get(0));
            msg(sender, "info-seen", "%count%", String.valueOf(this.seen.size()));
            msg(sender, "info-once", "%once%", String.valueOf(getConfig().getBoolean("only-once", false)));
            msg(sender, "info-delay", "%delay%", String.valueOf(getConfig().getLong("open-delay-ticks", 20L)));
            return true;
        }
        msg(sender, "unknown-command", null, null);
        return true;
    }

    private boolean hasPerm(CommandSender sender, String node) {
        if (sender.isOp()) return true;
        return sender.hasPermission(node) || sender.hasPermission("minestormjoinbook.admin");
    }

    private boolean requirePerm(CommandSender sender, String node) {
        if (hasPerm(sender, node)) return true;
        msg(sender, "no-permission", null, null);
        return false;
    }

    public void openBook(Player player) {
        int slot = player.getInventory().getHeldItemSlot();
        org.bukkit.inventory.ItemStack original = player.getInventory().getItem(slot);
        player.getInventory().setItem(slot, buildBook());
        player.updateInventory();

        String soundName = getConfig().getString("open-sound", "ITEM_BOOK_PAGE_TURN");
        if (soundName != null && !soundName.isEmpty()) {
            try {
                Sound s = Sound.valueOf(soundName.toUpperCase());
                player.playSound(player.getLocation(), s, 1.0f, 1.0f);
            } catch (IllegalArgumentException ignored) {}
        }

        PacketPlayOutCustomPayload packet = new PacketPlayOutCustomPayload(
                "MC|BOpen", new PacketDataSerializer(Unpooled.buffer()));
        ((CraftPlayer) player).getHandle().playerConnection.sendPacket((Packet<?>) packet);

        player.getInventory().setItem(slot, original);
        player.updateInventory();
    }

    private org.bukkit.inventory.ItemStack buildBook() {
        NBTTagList pages = new NBTTagList();
        for (String page : buildPages()) pages.add((NBTBase) new NBTTagString(page));
        NBTTagCompound tag = new NBTTagCompound();
        tag.setString("title", color(gui.getString("book.title", "&6Gamemodes")));
        tag.setString("author", color(gui.getString("book.author", "Server")));
        tag.set("pages", (NBTBase) pages);
        ItemStack nms = CraftItemStack.asNMSCopy(new org.bukkit.inventory.ItemStack(Material.WRITTEN_BOOK));
        nms.setTag(tag);
        return CraftItemStack.asBukkitCopy(nms);
    }

    private List<String> buildPages() {
        String header = color(gui.getString("book.header", "&6&lWELCOME"));
        String subtitle = color(gui.getString("book.subtitle", "&7Choose a gamemode:"));
        String format = gui.getString("book.button-format", "&0&r%display%");
        List<String> buttons = new ArrayList<String>();
        ConfigurationSection modes = gui.getConfigurationSection("gamemodes");
        if (modes != null) {
            for (String key : modes.getKeys(false)) {
                ConfigurationSection m = modes.getConfigurationSection(key);
                if (m == null) continue;
                String command = m.getString("command", "").trim();
                if (command.isEmpty()) continue;
                if (!command.startsWith("/")) command = "/" + command;
                String display = m.getString("display", key);
                String text = color(format.replace("%display%", display));
                String hover = color(m.getString("hover", ""));
                buttons.add(button(text, command, hover));
            }
        }
        List<String> pages = new ArrayList<String>();
        int total = Math.max(1, (buttons.size() + ENTRIES_PER_PAGE - 1) / ENTRIES_PER_PAGE);
        for (int p = 0; p < total; p++) {
            StringBuilder sb = new StringBuilder("[\"\"");
            if (p == 0) {
                sb.append(",{\"text\":\"").append(esc(header + "\n")).append("\"}");
                sb.append(",{\"text\":\"").append(esc(subtitle + "\n\n")).append("\"}");
            }
            int from = p * ENTRIES_PER_PAGE;
            int to = Math.min(buttons.size(), from + ENTRIES_PER_PAGE);
            if (buttons.isEmpty())
                sb.append(",{\"text\":\"").append(esc("&cNo gamemodes configured.")).append("\"}");
            for (int i = from; i < to; i++) {
                sb.append(",").append(buttons.get(i));
                sb.append(",{\"text\":\"\\n\"}");
            }
            sb.append("]");
            pages.add(sb.toString());
        }
        return pages;
    }

    private static String button(String text, String command, String hover) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"text\":\"").append(esc(text)).append("\"");
        sb.append(",\"clickEvent\":{\"action\":\"run_command\",\"value\":\"")
                .append(esc(command)).append("\"}");
        if (hover != null && !hover.isEmpty())
            sb.append(",\"hoverEvent\":{\"action\":\"show_text\",\"value\":\"")
                    .append(esc(hover)).append("\"}");
        sb.append("}");
        return sb.toString();
    }

    private void sendHelp(CommandSender sender) {
        msg(sender, "help-header", null, null);
        help(sender, "usage-reload", "desc-reload");
        help(sender, "usage-open", "desc-open");
        help(sender, "usage-reset", "desc-reset");
        help(sender, "usage-resetall", "desc-resetall");
        help(sender, "usage-list", "desc-list");
        help(sender, "usage-info", "desc-info");
        help(sender, "usage-creator", "desc-creator");
        help(sender, "usage-help", "desc-help");
    }

    private void help(CommandSender sender, String usageKey, String descKey) {
        String u = messages.getString(usageKey, "");
        String d = messages.getString(descKey, "");
        String line = messages.getString("help-line", "&e%usage% &7- %description%");
        sender.sendMessage(color(line.replace("%usage%", u).replace("%description%", d)));
    }

    private void msg(CommandSender sender, String key, String ph, String val) {
        String raw = messages.getString(key, "&cMissing message: " + key);
        raw = raw.replace("%prefix%", messages.getString("prefix", ""));
        raw = raw.replace("%sender%", sender.getName());
        raw = raw.replace("%player%", sender.getName());
        if (ph != null && val != null) raw = raw.replace(ph, val);
        sender.sendMessage(color(raw));
    }

    private String msgRaw(String key) { return messages.getString(key, ""); }

    private static String color(String s) {
        if (s == null) return "";
        return ChatColor.translateAlternateColorCodes('&', s);
    }

    private static String esc(String s) {
        StringBuilder sb = new StringBuilder();
        for (char c : s.toCharArray()) {
            switch (c) {
                case '\\': sb.append("\\\\"); break;
                case '"':  sb.append("\\\""); break;
                case '\n': sb.append("\\n"); break;
                case '\r': break;
                default:   sb.append(c); break;
            }
        }
        return sb.toString();
    }
}
'''

# ============================================================
# GitHub Actions workflow — uses BuildTools to produce spigot 1.8.8
# ============================================================
WORKFLOW = """name: Build MineStormJoinBook

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  # -----------------------------------------------------------
  # Stage 1: build Spigot 1.8.8 once with JDK 8 + BuildTools
  # -----------------------------------------------------------
  spigot:
    name: Build Spigot 1.8.8 with BuildTools
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up JDK 8
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '8'
          cache: maven

      - name: Cache Spigot 1.8.8 build
        id: spigot-cache
        uses: actions/cache@v4
        with:
          path: |
            ~/.m2/repository/org/spigotmc
            ~/.m2/repository/net/md-5
            ~/.m2/repository/org/bukkit
            ~/BuildTools
          key: spigot-1.8.8-v1

      - name: Install git config (BuildTools needs it)
        run: |
          git config --global user.email "ci@github.com"
          git config --global user.name "CI"
          git config --global --add safe.directory "$GITHUB_WORKSPACE"

      - name: Download BuildTools
        if: steps.spigot-cache.outputs.cache-hit != 'true'
        run: |
          mkdir -p ~/BuildTools
          cd ~/BuildTools
          curl -fL -o BuildTools.jar \\
            https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar

      - name: Build Spigot 1.8.8
        if: steps.spigot-cache.outputs.cache-hit != 'true'
        run: |
          cd ~/BuildTools
          java -jar BuildTools.jar --rev 1.8.8 --compile-if-changed=false 2>&1 | tail -n 60

      - name: Verify Spigot installed
        run: |
          ls -la ~/.m2/repository/org/spigotmc/spigot/1.8.8-R0.1-SNAPSHOT/ || true
          ls -la ~/.m2/repository/org/spigotmc/spigot-api/1.8.8-R0.1-SNAPSHOT/ || true

  # -----------------------------------------------------------
  # Stage 2: build plugin on JDK 8, 17, 21, 25
  # -----------------------------------------------------------
  build:
    name: Build plugin on JDK ${{ matrix.java }}
    needs: spigot
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        java: [ '8', '17', '21', '25' ]
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up JDK ${{ matrix.java }}
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: ${{ matrix.java }}
          cache: maven

      - name: Restore Spigot 1.8.8 from cache
        uses: actions/cache@v4
        with:
          path: |
            ~/.m2/repository/org/spigotmc
            ~/.m2/repository/net/md-5
            ~/.m2/repository/org/bukkit
          key: spigot-1.8.8-v1

      - name: Show Java version
        run: java -version

      - name: Build with Maven
        run: mvn -B -o -DskipTests clean package || mvn -B -DskipTests clean package

      - name: Upload artifact (JDK ${{ matrix.java }})
        uses: actions/upload-artifact@v4
        with:
          name: MineStormJoinBook-JDK${{ matrix.java }}
          path: target/*.jar
          if-no-files-found: error
"""

# ============================================================
# README
# ============================================================
README = """# MineStormJoinBook

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
"""

GITIGNORE = "target/\n*.iml\n.idea/\n.settings/\n.classpath\n.project\nBuildTools/\n"

# ============================================================
# Writer
# ============================================================
def write(path, content):
    full = path if ROOT == "." else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("  +", full)

def main():
    print("Patching project in:", os.path.abspath(ROOT))

    # Remove legacy package dir from earlier attempts
    legacy = os.path.join("src", "main", "java", "com", "example")
    if os.path.isdir(legacy):
        shutil.rmtree(legacy)
        print("  - removed legacy package:", legacy)

    write("pom.xml", POM_XML)
    write(os.path.join(RES, "plugin.yml"), PLUGIN_YML)
    write(os.path.join(RES, "config.yml"), CONFIG_YML)
    write(os.path.join(RES, "messages.yml"), MESSAGES_YML)
    write(os.path.join(RES, "gui.yml"), GUI_YML)
    write(os.path.join(SRC, "MineStormJoinBookPlugin.java"), JAVA_SRC)
    write(os.path.join(WF, "build.yml"), WORKFLOW)
    write("README.md", README)
    write(".gitignore", GITIGNORE)

    print()
    print("Done.")
    print("  git add .")
    print('  git commit -m "ci: build spigot 1.8.8 with BuildTools, cache it, then build plugin"')
    print("  git push")

if __name__ == "__main__":
    main()

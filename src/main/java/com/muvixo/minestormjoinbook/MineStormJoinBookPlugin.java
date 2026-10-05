package com.muvixo.minestormjoinbook;

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
    private File messagesFile;
    private File guiFile;
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
        if (!f.exists()) {
            f.getParentFile().mkdirs();
            saveResource(name, false);
        }
    }

    private FileConfiguration loadYaml(File file) {
        if (!file.exists()) {
            file.getParentFile().mkdirs();
            try { file.createNewFile(); } catch (IOException ignored) {}
        }
        return YamlConfiguration.loadConfiguration(file);
    }

    private void loadMessages() {
        this.messagesFile = new File(getDataFolder(), "messages.yml");
        if (!messagesFile.exists()) saveResourceIfMissing("messages.yml");
        this.messages = loadYaml(messagesFile);
        InputStream def = getResource("messages.yml");
        if (def != null) {
            this.messages.setDefaults(YamlConfiguration.loadConfiguration(
                    new InputStreamReader(def, StandardCharsets.UTF_8)));
        }
    }

    private void loadGui() {
        this.guiFile = new File(getDataFolder(), "gui.yml");
        if (!guiFile.exists()) saveResourceIfMissing("gui.yml");
        this.gui = loadYaml(guiFile);
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
                && !hasPerm(player, "minestormjoinbook.see")) {
            return;
        }
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
                reloadConfig();
                loadMessages();
                loadGui();
                msg(sender, "reload-success", null, null);
            } catch (Exception e) {
                msg(sender, "reload-failed", "%error%",
                        e.getMessage() == null ? "unknown" : e.getMessage());
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
                } catch (Exception e) {
                    msg(sender, "open-failed", "%player%", target.getName());
                }
                return true;
            }
            if (!(sender instanceof Player)) { msg(sender, "player-only", null, null); return true; }
            if (!requirePerm(sender, "minestormjoinbook.open")) return true;
            try {
                openBook((Player) sender);
                msg(sender, "open-self", null, null);
            } catch (Exception e) {
                msg(sender, "open-failed", "%player%", sender.getName());
            }
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
        int perPage = ENTRIES_PER_PAGE;
        int total = Math.max(1, (buttons.size() + perPage - 1) / perPage);
        for (int p = 0; p < total; p++) {
            StringBuilder sb = new StringBuilder("[\"\"");
            if (p == 0) {
                sb.append(",{\"text\":\"").append(esc(header + "\n")).append("\"}");
                sb.append(",{\"text\":\"").append(esc(subtitle + "\n\n")).append("\"}");
            }
            int from = p * perPage;
            int to = Math.min(buttons.size(), from + perPage);
            if (buttons.isEmpty()) {
                sb.append(",{\"text\":\"").append(esc("&cNo gamemodes configured.")).append("\"}");
            }
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
        if (hover != null && !hover.isEmpty()) {
            sb.append(",\"hoverEvent\":{\"action\":\"show_text\",\"value\":\"")
                    .append(esc(hover)).append("\"}");
        }
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

    private String msgRaw(String key) {
        return messages.getString(key, "");
    }

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

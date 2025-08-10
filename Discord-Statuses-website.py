import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

CONFIG_DIR = "data/DcStatuses"
CONFIG_FILE = os.path.join(CONFIG_DIR, "status_config.json")
STATUS_DATA_FILE = os.path.join(CONFIG_DIR, "status_data.json")

STATUS_EMOJI = {
    "Operational": "✅", "Online": "🟩", "Partial Outage": "🟨",
    "Offline": "🟥", "Maintenance": "🛠️", "Loading": "🔄", "Not Found": "❔"
}
STATUS_COLOR = {
    "Operational": discord.Color.green(), "Partial": discord.Color.gold(),
    "Outage": discord.Color.red(), "Maintenance": discord.Color.blue()
}

def create_response_embed(title: str, description: str, color: discord.Color = discord.Color.blue()) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)

class TitleModal(discord.ui.Modal, title="Change Embed Title"):
    def __init__(self, cog: "StatusCog"):
        super().__init__()
        self.cog = cog
        self.new_title = discord.ui.TextInput(label="New Embed Title", placeholder="e.g., Zygnal Status", default=self.cog.config.get("embed_title", "Service Status"))
        self.add_item(self.new_title)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        new_title = self.new_title.value.strip()
        self.cog.config["embed_title"] = new_title
        self.cog.save_config()
        await interaction.followup.send(embed=create_response_embed("✅ Title Updated", f"The embed title has been set to **{new_title}**."), ephemeral=True)
        await self.cog.trigger_update()

class ApiSettingsModal(discord.ui.Modal, title="API/Webhook Settings"):
    def __init__(self, cog: "StatusCog"):
        super().__init__()
        self.cog = cog
        self.api_url = discord.ui.TextInput(label="API POST URL", placeholder="e.g., https://zygnalbot.com/api/receive_status.php", default=self.cog.config.get("api_post_url"), style=discord.TextStyle.long, required=False)
        self.api_token = discord.ui.TextInput(label="Secret Token (optional)", placeholder="A secure password to authorize the request", default=self.cog.config.get("api_secret_token"), required=False)
        self.add_item(self.api_url)
        self.add_item(self.api_token)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.cog.config["api_post_url"] = self.api_url.value.strip() or None
        self.cog.config["api_secret_token"] = self.api_token.value.strip() or None
        self.cog.save_config()
        await interaction.followup.send(embed=create_response_embed("✅ API Settings Updated", "The API endpoint and token have been saved."), ephemeral=True)

class BotModal(discord.ui.Modal):
    def __init__(self, cog: "StatusCog", action: str):
        super().__init__(title=f"{action.title()} Bot")
        self.cog = cog
        self.action = action
        self.bot_id = discord.ui.TextInput(label="Bot's User ID", placeholder="e.g., 123456789012345678", min_length=17, max_length=20)
        self.add_item(self.bot_id)
        if self.action == "add":
            self.bot_label = discord.ui.TextInput(label="Display Name", placeholder="e.g., Cortex-Bot", style=discord.TextStyle.short)
            self.add_item(self.bot_label)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            bot_id = int(self.bot_id.value.strip())
            if self.action == "add":
                label = self.bot_label.value.strip()
                if not any(b['id'] == bot_id for b in self.cog.config["bots"]):
                    self.cog.config["bots"].append({"id": bot_id, "label": label})
                    self.cog.save_config()
                    embed = create_response_embed("✅ Bot Added", f"Bot **{label}** (`{bot_id}`) will now be monitored.")
                else:
                    embed = create_response_embed("⚠️ Already Exists", f"Bot with ID `{bot_id}` is already being monitored.", color=discord.Color.orange())
            elif self.action == "remove":
                bot_to_remove = next((b for b in self.cog.config["bots"] if b['id'] == bot_id), None)
                if bot_to_remove:
                    self.cog.config["bots"].remove(bot_to_remove)
                    self.cog.save_config()
                    embed = create_response_embed("🗑️ Bot Removed", f"Bot **{bot_to_remove['label']}** (`{bot_id}`) has been removed.")
                else:
                    embed = create_response_embed("❌ Not Found", f"Bot with ID `{bot_id}` is not on the monitoring list.", color=discord.Color.red())
        except ValueError:
            embed = create_response_embed("❌ Invalid ID", "A Bot ID must be a number.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await self.cog.trigger_update()

class WebsiteModal(discord.ui.Modal):
    def __init__(self, cog: "StatusCog", action: str):
        super().__init__(title=f"{action.title()} Website")
        self.cog = cog
        self.action = action
        self.url = discord.ui.TextInput(label="Website URL", placeholder="e.g., https://google.com")
        self.add_item(self.url)
        if self.action == "add":
            self.label = discord.ui.TextInput(label="Display Name", placeholder="e.g., Google Search")
            self.add_item(self.label)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        url = self.url.value.strip()
        if not url.startswith(("http://", "https://")): url = "https://" + url
        if self.action == "add":
            label = self.label.value.strip() or url
            if not any(w['url'] == url for w in self.cog.config["websites"]):
                self.cog.config["websites"].append({"url": url, "label": label})
                self.cog.save_config()
                embed = create_response_embed("✅ Website Added", f"**{label}** (`{url}`) will now be monitored.")
            else:
                embed = create_response_embed("⚠️ Already Exists", f"Website `{url}` is already monitored.", color=discord.Color.orange())
        elif self.action == "remove":
            website_to_remove = next((w for w in self.cog.config["websites"] if w['url'] == url), None)
            if website_to_remove:
                self.cog.config["websites"].remove(website_to_remove)
                self.cog.save_config()
                embed = create_response_embed("🗑️ Website Removed", f"Website `{url}` has been removed.")
            else:
                embed = create_response_embed("❌ Not Found", f"Website `{url}` is not on the monitoring list.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await self.cog.trigger_update()

class ServiceModal(discord.ui.Modal):
    def __init__(self, cog: "StatusCog", action: str):
        super().__init__(title=f"{action.title()} Service")
        self.cog = cog
        self.action = action
        self.service_name = discord.ui.TextInput(label="Service Name", placeholder="e.g., Database Server")
        self.add_item(self.service_name)
        if self.action == "add":
            self.service_status = discord.ui.TextInput(label="Initial Status", placeholder="e.g., Operational, Under Maintenance")
            self.add_item(self.service_status)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        name = self.service_name.value.strip()
        if self.action == "add":
            status = self.service_status.value.strip() or "Operational"
            self.cog.config["services"][name] = status
            self.cog.save_config()
            embed = create_response_embed("✅ Service Added", f"Service **{name}** added with status: `{status}`.")
        elif self.action == "remove":
            if name in self.cog.config["services"]:
                del self.cog.config["services"][name]
                self.cog.save_config()
                embed = create_response_embed("🗑️ Service Removed", f"Service **{name}** has been removed.")
            else:
                embed = create_response_embed("❌ Not Found", f"Service **{name}** is not on the list.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await self.cog.trigger_update()

class WebsiteButtonsView(discord.ui.View):
    def __init__(self, websites: List[Dict[str, str]]):
        super().__init__(timeout=None)
        for website in websites[:25]:
            self.add_item(discord.ui.Button(label=website.get("label", website["url"]), style=discord.ButtonStyle.link, url=website["url"]))

class DiscordServiceSelect(discord.ui.Select):
    def __init__(self, cog: "StatusCog", all_services: List[Dict[str, Any]]):
        self.cog = cog
        monitored = self.cog.config.get("monitored_discord_services", [])
        options = [
            discord.SelectOption(label=service['name'], value=service['id'], default=service['id'] in monitored)
            for service in all_services
        ]
        super().__init__(placeholder="Select Discord services to monitor...", min_values=0, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        self.cog.config["monitored_discord_services"] = self.values
        self.cog.save_config()
        all_labels = {opt.value: opt.label for opt in self.options}
        selected_labels = [all_labels[v] for v in self.values]
        await interaction.response.send_message(embed=create_response_embed("✅ Services Updated", f"Now monitoring: **{', '.join(selected_labels) or 'None'}**."), ephemeral=True)
        await self.cog.trigger_update()

class DiscordServiceView(discord.ui.View):
    def __init__(self, cog: "StatusCog", all_services: List[Dict[str, Any]]):
        super().__init__(timeout=180)
        self.add_item(DiscordServiceSelect(cog, all_services))

class AdminPanelView(discord.ui.View):
    def __init__(self, cog: "StatusCog"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Manage Bots", style=discord.ButtonStyle.secondary, emoji="🤖", custom_id="admin_panel:manage_bots")
    async def manage_bots(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_modal(BotModal(self.cog, "add"))

    @discord.ui.button(label="Manage Websites", style=discord.ButtonStyle.secondary, emoji="🌐", custom_id="admin_panel:manage_websites")
    async def manage_websites(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_modal(WebsiteModal(self.cog, "add"))

    @discord.ui.button(label="Manage Services", style=discord.ButtonStyle.secondary, emoji="⚙️", custom_id="admin_panel:manage_services")
    async def manage_services(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_modal(ServiceModal(self.cog, "add"))

    @discord.ui.button(label="Discord Services", style=discord.ButtonStyle.secondary, emoji="📢", row=1, custom_id="admin_panel:discord_services")
    async def manage_discord_services(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            async with self.cog.session.get("https://discordstatus.com/api/v2/components.json") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    all_services = [{"id": s['id'], "name": s['name']} for s in data.get('components', []) if not s.get('group_id')]
                    view = DiscordServiceView(self.cog, all_services)
                    await interaction.followup.send(embed=create_response_embed("📢 Manage Discord Services", "Select which official Discord services you want to display on the status embed."), view=view, ephemeral=True)
                else:
                    await interaction.followup.send(embed=create_response_embed("❌ Error", f"Could not fetch Discord service list (Status: {resp.status})."), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=create_response_embed("❌ Error", f"An unexpected error occurred: {e}"), ephemeral=True)

    @discord.ui.button(label="Remove Item", style=discord.ButtonStyle.danger, emoji="🗑️", row=1, custom_id="admin_panel:remove_item")
    async def remove_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=180)
        b_b = discord.ui.Button(label="Remove Bot", style=discord.ButtonStyle.danger, emoji="🤖")
        w_b = discord.ui.Button(label="Remove Website", style=discord.ButtonStyle.danger, emoji="🌐")
        s_b = discord.ui.Button(label="Remove Service", style=discord.ButtonStyle.danger, emoji="⚙️")
        async def b_cb(i: discord.Interaction): await i.response.send_modal(BotModal(self.cog, "remove"))
        async def w_cb(i: discord.Interaction): await i.response.send_modal(WebsiteModal(self.cog, "remove"))
        async def s_cb(i: discord.Interaction): await i.response.send_modal(ServiceModal(self.cog, "remove"))
        b_b.callback, w_b.callback, s_b.callback = b_cb, w_cb, s_cb
        view.add_item(b_b); view.add_item(w_b); view.add_item(s_b)
        await interaction.response.send_message(embed=create_response_embed("🗑️ Remove an Item", "Select the type of item you want to remove."), view=view, ephemeral=True)

    @discord.ui.button(label="Post/Move Status", style=discord.ButtonStyle.primary, emoji="📌", row=2, custom_id="admin_panel:post_status")
    async def post_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cog.waiting_for_channel[interaction.user.id] = interaction.channel.id
        await interaction.response.send_message(embed=create_response_embed("📌 Mention a Channel", "Please mention the channel where you want the status embed to be posted.\n\nSend your next message in this channel with the channel mention."), ephemeral=True)

    @discord.ui.button(label="API Settings", style=discord.ButtonStyle.secondary, emoji="🔗", row=2, custom_id="admin_panel:api_settings")
    async def api_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApiSettingsModal(self.cog))

    @discord.ui.button(label="Set Interval", style=discord.ButtonStyle.secondary, emoji="⏱️", row=3, custom_id="admin_panel:set_interval")
    async def set_interval(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=180)
        opts = [discord.SelectOption(label=f"{m} Minute(s)", value=str(m)) for m in [1, 2, 5, 10, 30, 60]]
        sel = discord.ui.Select(placeholder="Choose a refresh interval...", options=opts)
        async def cb(i: discord.Interaction):
            await i.response.defer(ephemeral=True)
            minutes = int(sel.values[0])
            self.cog.config["refresh_interval"] = minutes
            self.cog.save_config()
            self.cog.status_loop.change_interval(minutes=minutes)
            await i.followup.send(embed=create_response_embed("⏱️ Interval Updated", f"Status will now refresh every **{minutes} minute(s)**."), ephemeral=True)
        sel.callback = cb
        view.add_item(sel)
        await interaction.response.send_message(embed=create_response_embed("⏱️ Set Refresh Interval", "Choose how often the status embed should update."), view=view, ephemeral=True)

    @discord.ui.button(label="Change Title", style=discord.ButtonStyle.secondary, emoji="✏️", row=4, custom_id="admin_panel:change_title")
    async def change_title(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_modal(TitleModal(self.cog))

    @discord.ui.button(label="Refresh & POST", style=discord.ButtonStyle.success, emoji="🔄", row=4, custom_id="admin_panel:refresh")
    async def refresh_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.cog.trigger_update()
        await interaction.followup.send(embed=create_response_embed("🔄 Status Refreshed", "The status has been manually refreshed and posted to the API endpoint."), ephemeral=True)

class StatusCog(commands.Cog, name="Status Monitor"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.config = self.load_config()
        self.waiting_for_channel = {}
        self.status_data = {}
        self.bot.loop.create_task(self._init_async())

    async def _init_async(self):
        self.session = aiohttp.ClientSession()
        await self.register_persistent_views()
        self.status_loop.change_interval(minutes=self.config.get("refresh_interval", 5))
        if not self.status_loop.is_running():
            self.status_loop.start()

    async def register_persistent_views(self):
        await self.bot.wait_until_ready()
        if not hasattr(self.bot, 'persistent_views_added_status'):
            self.bot.add_view(AdminPanelView(self))
            self.bot.persistent_views_added_status = True
            print("Status Monitor Admin Panel View successfully registered.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if message.author.id in self.waiting_for_channel:
            if message.channel.id != self.waiting_for_channel[message.author.id]: return
            del self.waiting_for_channel[message.author.id]
            try:
                if not message.channel_mentions:
                    await message.reply(embed=create_response_embed("❌ No Channel Found", "Please mention a channel.", color=discord.Color.red()))
                    return
                selected_channel = message.channel_mentions[0]
                if not isinstance(selected_channel, (discord.TextChannel, discord.Thread)):
                    await message.reply(embed=create_response_embed("❌ Invalid Channel Type", "Please mention a text channel or thread.", color=discord.Color.red()))
                    return
                permissions = selected_channel.permissions_for(message.guild.me)
                if not permissions.send_messages or not permissions.embed_links:
                    await message.reply(embed=create_response_embed("❌ Permissions Missing", f"I need **Send Messages** and **Embed Links** permissions in {selected_channel.mention}.", color=discord.Color.red()))
                    return
                await self.delete_old_status_message()
                init_embed = discord.Embed(title="Service Status", description=f"{STATUS_EMOJI['Loading']} Initializing...", color=STATUS_COLOR["Maintenance"])
                msg = await selected_channel.send(embed=init_embed)
                self.config.update({"channel_id": msg.channel.id, "message_id": msg.id})
                self.save_config()
                await message.reply(embed=create_response_embed("✅ Success", f"Status embed posted to {selected_channel.mention}."))
                await self.trigger_update()
            except discord.Forbidden:
                await message.reply(embed=create_response_embed("❌ Permissions Error", "I was blocked. Please check my role/channel permissions.", color=discord.Color.red()))
            except Exception as e:
                print(f"An unexpected error occurred in channel mention handler: {e}")
                await message.reply(embed=create_response_embed("❌ Unexpected Error", f"An error occurred: {str(e)}", color=discord.Color.red()))

    def cog_unload(self):
        self.status_loop.cancel()
        if self.session: asyncio.create_task(self.session.close())

    def load_config(self) -> Dict[str, Any]:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        default_config = {
            "channel_id": None, "message_id": None, "bots": [], "websites": [], "services": {},
            "refresh_interval": 5, "embed_title": "Service Status",
            "monitored_discord_services": [],
            "api_post_url": None, "api_secret_token": None
        }
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: config = json.load(f)
            for key, value in default_config.items():
                config.setdefault(key, value)
        except (FileNotFoundError, json.JSONDecodeError):
            config = default_config
        self.save_config(config)
        return config

    def save_config(self, config_data: Optional[Dict[str, Any]] = None):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data or self.config, f, indent=4)

    def save_status_data(self):
        with open(STATUS_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.status_data, f, indent=4)

    async def delete_old_status_message(self):
        if self.config.get("channel_id") and self.config.get("message_id"):
            try:
                channel = await self.bot.fetch_channel(self.config["channel_id"])
                message = await channel.fetch_message(self.config["message_id"])
                await message.delete()
            except (discord.NotFound, discord.Forbidden): pass
            finally: self.config.update({"channel_id": None, "message_id": None}); self.save_config()

    async def fetch_website_status(self, url: str) -> (str, bool):
        try:
            async with self.session.get(url, timeout=10) as response:
                return ("Online", True) if 200 <= response.status < 300 else (f"Status {response.status}", False)
        except (asyncio.TimeoutError, aiohttp.ClientError): return "Offline", False

    async def trigger_update(self):
        if not self.status_loop.is_running():
            self.status_loop.start()
        await self.status_loop.coro(self)

    async def fetch_all_statuses(self) -> Dict[str, Any]:
        guild = self.bot.get_guild(self.config.get("guild_id"))
        if not guild and self.config.get("channel_id"):
             try:
                channel = await self.bot.fetch_channel(self.config["channel_id"])
                guild = channel.guild
                self.config["guild_id"] = guild.id
                self.save_config()
             except (discord.NotFound, discord.Forbidden):
                 print("Could not find guild to fetch member statuses.")
                 return {}

        status_data = {
            "bots": [], "websites": [], "discord_services": [], "custom_services": [],
            "last_updated_utc": datetime.now(timezone.utc).isoformat()
        }

        if guild:
            for bot_info in self.config.get("bots", []):
                bot_data = {"label": bot_info['label'], "id": bot_info['id']}
                try:
                    bot = guild.get_member(bot_info['id']) or await guild.fetch_member(bot_info['id'])
                    status_map = { discord.Status.online: "Online", discord.Status.idle: "Idle", discord.Status.dnd: "Do Not Disturb", discord.Status.offline: "Offline", discord.Status.invisible: "Invisible"}
                    bot_data["status"] = status_map.get(bot.status, "Offline")
                    bot_data["raw_status"] = str(bot.status)
                except discord.NotFound: bot_data["status"] = "Not Found in Server"
                except discord.Forbidden: bot_data["status"] = "No Permissions"
                except Exception: bot_data["status"] = "Error Fetching"
                status_data["bots"].append(bot_data)

        for site in self.config.get("websites", []):
            stat, ok = await self.fetch_website_status(site['url'])
            status_data["websites"].append({"label": site['label'], "url": site['url'], "status": stat, "online": ok})

        monitored_ids = self.config.get("monitored_discord_services", [])
        if monitored_ids:
            try:
                async with self.session.get("https://discordstatus.com/api/v2/components.json", timeout=10) as resp:
                    if resp.status == 200:
                        all_components = {c['id']: c for c in (await resp.json()).get('components', [])}
                        for service_id in monitored_ids:
                            if comp := all_components.get(service_id):
                                status_map = {"operational": "Operational", "degraded_performance": "Partial Outage", "partial_outage": "Partial Outage", "major_outage": "Offline", "under_maintenance": "Maintenance"}
                                status_text = status_map.get(comp['status'], comp['status'].replace("_", " ").title())
                                status_data["discord_services"].append({"name": comp['name'], "status": status_text, "raw_status": comp['status']})
                            else:
                                service_name_guess = service_id.replace("_", " ").title()
                                status_data["discord_services"].append({"name": service_name_guess, "status": "Not Found in API", "raw_status": "not_found"})
                    else:
                         status_data["discord_services"].append({"name": "Discord API", "status": f"API Error ({resp.status})", "raw_status": "api_error"})
            except Exception:
                status_data["discord_services"].append({"name": "Discord API", "status": "Failed to Fetch", "raw_status": "fetch_failed"})

        for name, status in self.config.get("services", {}).items():
            status_data["custom_services"].append({"name": name, "status": status})

        return status_data

    async def update_status_embed(self):
        if not self.config.get("channel_id") or not self.config.get("message_id"): return
        try:
            channel = self.bot.get_channel(self.config["channel_id"]) or await self.bot.fetch_channel(self.config["channel_id"])
            message = await channel.fetch_message(self.config["message_id"])
        except (discord.NotFound, discord.Forbidden):
            self.config.update({"channel_id": None, "message_id": None}); self.save_config()
            return

        await message.edit(embed=discord.Embed(title=f"{STATUS_EMOJI['Loading']} Checking Status...", color=STATUS_COLOR["Maintenance"]), view=None)

        self.status_data = await self.fetch_all_statuses()
        self.save_status_data()
        await self.post_data_to_api()

        embed = discord.Embed(title=self.config.get("embed_title", "Service Status"), color=STATUS_COLOR["Operational"])
        description = []

        if self.status_data.get("bots"):
            lines = []
            for bot in self.status_data["bots"]:
                emoji = STATUS_EMOJI["Online"] if bot["status"] == "Online" else (STATUS_EMOJI["Partial Outage"] if bot["status"] in ["Idle", "Do Not Disturb"] else STATUS_EMOJI["Offline"])
                lines.append(f"{emoji} **{bot['label']}**\n> Status: **{bot['status']}**")
            description.append("### **__Bots__**\n" + "\n\n".join(lines))

        if self.status_data.get("websites"):
            lines = []
            for site in self.status_data["websites"]:
                emoji = STATUS_EMOJI['Online'] if site['online'] else STATUS_EMOJI['Offline']
                lines.append(f"{emoji} [{site['label']}]({site['url']})\n> Status: **{site['status']}**")
            description.append("### **__Websites__**\n" + "\n\n".join(lines))

        other_services_section = []
        if self.status_data.get("discord_services") or self.status_data.get("custom_services"):
             other_services_section.append("### **__Other Services__**")

        if self.status_data.get("discord_services"):
            lines = ["**[Discord]**"]
            for service in self.status_data["discord_services"]:
                emoji = STATUS_EMOJI.get(service['status'], "❔")
                lines.append(f"> {emoji} **{service['name']}**: {service['status']}")
            other_services_section.append("\n".join(lines))

        if self.status_data.get("custom_services"):
            lines = []
            for service in self.status_data["custom_services"]:
                emoji = STATUS_EMOJI.get(service.get('status', 'Not Found'), '❔')
                lines.append(f"**[{service['name']}]**\n> {emoji} Status: **{service['status']}**")
            other_services_section.append("\n\n".join(lines))

        if other_services_section:
            description.append("\n\n".join(other_services_section))

        embed.description = "\n".join(description) or "No services are currently being monitored."
        embed.set_footer(text=f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}", icon_url=channel.guild.icon.url if channel.guild.icon else None)

        view = WebsiteButtonsView(self.config.get("websites", []))
        await message.edit(embed=embed, view=view)

    async def post_data_to_api(self):
        url = self.config.get("api_post_url")
        token = self.config.get("api_secret_token")
        if not url or not self.status_data:
            return

        final_url = url
        if token:
            if '?' in final_url:
                final_url += f"&token={token}"
            else:
                final_url += f"?token={token}"

        headers = {"Content-Type": "application/json"}

        try:
            async with self.session.post(final_url, json=self.status_data, headers=headers, timeout=15) as response:
                if response.status >= 400:
                    print(f"Error posting to API: Status {response.status} - {await response.text()}")
                else:
                    print(f"Successfully posted status data to API (Status: {response.status})")
        except Exception as e:
            print(f"Failed to post data to API endpoint '{url}'. Error: {e}")

    @tasks.loop(minutes=5)
    async def status_loop(self):
        await self.update_status_embed()

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()
        try:
            with open(STATUS_DATA_FILE, "r", encoding="utf-8") as f:
                self.status_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.status_data = {}

    @commands.hybrid_command(name="status-setup", description="Opens the admin panel for the status monitor.")
    @commands.has_permissions(administrator=True)
    async def status_setup(self, ctx: commands.Context):
        if 'guild_id' not in self.config or not self.config['guild_id']:
            self.config['guild_id'] = ctx.guild.id
            self.save_config()

        embed = discord.Embed(
            title="🛠️ Status Monitor Admin Panel",
            description=(
                "Welcome! Use the buttons below to manage the status monitor.\n\n"
                "• **Manage Items**: Add/remove bots, websites, and custom services.\n"
                "• **Discord Services**: Choose which official Discord services to monitor.\n"
                "• **API Settings**: Set the URL and token to post status data to your website. [**New!**]\n"
                "• **Post/Move Status**: Set the channel for the public status embed.\n"
                "• **Settings**: Adjust the refresh interval and embed title.\n"
                "• **Refresh & POST**: Manually trigger an immediate update and send it to your API."
            ),
            color=discord.Color.dark_grey()
        )
        await ctx.send(embed=embed, view=AdminPanelView(self), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCog(bot))

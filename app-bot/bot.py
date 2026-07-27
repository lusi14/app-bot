import discord
from discord import app_commands
from discord.ext import commands
import config

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DEPARTMENTS = {
    "lapd": "Los Angeles Police Department",
    "lasd": "Los Angeles County Sheriff's Department",
    "chp": "California Highway Patrol",
    "lafd": "Los Angeles Fire Department",
    "usms": "United States Marshals Service",
    "dot": "Department of Transportation",
}

def has_permission(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    if config.REQUIRED_ROLE_ID is None:
        return True
    return any(r.id == config.REQUIRED_ROLE_ID for r in interaction.user.roles)

async def process_application(
    interaction: discord.Interaction,
    department_key: str,
    action: str,          # "accept" or "deny"
    user: discord.Member,
    reason: str,
    note: str | None = None,
):
    if not has_permission(interaction):
        await interaction.response.send_message(
            "You do not have permission to use this command.", ephemeral=True
        )
        return

    dept_name = DEPARTMENTS[department_key]
    color = discord.Color.green() if action == "accept" else discord.Color.red()
    title = f"{dept_name} Application {'Accepted' if action == 'accept' else 'Denied'}"

    embed = discord.Embed(title=title, color=color, timestamp=discord.utils.utcnow())
    embed.add_field(name="Applicant", value=user.mention, inline=True)
    embed.add_field(name="Handled by", value=interaction.user.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    if note:
        embed.add_field(name="Note", value=note, inline=False)
    embed.set_footer(text=f"Department: {dept_name}")

    log_channel = bot.get_channel(config.LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(content=user.mention, embed=embed)
    else:
        await interaction.followup.send("Log channel not found.", ephemeral=True)
        return

    await interaction.response.send_message(
        f"{dept_name} application for {user.mention} has been **{action}ed**.",
        ephemeral=True,
    )

def make_command(dept_key: str, action: str):
    @app_commands.command(
        name=f"{dept_key}-{action}",
        description=f"{action.capitalize()} an application for {DEPARTMENTS[dept_key]}",
    )
    @app_commands.describe(
        user="The user whose application is being processed",
        reason="Reason for the decision",
        note="Optional extra note",
    )
    async def command(
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
        note: str | None = None,
    ):
        await process_application(interaction, dept_key, action, user, reason, note)

    return command

# Register all 12 slash commands
for key in DEPARTMENTS:
    bot.tree.add_command(make_command(key, "deny"))
    bot.tree.add_command(make_command(key, "accept"))

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=config.GUILD_ID))
        print(f"Synced {len(synced)} commands to guild {config.GUILD_ID}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

bot.run(config.TOKEN)
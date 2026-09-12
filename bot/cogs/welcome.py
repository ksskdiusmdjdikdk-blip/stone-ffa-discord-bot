"""Welcome messages, auto-role, and verification panel."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import config
from bot.database import db
from bot.logger import logger
from bot.utils.checks import staff_check
from bot.utils.embeds import base_embed, error_embed, info_embed, success_embed


class VerifyView(discord.ui.View):
    """Basic verification button. Designed for future Minecraft account linking."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="stoneffa:verify",
    )
    async def verify(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=error_embed("Error", "Guild only."), ephemeral=True
            )
            return

        await db.set_verification_placeholder(interaction.guild.id, interaction.user.id)

        role_assigned = False
        if config.welcome_role_id:
            role = interaction.guild.get_role(config.welcome_role_id)
            member = interaction.user
            if isinstance(member, discord.Member) and role and role not in member.roles:
                try:
                    await member.add_roles(role, reason="Verification button")
                    role_assigned = True
                except discord.Forbidden:
                    logger.warning("Missing permission to assign welcome role")
                except discord.HTTPException as exc:
                    logger.warning("Failed to assign role: %s", exc)

        desc = (
            "You clicked the verification button.\n\n"
            "**Note:** Minecraft account linking is not connected yet. "
            "This step only records your Discord verification intent"
        )
        if role_assigned:
            desc += " and assigned the configured role."
        else:
            desc += "."

        await interaction.response.send_message(
            embed=success_embed("Verification Recorded", desc),
            ephemeral=True,
        )


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(VerifyView())

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        role_id = config.auto_role_id or config.welcome_role_id
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Auto-role on join")
                except discord.Forbidden:
                    logger.warning(
                        "Cannot assign auto-role %s (missing permissions)", role_id
                    )
                except discord.HTTPException as exc:
                    logger.warning("Auto-role failed: %s", exc)

        if not config.welcome_channel_id:
            return
        channel = member.guild.get_channel(config.welcome_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        embed = base_embed(
            title="Welcome to Stone FFA!",
            description=(
                f"Hey {member.mention}, welcome to the **Stone FFA** community!\n\n"
                f"• Server IP: `{config.minecraft_server_ip}`\n"
                f"• Website: {config.website_url}\n"
                f"• Store: {config.store_url}\n\n"
                "Read the rules and have fun!"
            ),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await channel.send(content=member.mention, embed=embed)
        except discord.HTTPException as exc:
            logger.warning("Failed to send welcome message: %s", exc)

        if config.log_channel_id:
            log_ch = member.guild.get_channel(config.log_channel_id)
            if isinstance(log_ch, discord.TextChannel):
                try:
                    await log_ch.send(
                        embed=info_embed(
                            "Member Joined",
                            f"{member.mention} (`{member.id}`)\n"
                            f"Account created: <t:{int(member.created_at.timestamp())}:R>",
                        )
                    )
                except discord.HTTPException:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if not config.log_channel_id:
            return
        log_ch = member.guild.get_channel(config.log_channel_id)
        if not isinstance(log_ch, discord.TextChannel):
            return
        try:
            await log_ch.send(
                embed=info_embed(
                    "Member Left",
                    f"{member} (`{member.id}`)",
                )
            )
        except discord.HTTPException:
            pass

    @app_commands.command(name="verifypanel", description="Post the verification panel (staff)")
    @staff_check()
    async def verifypanel(self, interaction: discord.Interaction) -> None:
        embed = base_embed(
            title="Stone FFA Verification",
            description=(
                "Click the button below to verify.\n\n"
                "Minecraft account linking can be added later; "
                "this button currently records your Discord verification only."
            ),
        )
        await interaction.response.send_message(embed=embed, view=VerifyView())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))

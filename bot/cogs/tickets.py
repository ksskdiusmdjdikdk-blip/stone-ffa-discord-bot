"""Professional ticket system for Stone FFA support."""

from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import config
from bot.database import db
from bot.logger import logger
from bot.utils.checks import is_staff, staff_check
from bot.utils.embeds import error_embed, success_embed, ticket_embed


class CloseConfirmView(discord.ui.View):
    def __init__(self, ticket_channel_id: int) -> None:
        super().__init__(timeout=60)
        self.ticket_channel_id = ticket_channel_id

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        channel = interaction.guild.get_channel(self.ticket_channel_id)
        if channel is None or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=error_embed("Error", "Ticket channel not found."), ephemeral=True
            )
            return

        record = await db.get_ticket_by_channel(channel.id)
        if record is None or record.status != "open":
            await interaction.response.send_message(
                embed=error_embed("Error", "This ticket is already closed."), ephemeral=True
            )
            return

        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                embed=error_embed("Error", "Invalid context."), ephemeral=True
            )
            return
        if member.id != record.owner_id and not is_staff(member):
            await interaction.response.send_message(
                embed=error_embed("Denied", "Only the ticket owner or staff can close."),
                ephemeral=True,
            )
            return

        await db.close_ticket(channel.id, member.id)
        await interaction.response.send_message(
            embed=success_embed("Closing", "Ticket will be closed in a few seconds…")
        )

        try:
            messages = []
            async for msg in channel.history(limit=50, oldest_first=True):
                author = msg.author.display_name
                content = msg.content or "[embed/attachment]"
                messages.append(f"[{msg.created_at:%Y-%m-%d %H:%M}] {author}: {content[:200]}")
            transcript = "\n".join(messages) if messages else "(empty)"
        except discord.HTTPException:
            transcript = "(could not fetch history)"

        log_channel_id = config.log_channel_id
        if log_channel_id:
            log_ch = interaction.guild.get_channel(log_channel_id)
            if isinstance(log_ch, discord.TextChannel):
                embed = ticket_embed(
                    "Ticket Closed",
                    f"**Channel:** {channel.name}\n"
                    f"**Owner:** <@{record.owner_id}>\n"
                    f"**Closed by:** {member.mention}",
                )
                try:
                    if len(transcript) > 3500:
                        transcript = transcript[:3500] + "\n… (truncated)"
                    embed.add_field(name="Recent messages", value=f"```{transcript}```", inline=False)
                    await log_ch.send(embed=embed)
                except discord.HTTPException:
                    logger.warning("Failed to send ticket close log")

        try:
            await channel.delete(reason=f"Ticket closed by {member}")
        except discord.HTTPException as exc:
            logger.warning("Failed to delete ticket channel: %s", exc)

        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_message("Close cancelled.", ephemeral=True)
        self.stop()


class TicketControlView(discord.ui.View):
    """Persistent view attached inside ticket channels."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="stoneffa:ticket_close",
    )
    async def close_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        view = CloseConfirmView(interaction.channel_id)
        await interaction.response.send_message(
            embed=ticket_embed(
                "Close Ticket?",
                "Are you sure you want to close this ticket? This cannot be undone.",
            ),
            view=view,
            ephemeral=True,
        )


class TicketPanelView(discord.ui.View):
    """Persistent panel with Create Ticket button."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="stoneffa:ticket_create",
    )
    async def create_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=error_embed("Error", "Guild only."), ephemeral=True
            )
            return

        existing = await db.get_open_ticket_by_owner(interaction.guild.id, interaction.user.id)
        if existing is not None:
            ch = interaction.guild.get_channel(existing.channel_id)
            mention = ch.mention if ch else f"`{existing.channel_id}`"
            await interaction.response.send_message(
                embed=error_embed(
                    "Ticket Already Open",
                    f"You already have an open ticket: {mention}",
                ),
                ephemeral=True,
            )
            return

        category = None
        if config.ticket_category_id:
            category = interaction.guild.get_channel(config.ticket_category_id)
            if not isinstance(category, discord.CategoryChannel):
                category = None

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True,
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
            ),
        }

        staff_role_id = config.ticket_support_role_id or config.staff_role_id
        if staff_role_id:
            role = interaction.guild.get_role(staff_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_messages=True,
                    read_message_history=True,
                )

        name = f"ticket-{interaction.user.name}"[:90]
        try:
            channel = await interaction.guild.create_text_channel(
                name=name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket opened by {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed(
                    "Missing Permissions",
                    "I need Manage Channels to create tickets.",
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=error_embed("Failed", str(exc)), ephemeral=True
            )
            return

        await db.create_ticket(interaction.guild.id, channel.id, interaction.user.id)

        embed = ticket_embed(
            "Support Ticket",
            f"Welcome {interaction.user.mention}!\n\n"
            "Please describe your issue. Staff will assist you shortly.\n"
            "Click **Close Ticket** when finished.",
        )
        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=TicketControlView(),
        )

        await interaction.response.send_message(
            embed=success_embed("Ticket Created", f"Your ticket: {channel.mention}"),
            ephemeral=True,
        )

        if config.log_channel_id:
            log_ch = interaction.guild.get_channel(config.log_channel_id)
            if isinstance(log_ch, discord.TextChannel):
                try:
                    await log_ch.send(
                        embed=ticket_embed(
                            "Ticket Opened",
                            f"**User:** {interaction.user.mention}\n"
                            f"**Channel:** {channel.mention}",
                        )
                    )
                except discord.HTTPException:
                    pass


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(TicketControlView())

    @app_commands.command(name="ticketpanel", description="Post the ticket creation panel (staff)")
    @staff_check()
    async def ticketpanel(self, interaction: discord.Interaction) -> None:
        embed = ticket_embed(
            "Stone FFA Support",
            "Need help? Click the button below to open a private support ticket.\n"
            "Please only open one ticket at a time.",
        )
        await interaction.response.send_message(embed=embed, view=TicketPanelView())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))

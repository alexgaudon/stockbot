import discord
from typing import Optional
from stockbot.stock_service import StockService


class StockReportView(discord.ui.View):
    """Interactive view for stock reports with refresh and period change buttons"""
    
    def __init__(self, stock_service: StockService, symbol: str, chart_period_months: int = 3):
        super().__init__(timeout=None)  # No timeout for persistent buttons
        self.stock_service = stock_service
        self.symbol = symbol
        self.chart_period_months = chart_period_months
        
        # Set period attributes on buttons after initialization
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id and item.custom_id.startswith("period_"):
                item.period = int(item.custom_id.split("_")[1])
        
        # Update button styles based on current period
        self._update_button_styles()
    
    def _update_button_styles(self):
        """Update button styles to highlight the current period"""
        for item in self.children:
            if isinstance(item, discord.ui.Button) and hasattr(item, 'period'):
                if item.period == self.chart_period_months:
                    item.style = discord.ButtonStyle.primary
                else:
                    item.style = discord.ButtonStyle.secondary
    
    async def _update_stock_data(self, interaction: discord.Interaction):
        """Fetch and update the stock data"""
        await interaction.response.defer()
        
        embed, file = await self.stock_service.get_stock_info(
            self.symbol,
            chart_period_months=self.chart_period_months
        )
        
        if embed is None:
            embed = discord.Embed(
                title="Error",
                description=f"Could not fetch data for {self.symbol}",
                color=discord.Color.red()
            )
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=self
            )
        else:
            # Update button styles
            self._update_button_styles()
            
            # Edit the message with new data
            if file:
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    embed=embed,
                    attachments=[file],
                    view=self
                )
            else:
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    embed=embed,
                    view=self
                )
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.green, custom_id="refresh")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the stock data"""
        await self._update_stock_data(interaction)
    
    @discord.ui.button(label="1M", style=discord.ButtonStyle.secondary, custom_id="period_1")
    async def period_1m(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Change chart period to 1 month"""
        self.chart_period_months = 1
        await self._update_stock_data(interaction)
    
    @discord.ui.button(label="3M", style=discord.ButtonStyle.secondary, custom_id="period_3")
    async def period_3m(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Change chart period to 3 months"""
        self.chart_period_months = 3
        await self._update_stock_data(interaction)
    
    @discord.ui.button(label="6M", style=discord.ButtonStyle.secondary, custom_id="period_6")
    async def period_6m(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Change chart period to 6 months"""
        self.chart_period_months = 6
        await self._update_stock_data(interaction)
    
    @discord.ui.button(label="1Y", style=discord.ButtonStyle.secondary, custom_id="period_12")
    async def period_1y(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Change chart period to 1 year"""
        self.chart_period_months = 12
        await self._update_stock_data(interaction)


class MinimalStockView(discord.ui.View):
    """Minimal interactive view for brief stock reports"""
    
    def __init__(self, stock_service: StockService, symbol: str):
        super().__init__(timeout=None)
        self.stock_service = stock_service
        self.symbol = symbol
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.green, custom_id="refresh_minimal")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the minimal stock data"""
        await interaction.response.defer()
        
        embed, file = await self.stock_service.get_stock_brief(self.symbol)
        
        if embed is None:
            embed = discord.Embed(
                title="Error",
                description=f"Could not fetch data for {self.symbol}",
                color=discord.Color.red()
            )
        
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=self
        )
    
    @discord.ui.button(label="📊 Full Report", style=discord.ButtonStyle.primary, custom_id="full_report")
    async def full_report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show full stock report with chart"""
        await interaction.response.defer()
        
        embed, file = await self.stock_service.get_stock_info(self.symbol, chart_period_months=3)
        
        if embed is None:
            embed = discord.Embed(
                title="Error",
                description=f"Could not fetch data for {self.symbol}",
                color=discord.Color.red()
            )
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=self
            )
        else:
            # Switch to full report view
            view = StockReportView(self.stock_service, self.symbol, chart_period_months=3)
            if file:
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    embed=embed,
                    attachments=[file],
                    view=view
                )
            else:
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    embed=embed,
                    view=view
                )


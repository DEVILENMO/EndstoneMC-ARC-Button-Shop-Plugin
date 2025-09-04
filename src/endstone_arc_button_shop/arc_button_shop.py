import datetime
import os
import json
import math

from endstone.command import Command, CommandSender
from endstone.event import event_handler, PlayerInteractEvent, BlockBreakEvent
from endstone.plugin import Plugin
from endstone.form import ActionForm, ModalForm, Label, TextInput
from endstone.block import Block

from .DatabaseManager import DatabaseManager
from .LanguageManager import LanguageManager
from .SettingManager import SettingManager


class ARCButtonShopPlugin(Plugin):
    prefix = "ARCButtonShopPlugin"
    api_version = "0.10"
    load = "POSTWORLD"

    commands = {
        "shop": {
            "description": "Open button shop interface",
            "usages": ["/shop"],
            "permissions": ["arc_button_shop.command.shop"],
        },
        "shopmanage": {
            "description": "Manage button shops, op only.",
            "usages": ["/shopmanage"]
        }
    }

    permissions = {
        "arc_button_shop.command.shop": {
            "description": "Allow users to access shop interface",
            "default": True
        }
    }

    def __init__(self):
        super().__init__()
        self.setting_shop_player = {}  # 玩家名 -> 商店设置数据
        self.CHUNK_SIZE = 16  # 区块大小，用于优化查询
    
    def _safe_log(self, level: str, message: str):
        """
        安全的日志记录方法，在logger未初始化时使用print
        :param level: 日志级别 (info, warning, error)
        :param message: 日志消息
        """
        if hasattr(self, 'logger') and self.logger is not None:
            if level.lower() == 'info':
                self.logger.info(message)
            elif level.lower() == 'warning':
                self.logger.warning(message)
            elif level.lower() == 'error':
                self.logger.error(message)
            else:
                self.logger.info(message)
        else:
            # 如果logger未初始化，使用print
            print(f"[{level.upper()}] {message}")

    def on_load(self) -> None:
        self._safe_log('info', "[ARCButtonShop] on_load is called!")
        
        # 初始化语言管理器
        self.language_manager = LanguageManager("CN")
        
        # 初始化设置管理器
        self.setting_manager = SettingManager()
        
        # 初始化默认配置
        self._init_default_settings()
        
        # 初始化数据库管理器
        db_path = os.path.join("plugins", "ARCButtonShop", "button_shop.db")
        self.db_manager = DatabaseManager(db_path)
        
        # 创建商店相关表
        self._create_shop_tables()
        
        # 初始化经济插件 - 检查 arc_core 优先，然后 umoney
        self._init_economy_plugin()

    def on_enable(self) -> None:
        self._safe_log('info', "[ARCButtonShop] on_enable is called!")
        self.register_events(self)

    def on_disable(self) -> None:
        self._safe_log('info', "[ARCButtonShop] on_disable is called!")
        
        # 关闭数据库连接
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
    
    def _init_default_settings(self) -> None:
        """初始化默认配置"""
        # 交易税率 (默认5%)
        tax_rate = self.setting_manager.GetSetting("trade_tax_rate")
        if tax_rate is None:
            self.setting_manager.SetSetting("trade_tax_rate", "0.05")
            self._safe_log('info', "[ARCButtonShop] Set default trade tax rate: 5%")
        
        # 最大商店数量限制 (默认50)
        max_shops = self.setting_manager.GetSetting("max_shops_per_player")
        if max_shops is None:
            self.setting_manager.SetSetting("max_shops_per_player", "50")
            self._safe_log('info', "[ARCButtonShop] Set default max shops per player: 50")
        
        # 是否启用交易税 (默认启用)
        tax_enabled = self.setting_manager.GetSetting("trade_tax_enabled")
        if tax_enabled is None:
            self.setting_manager.SetSetting("trade_tax_enabled", "true")
            self._safe_log('info', "[ARCButtonShop] Trade tax enabled by default")

    def _init_economy_plugin(self) -> None:
        """初始化经济插件 - 检查 arc_core 优先，然后 umoney"""
        try:
            self.economy_plugin = self.server.plugin_manager.get_plugin('arc_core')
            if self.economy_plugin is not None:
                self._safe_log('info', "[ARCButtonShop] Using ARC Core economy system for money rewards.")
            else:
                self.economy_plugin = self.server.plugin_manager.get_plugin('umoney')
                if self.economy_plugin is not None:
                    self._safe_log('info', "[ARCButtonShop] Using UMoney economy system for money rewards.")
                else:
                    self._safe_log('warning', "[ARCButtonShop] No supported economy plugin found (arc_core or umoney). Money rewards will not be available.")
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Failed to load economy plugin: {e}. Money rewards will not be available.")

    def _get_player_money(self, player_name: str) -> int:
        """获取玩家金钱数量"""
        if not self.economy_plugin:
            return 0
        
        try:
            if hasattr(self.economy_plugin, 'api_get_player_money'):
                # ARC Core API
                return self.economy_plugin.api_get_player_money(player_name)
            elif hasattr(self.economy_plugin, 'get_money'):
                # UMoney API
                return self.economy_plugin.get_money(player_name)
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Failed to get player money for {player_name}: {e}")
        
        return 0

    def _change_player_money(self, player_name: str, amount: int) -> bool:
        """改变玩家金钱数量"""
        if not self.economy_plugin:
            return False
        
        try:
            if hasattr(self.economy_plugin, 'api_change_player_money'):
                # ARC Core API
                return self.economy_plugin.api_change_player_money(player_name, amount)
            elif hasattr(self.economy_plugin, 'change_money'):
                # UMoney API
                return self.economy_plugin.change_money(player_name, amount)
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Failed to change player money for {player_name}: {e}")
        
        return False

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        match command.name:
            case "shop":
                if hasattr(sender, 'location') and hasattr(sender, 'send_form'):
                    self._show_shop_main_panel(sender)
                else:
                    sender.send_message(self.language_manager.GetText("PLAYER_ONLY_COMMAND"))
            case "shopmanage":
                return self._handle_shop_manage_command(sender, args)
        return True
    
    # 数据库
    def _create_shop_tables(self) -> None:
        """创建商店相关数据表"""
        
        # 创建商店表
        shop_fields = {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "shop_uuid": "TEXT NOT NULL UNIQUE",  # 商店唯一标识
            "owner_xuid": "TEXT NOT NULL",  # 店主XUID（主要标识符）
            "owner_name": "TEXT NOT NULL",  # 店主名称（用于显示）
            "shop_type": "TEXT NOT NULL DEFAULT 'sell'",  # 商店类型：'sell'出售, 'buy'收购
            "x": "INTEGER NOT NULL",  # 按钮X坐标
            "y": "INTEGER NOT NULL",  # 按钮Y坐标
            "z": "INTEGER NOT NULL",  # 按钮Z坐标
            "dimension": "TEXT NOT NULL",  # 维度
            "chunk_x": "INTEGER NOT NULL",  # 区块X坐标（用于优化查询）
            "chunk_z": "INTEGER NOT NULL",  # 区块Z坐标（用于优化查询）
            "item_type": "TEXT NOT NULL",  # 物品类型
            "item_data": "TEXT NOT NULL",  # 物品数据（JSON格式）
            "quantity": "INTEGER NOT NULL",  # 商品数量
            "unit_price": "REAL NOT NULL",  # 单价
            "stock": "INTEGER NOT NULL",  # 库存（出售商店为剩余库存，收购商店为资金余额）
            "collected_items": "TEXT",  # 收购商店收集的物品（JSON格式）
            "is_active": "INTEGER NOT NULL DEFAULT 1",  # 是否激活
            "create_time": "TEXT NOT NULL",  # 创建时间
            "last_purchase_time": "TEXT"  # 最后购买时间
        }
        
        if self.db_manager.create_table("button_shops", shop_fields):
            self._safe_log('info', "[ARCButtonShop] Button shops table created successfully")
        else:
            self._safe_log('error', "[ARCButtonShop] Failed to create button shops table")
        
        # 创建交易记录表
        transaction_fields = {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "shop_id": "INTEGER NOT NULL",  # 商店ID
            "buyer_xuid": "TEXT NOT NULL",  # 买家XUID（主要标识符）
            "buyer_name": "TEXT NOT NULL",  # 买家名称（用于显示）
            "quantity": "INTEGER NOT NULL",  # 购买数量
            "unit_price": "REAL NOT NULL",  # 购买时的单价
            "total_price": "REAL NOT NULL",  # 总价
            "transaction_time": "TEXT NOT NULL"  # 交易时间
        }
        
        if self.db_manager.create_table("shop_transactions", transaction_fields):
            self._safe_log('info', "[ARCButtonShop] Shop transactions table created successfully")
        else:
            self._safe_log('error', "[ARCButtonShop] Failed to create shop transactions table")
        
        # 创建区块索引表（用于快速查询）
        chunk_index_fields = {
            "chunk_x": "INTEGER NOT NULL",
            "chunk_z": "INTEGER NOT NULL", 
            "dimension": "TEXT NOT NULL",
            "shop_count": "INTEGER NOT NULL DEFAULT 0",
            "PRIMARY KEY": "(chunk_x, chunk_z, dimension)"
        }
        
        if self.db_manager.create_table("chunk_index", chunk_index_fields):
            self._safe_log('info', "[ARCButtonShop] Chunk index table created successfully")
        else:
            self._safe_log('error', "[ARCButtonShop] Failed to create chunk index table")

    # 事件监听器
    @event_handler
    def on_player_interact(self, event: PlayerInteractEvent):
        """处理玩家交互事件"""
        try:
            player = event.player
            block = event.block

            # 检查block是否为None
            if block is None:
                return

            # 检查玩家是否处于商店设置状态
            if player.name in self.setting_shop_player:
                if not self._is_button_block(block):
                    # 提示玩家当前交互的不是按钮
                    player.send_message(self.language_manager.GetText("SHOP_NOT_BUTTON").format(block.type))
                    return
                else:
                    self._handle_shop_creation(player, block)
                    event.is_cancelled = True
                return
            else:
                # 检查是否是按钮交互
                if not self._is_button_block(block):
                    return
                
                # 通过区块索引快速检查该位置是否有商店
                shop_data = self._get_shop_at_position_optimized(block.x, block.y, block.z, block.dimension.name)
                if shop_data:
                    self._show_shop_detail_panel(player, shop_data)
                    event.is_cancelled = True
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Player interact error: {str(e)}")

    @event_handler
    def on_block_break(self, event: BlockBreakEvent):
        """处理方块破坏事件（商店保护）"""
        try:
            player = event.player
            block = event.block
            
            # 检查block是否为None
            if block is None:
                return
            
            # 检查是否是按钮破坏
            if not self._is_button_block(block):
                return
            
            # 检查该位置是否有商店
            shop_data = self._get_shop_at_position_optimized(block.x, block.y, block.z, block.dimension.name)
            if not shop_data:
                return  # 没有商店，允许正常破坏
            
            # 检查商店是否有效
            if not shop_data['is_active']:
                return  # 商店已失效，允许破坏
            
            # 检查是否是店主
            if str(player.unique_id) == shop_data['owner_xuid']:
                # 店主破坏按钮，删除商店
                self._handle_shop_removal_by_owner(player, shop_data)
                event.is_cancelled = True
                return
            else:
                # 非店主破坏按钮，阻止破坏并提示
                player.send_message(self.language_manager.GetText("SHOP_BREAK_PROTECTED").format(shop_data['owner_name']))
                event.is_cancelled = True
                return
                
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Block break error: {str(e)}")

    # 商店管理系统
    def _show_shop_main_panel(self, player):
        """显示商店主面板"""
        try:
            main_panel = ActionForm(
                title=self.language_manager.GetText("SHOP_MAIN_PANEL_TITLE"),
                content=self.language_manager.GetText("SHOP_MAIN_PANEL_CONTENT")
            )
            
            # 创建商店按钮
            main_panel.add_button(
                self.language_manager.GetText("SHOP_CREATE_BUTTON"),
                on_click=lambda sender: self._show_shop_type_selection_panel(sender)
            )
            
            # 我的商店按钮
            main_panel.add_button(
                self.language_manager.GetText("SHOP_MY_SHOPS_BUTTON"),
                on_click=lambda sender: self._show_my_shops_panel(sender)
            )
            
            # 附近商店按钮
            main_panel.add_button(
                self.language_manager.GetText("SHOP_NEARBY_BUTTON"), 
                on_click=lambda sender: self._show_nearby_shops_panel(sender)
            )
            
            # 关闭按钮
            main_panel.add_button(
                self.language_manager.GetText("SHOP_CLOSE_BUTTON"),
                on_click=lambda sender: None
            )
            
            player.send_form(main_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show main panel error: {str(e)}")
            player.send_message(self.language_manager.GetText("SHOP_PANEL_ERROR"))

    def _show_shop_type_selection_panel(self, player):
        """显示商店类型选择面板"""
        try:
            type_panel = ActionForm(
                title=self.language_manager.GetText("SHOP_TYPE_SELECT_TITLE"),
                content=self.language_manager.GetText("SHOP_TYPE_SELECT_CONTENT")
            )
            
            # 出售商店按钮
            type_panel.add_button(
                self.language_manager.GetText("SHOP_TYPE_SELL_BUTTON"),
                on_click=lambda sender: self._show_item_selection_panel(sender, "sell")
            )
            
            # 收购商店按钮
            type_panel.add_button(
                self.language_manager.GetText("SHOP_TYPE_BUY_BUTTON"),
                on_click=lambda sender: self._show_item_selection_panel(sender, "buy")
            )
            
            # 返回按钮
            type_panel.add_button(
                self.language_manager.GetText("SHOP_BACK_BUTTON"),
                on_click=lambda sender: self._show_shop_main_panel(sender)
            )
            
            player.send_form(type_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show shop type selection panel error: {str(e)}")
            player.send_message(self.language_manager.GetText("SHOP_PANEL_ERROR"))

    def _show_item_selection_panel(self, player, shop_type="sell"):
        """显示物品选择面板"""
        try:
            # 获取玩家背包中的物品
            inventory_items = self._get_player_inventory_items(player)
            
            if not inventory_items:
                no_items_panel = ActionForm(
                    title=self.language_manager.GetText("SHOP_ITEM_SELECT_TITLE"),
                    content=self.language_manager.GetText("SHOP_NO_ITEMS"),
                    on_close=lambda sender: self._show_shop_main_panel(sender)
                )
                player.send_form(no_items_panel)
                return
            
            # 创建物品选择面板
            item_select_panel = ActionForm(
                title=self.language_manager.GetText("SHOP_ITEM_SELECT_TITLE"),
                content=self.language_manager.GetText("SHOP_ITEM_SELECT_CONTENT")
            )
            
            # 为每个物品添加按钮
            for item_info in inventory_items:
                item_name = item_info['name']
                item_count = item_info['count']
                
                # 构建按钮文本，包含附魔和Lore信息
                button_text = f"{item_name} x{item_count}"
                
                # 添加附魔信息
                if item_info.get('enchants'):
                    button_text += " §b[附魔]"
                
                # 添加Lore信息
                if item_info.get('lore'):
                    button_text += " §d[Lore]"
                
                item_select_panel.add_button(
                    button_text,
                    on_click=lambda sender, item=item_info: self._show_price_setting_panel(sender, item, shop_type)
                )
            
            # 返回按钮
            item_select_panel.add_button(
                self.language_manager.GetText("SHOP_BACK_BUTTON"),
                on_click=lambda sender: self._show_shop_main_panel(sender)
            )
            
            player.send_form(item_select_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show item selection panel error: {str(e)}")
            player.send_message(self.language_manager.GetText("SHOP_PANEL_ERROR"))

    def _show_price_setting_panel(self, player, item_info, shop_type="sell"):
        """显示价格设置面板"""
        try:
            controls = []
            
            if shop_type == "sell":
                # 出售商店 - 显示物品信息
                item_info_text = f"物品: {item_info['name']}\n数量: {item_info['count']}"
                
                # 添加附魔信息
                if item_info.get('enchants'):
                    item_info_text += "\n附魔:"
                    for enchant_id, level in item_info['enchants'].items():
                        item_info_text += f"\n  {enchant_id} [等级 {level}]"
                
                # 添加Lore信息
                if item_info.get('lore'):
                    item_info_text += "\nLore:"
                    for lore_line in item_info['lore']:
                        item_info_text += f"\n  {lore_line}"
                
                item_label = Label(text=item_info_text)
                controls.append(item_label)
                
                # 单价输入
                price_input = TextInput(
                    label=self.language_manager.GetText("SHOP_PRICE_INPUT_LABEL"),
                    placeholder=self.language_manager.GetText("SHOP_PRICE_INPUT_PLACEHOLDER"),
                    default_value="10"
                )
                controls.append(price_input)
                
            else:  # buy
                # 收购商店 - 显示收购信息
                buy_info_text = f"收购物品: {item_info['name']}"
                
                # 添加附魔信息
                if item_info.get('enchants'):
                    buy_info_text += "\n附魔:"
                    for enchant_id, level in item_info['enchants'].items():
                        buy_info_text += f"\n  {enchant_id} [等级 {level}]"
                
                # 添加Lore信息
                if item_info.get('lore'):
                    buy_info_text += "\nLore:"
                    for lore_line in item_info['lore']:
                        buy_info_text += f"\n  {lore_line}"
                
                buy_label = Label(text=buy_info_text)
                controls.append(buy_label)
                
                # 收购单价输入
                price_input = TextInput(
                    label=self.language_manager.GetText("SHOP_BUY_PRICE_INPUT_LABEL"),
                    placeholder=self.language_manager.GetText("SHOP_BUY_PRICE_INPUT_PLACEHOLDER"),
                    default_value="10"
                )
                controls.append(price_input)
                
                # 预算输入
                budget_input = TextInput(
                    label=self.language_manager.GetText("SHOP_BUY_BUDGET_LABEL"),
                    placeholder=self.language_manager.GetText("SHOP_BUY_BUDGET_PLACEHOLDER"),
                    default_value="1000"
                )
                controls.append(budget_input)
            
            def process_shop_creation(sender, json_str: str):
                try:
                    data = json.loads(json_str)
                    price_str = data[1]  # 价格输入
                    
                    # 验证价格
                    try:
                        unit_price = int(float(price_str))
                        if unit_price <= 0:
                            raise ValueError("Price must be positive")
                    except ValueError:
                        result_form = ActionForm(
                            title=self.language_manager.GetText("SHOP_RESULT_TITLE"),
                            content=self.language_manager.GetText("SHOP_INVALID_PRICE"),
                            on_close=lambda s: self._show_price_setting_panel(s, item_info, shop_type)
                        )
                        sender.send_form(result_form)
                        return
                    
                    budget = 0
                    if shop_type == "buy":
                        # 收购商店需要验证预算
                        budget_str = data[2]  # 预算输入
                        try:
                            budget = int(float(budget_str))
                            if budget <= 0:
                                raise ValueError("Budget must be positive")
                            if budget < unit_price:
                                raise ValueError("Budget must be at least equal to unit price")
                        except ValueError:
                            result_form = ActionForm(
                                title=self.language_manager.GetText("SHOP_RESULT_TITLE"),
                                content=self.language_manager.GetText("SHOP_INVALID_BUDGET"),
                                on_close=lambda s: self._show_price_setting_panel(s, item_info, shop_type)
                            )
                            sender.send_form(result_form)
                            return
                        
                        # 检查玩家资金是否足够
                        player_money = self._get_player_money(sender.name)
                        if player_money < int(budget):
                                result_form = ActionForm(
                                    title=self.language_manager.GetText("SHOP_RESULT_TITLE"),
                                    content=self.language_manager.GetText("SHOP_INSUFFICIENT_FUNDS_FOR_BUDGET").format(int(budget), player_money),
                                    on_close=lambda s: self._show_price_setting_panel(s, item_info, shop_type)
                                )
                                sender.send_form(result_form)
                                return
                    
                    # 设置商店创建数据
                    shop_data = {
                        'item_info': item_info,
                        'unit_price': unit_price,
                        'shop_type': shop_type,
                        'budget': budget,  # 收购商店的预算，出售商店为0
                        'create_time': datetime.datetime.now()
                    }
                    
                    self.setting_shop_player[sender.name] = shop_data
                    
                    # 显示设置说明
                    if shop_type == "sell":
                        instruction_content = self.language_manager.GetText("SHOP_SETUP_INSTRUCTION").format(
                            item_info['name'], item_info['count'], unit_price
                        ).replace('\\n', '\n')
                    else:
                        instruction_content = self.language_manager.GetText("SHOP_BUY_SETUP_INSTRUCTION").format(
                            item_info['name'], unit_price, int(budget), int(budget / unit_price)
                        ).replace('\\n', '\n')
                    
                    instruction_form = ActionForm(
                        title=self.language_manager.GetText("SHOP_SETUP_TITLE"),
                        content=instruction_content,
                        on_close=lambda s: None
                    )
                    sender.send_form(instruction_form)
                    
                except Exception as e:
                    self._safe_log('error', f"[ARCButtonShop] Process shop creation error: {str(e)}")
                    error_form = ActionForm(
                        title=self.language_manager.GetText("SHOP_RESULT_TITLE"),
                        content=self.language_manager.GetText("SHOP_PANEL_ERROR"),
                        on_close=lambda s: self._show_shop_main_panel(s)
                    )
                    sender.send_form(error_form)
            
            title = self.language_manager.GetText("SHOP_BUY_PRICE_PANEL_TITLE" if shop_type == "buy" else "SHOP_PRICE_PANEL_TITLE")
            price_panel = ModalForm(
                title=title,
                controls=controls,
                on_close=lambda sender: self._show_item_selection_panel(sender, shop_type),
                on_submit=process_shop_creation
            )
            
            player.send_form(price_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show price setting panel error: {str(e)}")
            player.send_message(self.language_manager.GetText("SHOP_PANEL_ERROR"))

    def _show_shop_detail_panel(self, player, shop_data):
        """显示商店详情面板"""
        try:
            item_data = json.loads(shop_data['item_data'])
            shop_type = shop_data.get('shop_type', 'sell')
            
            # 构建商店信息
            shop_info = f"店主: {shop_data['owner_name']}\n"
            shop_info += f"物品: {item_data.get('name', 'Unknown')}\n"
            shop_info += f"库存: {shop_data['stock']}\n"
            shop_info += f"单价: {shop_data['unit_price']}\n"
            
            # 添加附魔信息
            if item_data.get('enchants'):
                shop_info += "\n附魔:"
                for enchant_id, level in item_data['enchants'].items():
                    shop_info += f"\n  {enchant_id} [等级 {level}]"
            
            # 添加Lore信息
            if item_data.get('lore'):
                shop_info += "\nLore:"
                for lore_line in item_data['lore']:
                    shop_info += f"\n  {lore_line}"
            
            detail_panel = ActionForm(
                title=self.language_manager.GetText("SHOP_DETAIL_TITLE"),
                content=shop_info
            )
            
            # 如果不是店主且有库存，添加购买按钮
            if str(player.unique_id) != shop_data['owner_xuid'] and shop_data['stock'] > 0:
                if shop_type == "sell":
                    # 出售商店 - 显示购买按钮
                    detail_panel.add_button(
                        self.language_manager.GetText("SHOP_BUY_BUTTON"),
                        on_click=lambda sender: self._show_purchase_panel(sender, shop_data)
                    )
                else:
                    # 收购商店 - 显示出售按钮
                    detail_panel.add_button(
                        self.language_manager.GetText("SHOP_SELL_BUTTON"),
                        on_click=lambda sender: self._show_purchase_panel(sender, shop_data)
                    )
            elif str(player.unique_id) == shop_data['owner_xuid']:
                # 店主管理按钮
                detail_panel.add_button(
                    self.language_manager.GetText("SHOP_MANAGE_BUTTON"),
                    on_click=lambda sender: self._show_shop_manage_panel(sender, shop_data)
                )
            
            # 关闭按钮
            detail_panel.add_button(
                self.language_manager.GetText("SHOP_CLOSE_BUTTON"),
                on_click=lambda sender: None
            )
            
            player.send_form(detail_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show shop detail error: {str(e)}")
            player.send_message(self.language_manager.GetText("SHOP_PANEL_ERROR"))

    def _show_purchase_panel(self, player, shop_data):
        """显示购买面板"""
        try:
            item_data = json.loads(shop_data['item_data'])
            shop_type = shop_data.get('shop_type', 'sell')
            
            # 商品信息标签
            if shop_type == "sell":
                purchase_info = f"物品: {item_data.get('name', 'Unknown')}\n"
                purchase_info += f"库存: {shop_data['stock']}\n"
                purchase_info += f"单价: {shop_data['unit_price']}\n"
            else:
                purchase_info = f"收购物品: {item_data.get('name', 'Unknown')}\n"
                purchase_info += f"预算: {shop_data['stock']}\n"
                purchase_info += f"收购价: {shop_data['unit_price']}\n"
            
            # 添加附魔信息
            if item_data.get('enchants'):
                purchase_info += "\n附魔:"
                for enchant_id, level in item_data['enchants'].items():
                    purchase_info += f"\n  {enchant_id} [等级 {level}]"
            
            # 添加Lore信息
            if item_data.get('lore'):
                purchase_info += "\nLore:"
                for lore_line in item_data['lore']:
                    purchase_info += f"\n  {lore_line}"
            
            # 添加税收信息
            tax_rate = self._get_tax_rate()
            if tax_rate > 0:
                tax_percent = int(tax_rate * 100)
                purchase_info += f"\n\n§7交易税: {tax_percent}%"
            
            item_label = Label(text=purchase_info)
            
            # 数量输入
            if shop_type == "sell":
                quantity_input = TextInput(
                    label=self.language_manager.GetText("SHOP_QUANTITY_LABEL"),
                    placeholder=self.language_manager.GetText("SHOP_QUANTITY_PLACEHOLDER").format(shop_data['stock']),
                    default_value="1"
                )
            else:
                quantity_input = TextInput(
                    label=self.language_manager.GetText("SHOP_SELL_QUANTITY_LABEL"),
                    placeholder=self.language_manager.GetText("SHOP_SELL_QUANTITY_PLACEHOLDER").format(shop_data['stock']),
                    default_value="1"
                )
            
            def process_purchase(sender, json_str: str):
                try:
                    data = json.loads(json_str)
                    quantity_str = data[1]  # 数量输入
                    
                    # 验证数量
                    try:
                        quantity = int(quantity_str)
                        if quantity <= 0:
                            raise ValueError("Quantity must be positive")
                        if quantity > shop_data['stock']:
                            raise ValueError("Not enough stock")
                    except ValueError as e:
                        result_form = ActionForm(
                            title=self.language_manager.GetText("SHOP_RESULT_TITLE"),
                            content=self.language_manager.GetText("SHOP_INVALID_QUANTITY"),
                            on_close=lambda s: self._show_purchase_panel(s, shop_data)
                        )
                        sender.send_form(result_form)
                        return
                    
                    # 执行购买
                    success, message = self._execute_purchase(sender, shop_data, quantity)
                    
                    result_form = ActionForm(
                        title=self.language_manager.GetText("SHOP_RESULT_TITLE"),
                        content=message,
                        on_close=lambda s: None
                    )
                    sender.send_form(result_form)
                    
                except Exception as e:
                    self._safe_log('error', f"[ARCButtonShop] Process purchase error: {str(e)}")
                    error_form = ActionForm(
                        title=self.language_manager.GetText("SHOP_RESULT_TITLE"),
                        content=self.language_manager.GetText("SHOP_PANEL_ERROR"),
                        on_close=lambda s: None
                    )
                    sender.send_form(error_form)
            
            # 根据商店类型选择标题
            if shop_type == "sell":
                panel_title = self.language_manager.GetText("SHOP_PURCHASE_TITLE")
            else:
                panel_title = self.language_manager.GetText("SHOP_SELL_TITLE")
            
            purchase_panel = ModalForm(
                title=panel_title,
                controls=[item_label, quantity_input],
                on_close=lambda sender: self._show_shop_detail_panel(sender, shop_data),
                on_submit=process_purchase
            )
            
            player.send_form(purchase_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show purchase panel error: {str(e)}")
            player.send_message(self.language_manager.GetText("SHOP_PANEL_ERROR"))

    # 商店操作相关方法
    def _handle_shop_creation(self, player, block):
        """处理商店创建"""
        try:
            if player.name not in self.setting_shop_player:
                return
            
            shop_data = self.setting_shop_player[player.name]
            item_info = shop_data['item_info']
            unit_price = shop_data['unit_price']
            shop_type = shop_data.get('shop_type', 'sell')
            budget = shop_data.get('budget', 0)
            
            # 检查该位置是否已有商店
            existing_shop = self._get_shop_at_position(block.x, block.y, block.z, block.dimension.name)
            if existing_shop:
                player.send_message(self.language_manager.GetText("SHOP_ALREADY_EXISTS"))
                return
            
            if shop_type == "sell":
                # 出售商店 - 检查玩家是否还有该物品
                if not self._player_has_item(player, item_info):
                    player.send_message(self.language_manager.GetText("SHOP_ITEM_NOT_FOUND"))
                    del self.setting_shop_player[player.name]
                    return
            else:
                # 收购商店 - 检查玩家资金是否足够预算
                player_money = self._get_player_money(player.name)
                if player_money < int(budget):
                        player.send_message(self.language_manager.GetText("SHOP_INSUFFICIENT_FUNDS_FOR_BUDGET").format(int(budget), player_money))
                        del self.setting_shop_player[player.name]
                        return
            
            # 创建商店
            shop_uuid = self._generate_shop_uuid()
            chunk_x, chunk_z = self._get_chunk_coords(block.x, block.z)
            
            # 根据商店类型设置不同的数量和库存
            if shop_type == "sell":
                quantity = item_info['count']
                stock = item_info['count']  # 出售商店的库存是物品数量
            else:  # buy
                quantity = int(budget / unit_price)  # 收购商店能收购的最大数量
                stock = int(budget)  # 收购商店的库存是预算金额
            
            new_shop = {
                'shop_uuid': shop_uuid,
                'owner_xuid': str(player.unique_id),
                'owner_name': player.name,
                'shop_type': shop_type,
                'x': block.x,
                'y': block.y,
                'z': block.z,
                'dimension': block.dimension.name,
                'chunk_x': chunk_x,
                'chunk_z': chunk_z,
                'item_type': item_info['type'],
                'item_data': json.dumps(item_info),
                'quantity': quantity,
                'unit_price': int(unit_price),
                'stock': stock,
                'create_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 根据商店类型执行不同的操作
            operation_success = False
            
            if shop_type == "sell":
                # 出售商店 - 从玩家背包移除物品
                operation_success = self._remove_item_from_player(player, item_info)
                if not operation_success:
                    player.send_message(self.language_manager.GetText("SHOP_ITEM_REMOVE_FAILED"))
            else:
                # 收购商店 - 从玩家资金中扣除预算
                operation_success = self._change_player_money(player.name, -int(budget))
                if not operation_success:
                        player.send_message(self.language_manager.GetText("SHOP_BUDGET_DEDUCT_FAILED"))
            
            if operation_success:
                # 插入商店数据
                if self.db_manager.insert("button_shops", new_shop):
                    # 更新区块索引
                    self._update_chunk_index(chunk_x, chunk_z, block.dimension.name, 1)
                    
                    if shop_type == "sell":
                        player.send_message(self.language_manager.GetText("SHOP_CREATED_SUCCESS").format(
                            item_info['name'], item_info['count'], unit_price
                        ))
                    else:
                        player.send_message(self.language_manager.GetText("SHOP_BUY_CREATED_SUCCESS").format(
                            item_info['name'], unit_price, int(budget), quantity
                        ))
                    self._safe_log('info', f"[ARCButtonShop] Shop created by {player.name} at ({block.x}, {block.y}, {block.z})")
                else:
                    # 如果创建失败，根据商店类型进行回滚
                    if shop_type == "sell":
                        self._give_item_to_player(player, item_info)
                    else:
                        # 退还预算资金
                        self._change_player_money(player.name, int(budget))
                    player.send_message(self.language_manager.GetText("SHOP_CREATE_FAILED"))
            else:
                player.send_message(self.language_manager.GetText("SHOP_ITEM_REMOVE_FAILED"))
            
            # 清除设置状态
            del self.setting_shop_player[player.name]
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Handle shop creation error: {str(e)}")
            player.send_message(self.language_manager.GetText("SHOP_CREATE_FAILED"))
            if player.name in self.setting_shop_player:
                del self.setting_shop_player[player.name]

    def _execute_purchase(self, player, shop_data, quantity):
        """执行购买操作（支持出售商店、收购商店和税收）"""
        try:
            shop_type = shop_data.get('shop_type', 'sell')
            base_price = int(quantity * shop_data['unit_price'])
            tax_amount = self._calculate_tax(base_price)
            total_price = base_price + tax_amount
            
            # 检查经济插件是否可用
            if not self.economy_plugin:
                return False, self.language_manager.GetText("SHOP_CORE_PLUGIN_NOT_FOUND")
            
            # 检查当前商店状态
            current_shop = self._get_shop_by_id(shop_data['id'])
            if not current_shop or not current_shop['is_active']:
                return False, self.language_manager.GetText("SHOP_NOT_AVAILABLE")
            
            if shop_type == "sell":
                return self._execute_sell_shop_purchase(player, current_shop, quantity, base_price, tax_amount, total_price)
            else:  # buy
                return self._execute_buy_shop_purchase(player, current_shop, quantity, base_price, tax_amount, total_price)
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Execute purchase error: {str(e)}")
            return False, self.language_manager.GetText("SHOP_PURCHASE_ERROR")

    def _execute_sell_shop_purchase(self, player, shop_data, quantity, base_price, tax_amount, total_price):
        """执行出售商店的购买操作"""
        try:
            # 检查买家资金
            buyer_money = self._get_player_money(player.name)
            if buyer_money < total_price:
                return False, self.language_manager.GetText("SHOP_INSUFFICIENT_FUNDS").format(total_price, buyer_money)
            
            # 检查库存（对于出售商店，stock是物品数量）
            if shop_data['stock'] < quantity:
                return False, self.language_manager.GetText("SHOP_INSUFFICIENT_STOCK")
            
            # 扣除买家资金（包含税费）
            if not self._change_player_money(player.name, -total_price):
                return False, self.language_manager.GetText("SHOP_PAYMENT_FAILED")
            
            # 给店主增加资金（不含税费）
            if not self._change_player_money(shop_data['owner_name'], base_price):
                # 如果给店主加钱失败，返还买家资金
                self._change_player_money(player.name, total_price)
                return False, self.language_manager.GetText("SHOP_OWNER_PAYMENT_FAILED")
            
            # 更新库存
            new_stock = shop_data['stock'] - quantity
            update_data = {
                'stock': new_stock,
                'last_purchase_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if new_stock <= 0:
                update_data['is_active'] = 0  # 库存为0时设为非活跃
            
            self.db_manager.update(
                table='button_shops',
                data=update_data,
                where='id = ?',
                params=(shop_data['id'],)
            )
            
            # 给买家物品
            item_data = json.loads(shop_data['item_data'])
            purchase_item = {
                'type': item_data['type'],
                'name': item_data['name'],
                'count': quantity,
                'data': item_data.get('data', 0)
            }
            
            if self._give_item_to_player(player, purchase_item):
                # 记录交易
                self._record_transaction(shop_data['id'], player, quantity, shop_data['unit_price'], total_price, tax_amount)
                
                # 通知店主
                self._notify_shop_owner(shop_data, player.name, quantity, item_data['name'], base_price, "sell")
                
                return True, self._get_purchase_success_message(quantity, item_data['name'], total_price, tax_amount)
            else:
                # 交易失败回滚
                self._rollback_sell_transaction(player, shop_data, total_price, base_price)
                return False, self.language_manager.GetText("SHOP_ITEM_GIVE_FAILED")
                
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Execute sell shop purchase error: {str(e)}")
            return False, self.language_manager.GetText("SHOP_PURCHASE_ERROR")

    def _execute_buy_shop_purchase(self, player, shop_data, quantity, base_price, tax_amount, total_price):
        """执行收购商店的购买操作（玩家出售物品给收购商店）"""
        try:
            # 对于收购商店：玩家是卖家，shop_owner是买家
            # 检查商店预算（对于收购商店，stock是预算余额）
            if shop_data['stock'] < base_price:
                return False, self.language_manager.GetText("SHOP_INSUFFICIENT_BUDGET")
            
            # 检查玩家是否有足够的物品
            item_data = json.loads(shop_data['item_data'])
            required_item = {
                'type': item_data['type'],
                'name': item_data['name'],
                'count': quantity,
                'data': item_data.get('data', 0)
            }
            
            if not self._player_has_item(player, required_item):
                return False, self.language_manager.GetText("SHOP_PLAYER_NO_ITEMS")
            
            # 从玩家背包移除物品
            if not self._remove_item_from_player(player, required_item):
                return False, self.language_manager.GetText("SHOP_ITEM_REMOVE_FAILED")
            
            # 给玩家资金（扣除税费后）
            player_income = base_price - tax_amount
            if not self._change_player_money(player.name, player_income):
                # 归还物品
                self._give_item_to_player(player, required_item)
                return False, self.language_manager.GetText("SHOP_PAYMENT_FAILED")
            
            # 更新商店预算和收集的物品
            new_budget = shop_data['stock'] - base_price
            
            # 获取当前收集的物品
            collected_items = []
            if shop_data.get('collected_items'):
                try:
                    collected_items = json.loads(shop_data['collected_items'])
                except:
                    collected_items = []
            
            # 添加新收集的物品
            collected_item = {
                'type': item_data['type'],
                'name': item_data['name'],
                'count': quantity,
                'data': item_data.get('data', 0),
                'enchants': item_data.get('enchants', {}),
                'lore': item_data.get('lore', []),
                'collect_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            collected_items.append(collected_item)
            
            update_data = {
                'stock': new_budget,
                'collected_items': json.dumps(collected_items),
                'last_purchase_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if new_budget < shop_data['unit_price']:
                update_data['is_active'] = 0  # 预算不足时设为非活跃
            
            self.db_manager.update(
                table='button_shops',
                data=update_data,
                where='id = ?',
                params=(shop_data['id'],)
            )
            
            # 记录交易（注意：对收购商店，玩家是卖家）
            self._record_transaction(shop_data['id'], player, quantity, shop_data['unit_price'], base_price, tax_amount, is_buy_shop=True)
            
            # 通知店主
            self._notify_shop_owner(shop_data, player.name, quantity, item_data['name'], base_price, "buy")
            
            return True, self._get_sell_success_message(quantity, item_data['name'], player_income, tax_amount)
                
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Execute buy shop purchase error: {str(e)}")
            return False, self.language_manager.GetText("SHOP_PURCHASE_ERROR")

    # 交易辅助方法
    def _record_transaction(self, shop_id, player, quantity, unit_price, total_price, tax_amount, is_buy_shop=False):
        """记录交易"""
        try:
            transaction_data = {
                'shop_id': shop_id,
                'buyer_xuid': str(player.unique_id),
                'buyer_name': player.name,
                'quantity': quantity,
                'unit_price': unit_price,
                'total_price': total_price,
                'transaction_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.db_manager.insert("shop_transactions", transaction_data)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Record transaction error: {str(e)}")

    def _notify_shop_owner(self, shop_data, buyer_name, quantity, item_name, amount, shop_type):
        """通知店主"""
        try:
            owner_player = self.server.get_player(shop_data['owner_name'])
            if owner_player:
                if shop_type == "sell":
                    message = self.language_manager.GetText("SHOP_SALE_NOTIFICATION").format(
                        buyer_name, quantity, item_name, amount
                    )
                else:
                    message = self.language_manager.GetText("SHOP_BUY_NOTIFICATION").format(
                        buyer_name, quantity, item_name, amount
                    )
                owner_player.send_message(message)
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Notify shop owner error: {str(e)}")

    def _get_purchase_success_message(self, quantity, item_name, total_price, tax_amount):
        """获取购买成功消息"""
        if tax_amount > 0:
            tax_percent = int(self._get_tax_rate() * 100)
            return self.language_manager.GetText("SHOP_PURCHASE_SUCCESS_WITH_TAX").format(
                quantity, item_name, total_price, tax_amount
            ) + f"\n§7交易税: {tax_percent}% (税费: {tax_amount})"
        else:
            return self.language_manager.GetText("SHOP_PURCHASE_SUCCESS").format(
                quantity, item_name, total_price
            )

    def _get_sell_success_message(self, quantity, item_name, income, tax_amount):
        """获取出售成功消息"""
        if tax_amount > 0:
            tax_percent = int(self._get_tax_rate() * 100)
            return self.language_manager.GetText("SHOP_SELL_SUCCESS_WITH_TAX").format(
                quantity, item_name, income, tax_amount
            ) + f"\n§7交易税: {tax_percent}% (税费: {tax_amount})"
        else:
            return self.language_manager.GetText("SHOP_SELL_SUCCESS").format(
                quantity, item_name, income
            )

    def _rollback_sell_transaction(self, player, shop_data, total_price, base_price):
        """回滚出售交易"""
        try:
            # 退还买家资金
            self._change_player_money(player.name, total_price)
            # 扣除店主资金
            self._change_player_money(shop_data['owner_name'], -base_price)
            # 恢复库存
            self.db_manager.update(
                table='button_shops',
                data={'stock': shop_data['stock']},
                where='id = ?',
                params=(shop_data['id'],)
            )
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Rollback transaction error: {str(e)}")

    # 辅助方法
    def _is_button_block(self, block: Block) -> bool:
        """检查是否为按钮方块"""
        # 检查block是否为None
        if block is None:
            return False
            
        # 检查block.type是否为None
        if block.type is None:
            return False
            
        # 检查方块类型是否为按钮
        button_types = [
            "minecraft:wooden_button", "minecraft:stone_button", "minecraft:birch_button",
            "minecraft:spruce_button", "minecraft:jungle_button", "minecraft:acacia_button",
            "minecraft:dark_oak_button", "minecraft:mangrove_button", "minecraft:cherry_button",
            "minecraft:bamboo_button", "minecraft:crimson_button", "minecraft:warped_button",
            "minecraft:polished_blackstone_button"
        ]
        
        # 安全地获取block.type.id
        try:
            if hasattr(block.type, 'id'):
                return block.type.id in button_types
            else:
                # 如果block.type没有id属性，尝试转换为字符串进行比较
                block_type_str = str(block.type)
                return block_type_str in button_types
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Error checking button block: {str(e)}")
            return False

    def _get_shop_at_position(self, x: int, y: int, z: int, dimension: str):
        """获取指定位置的商店（直接查询，用于API接口）"""
        try:
            return self.db_manager.query_one(
                "SELECT * FROM button_shops WHERE x = ? AND y = ? AND z = ? AND dimension = ? AND is_active = 1",
                (x, y, z, dimension)
            )
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Get shop at position error: {str(e)}")
            return None

    def _get_shop_at_position_optimized(self, x: int, y: int, z: int, dimension: str):
        """获取指定位置的商店（优化版本，先查区块索引）"""
        try:
            # 1. 计算区块坐标
            chunk_x, chunk_z = self._get_chunk_coords(x, z)
            
            # 2. 检查该区块是否有商店
            chunk_has_shops = self.db_manager.query_one(
                "SELECT COUNT(*) as count FROM chunk_index WHERE chunk_x = ? AND chunk_z = ? AND dimension = ? AND shop_count > 0",
                (chunk_x, chunk_z, dimension)
            )
            
            # 3. 如果区块没有商店，直接返回None
            if not chunk_has_shops or chunk_has_shops['count'] == 0:
                return None
            
            # 4. 如果区块有商店，再精确查询该位置的商店
            return self.db_manager.query_one(
                "SELECT * FROM button_shops WHERE x = ? AND y = ? AND z = ? AND dimension = ? AND is_active = 1",
                (x, y, z, dimension)
            )
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Get shop at position optimized error: {str(e)}")
            return None

    def _get_shop_by_id(self, shop_id: int):
        """根据ID获取商店"""
        try:
            return self.db_manager.query_one(
                "SELECT * FROM button_shops WHERE id = ?",
                (shop_id,)
            )
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Get shop by id error: {str(e)}")
            return None

    def _get_chunk_coords(self, x: int, z: int) -> tuple:
        """获取区块坐标"""
        return x // self.CHUNK_SIZE, z // self.CHUNK_SIZE

    def _update_chunk_index(self, chunk_x: int, chunk_z: int, dimension: str, delta: int):
        """更新区块索引"""
        try:
            # 先尝试获取现有记录
            existing = self.db_manager.query_one(
                "SELECT shop_count FROM chunk_index WHERE chunk_x = ? AND chunk_z = ? AND dimension = ?",
                (chunk_x, chunk_z, dimension)
            )
            
            if existing:
                # 更新现有记录
                new_count = max(0, existing['shop_count'] + delta)
                self.db_manager.update(
                    table='chunk_index',
                    data={'shop_count': new_count},
                    where='chunk_x = ? AND chunk_z = ? AND dimension = ?',
                    params=(chunk_x, chunk_z, dimension)
                )
            else:
                # 创建新记录
                self.db_manager.insert("chunk_index", {
                    'chunk_x': chunk_x,
                    'chunk_z': chunk_z,
                    'dimension': dimension,
                    'shop_count': max(0, delta)
                })
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Update chunk index error: {str(e)}")

    def _generate_shop_uuid(self) -> str:
        """生成商店UUID"""
        import uuid
        return str(uuid.uuid4())

    def _calculate_tax(self, amount: int) -> int:
        """计算交易税（整数）"""
        try:
            tax_enabled = self.setting_manager.GetSetting("trade_tax_enabled")
            if tax_enabled and tax_enabled.lower() == "true":
                tax_rate = float(self.setting_manager.GetSetting("trade_tax_rate") or "0.05")
                return int(amount * tax_rate)
            return 0
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Calculate tax error: {str(e)}")
            return 0

    def _get_tax_rate(self) -> float:
        """获取税率"""
        try:
            return float(self.setting_manager.GetSetting("trade_tax_rate") or "0.05")
        except Exception:
            return 0.05

    def _get_player_inventory_items(self, player):
        """获取玩家背包物品"""
        try:
            items = []
            # 使用EndStone inventory API遍历玩家背包
            inventory = player.inventory
            
            for slot_index in range(inventory.size):
                item_stack = inventory.get_item(slot_index)
                
                if item_stack and item_stack.type and item_stack.amount > 0:
                    # 获取物品类型ID和显示名称
                    item_type_id = item_stack.type.id
                    item_type_translation_key = item_stack.type.translation_key
                    
                    # 尝试获取本地化的物品名称
                    try:
                        display_name = self.server.language.translate(
                            item_type_translation_key,
                            None,
                            player.locale
                        )
                    except:
                        # 如果翻译失败，使用类型ID作为备选
                        display_name = item_type_id
                    
                    # 如果有自定义显示名称，优先使用
                    if item_stack.item_meta and item_stack.item_meta.has_display_name:
                        display_name = item_stack.item_meta.display_name
                    
                    # 获取附魔信息
                    enchants = {}
                    if item_stack.item_meta and item_stack.item_meta.enchants:
                        try:
                            # 附魔信息直接是字典格式 {enchant_key: level}
                            if isinstance(item_stack.item_meta.enchants, dict):
                                enchants = item_stack.item_meta.enchants.copy()
                            else:
                                # 如果是列表格式，转换为字典
                                for enchant in item_stack.item_meta.enchants:
                                    try:
                                        if hasattr(enchant, 'type') and hasattr(enchant.type, 'id'):
                                            enchant_id = enchant.type.id
                                        else:
                                            enchant_id = str(enchant.type)
                                        
                                        if hasattr(enchant, 'level'):
                                            enchant_level = enchant.level
                                        else:
                                            enchant_level = 1  # 默认等级
                                        
                                        enchants[enchant_id] = enchant_level
                                    except Exception as enchant_error:
                                        self._safe_log('warning', f"[ARCButtonShop] Failed to get enchant info: {str(enchant_error)}")
                                        continue
                        except Exception as e:
                            self._safe_log('warning', f"[ARCButtonShop] Failed to process enchants: {str(e)}")
                            enchants = {}
                    
                    # 获取Lore信息
                    lore = []
                    if item_stack.item_meta and item_stack.item_meta.has_lore:
                        try:
                            lore = item_stack.item_meta.lore
                            if not isinstance(lore, list):
                                lore = []
                        except Exception as lore_error:
                            self._safe_log('warning', f"[ARCButtonShop] Failed to get lore info: {str(lore_error)}")
                            lore = []
                    
                    items.append({
                        'type': item_type_id,  # 使用类型ID而不是ItemType对象
                        'type_translation_key': item_type_translation_key,  # 保存翻译键
                        'name': display_name,
                        'count': item_stack.amount,
                        'data': item_stack.data,
                        'enchants': enchants,  # 保存附魔信息
                        'lore': lore,  # 保存Lore信息
                        'slot_index': slot_index  # 记录槽位索引，用于后续操作
                    })
            
            return items
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Get player inventory error: {str(e)}")
            return []

    def _player_has_item(self, player, item_info) -> bool:
        """检查玩家是否拥有指定物品"""
        try:
            inventory = player.inventory
            required_type = item_info['type']  # 现在是字符串ID
            required_count = item_info['count']
            required_data = item_info.get('data', 0)
            required_enchants = item_info.get('enchants', {})
            required_lore = item_info.get('lore', [])
            
            total_count = 0
            debug_info = []  # 用于调试的背包信息
            
            # 遍历背包检查物品
            for slot_index in range(inventory.size):
                item_stack = inventory.get_item(slot_index)
                
                if not item_stack or not item_stack.type:
                    continue
                
                # 记录调试信息
                debug_item = {
                    'slot': slot_index,
                    'type': item_stack.type.id,
                    'data': item_stack.data,
                    'amount': item_stack.amount,
                    'enchants': {},
                    'lore': []
                }
                
                # 获取附魔信息用于调试
                if item_stack.item_meta and item_stack.item_meta.enchants:
                    try:
                        if isinstance(item_stack.item_meta.enchants, dict):
                            debug_item['enchants'] = item_stack.item_meta.enchants.copy()
                        else:
                            for enchant in item_stack.item_meta.enchants:
                                try:
                                    if hasattr(enchant, 'type') and hasattr(enchant.type, 'id'):
                                        enchant_id = enchant.type.id
                                    else:
                                        enchant_id = str(enchant.type)
                                    
                                    if hasattr(enchant, 'level'):
                                        enchant_level = enchant.level
                                    else:
                                        enchant_level = 1
                                    
                                    debug_item['enchants'][enchant_id] = enchant_level
                                except:
                                    continue
                    except:
                        pass
                
                # 获取Lore信息用于调试
                if item_stack.item_meta and item_stack.item_meta.has_lore:
                    try:
                        debug_item['lore'] = item_stack.item_meta.lore
                        if not isinstance(debug_item['lore'], list):
                            debug_item['lore'] = []
                    except:
                        pass
                
                debug_info.append(debug_item)
                
                # 检查基本类型和数据
                if (item_stack.type.id == required_type and 
                    item_stack.data == required_data):
                    
                    # 检查附魔信息
                    item_enchants = {}
                    if item_stack.item_meta and item_stack.item_meta.enchants:
                        try:
                            if isinstance(item_stack.item_meta.enchants, dict):
                                item_enchants = item_stack.item_meta.enchants.copy()
                            else:
                                for enchant in item_stack.item_meta.enchants:
                                    try:
                                        if hasattr(enchant, 'type') and hasattr(enchant.type, 'id'):
                                            enchant_id = enchant.type.id
                                        else:
                                            enchant_id = str(enchant.type)
                                        
                                        if hasattr(enchant, 'level'):
                                            enchant_level = enchant.level
                                        else:
                                            enchant_level = 1
                                        
                                        item_enchants[enchant_id] = enchant_level
                                    except:
                                        continue
                        except:
                            item_enchants = {}
                    
                    # 检查Lore信息
                    item_lore = []
                    if item_stack.item_meta and item_stack.item_meta.has_lore:
                        try:
                            item_lore = item_stack.item_meta.lore
                            if not isinstance(item_lore, list):
                                item_lore = []
                        except:
                            item_lore = []
                    
                    # 比较附魔和Lore
                    enchants_match = True
                    if required_enchants:
                        if not item_enchants:
                            enchants_match = False
                        else:
                            for enchant_id, level in required_enchants.items():
                                if enchant_id not in item_enchants or item_enchants[enchant_id] != level:
                                    enchants_match = False
                                    break
                    
                    lore_match = True
                    if required_lore:
                        if not item_lore:
                            lore_match = False
                        else:
                            if len(required_lore) != len(item_lore):
                                lore_match = False
                            else:
                                for i, lore_line in enumerate(required_lore):
                                    if i >= len(item_lore) or item_lore[i] != lore_line:
                                        lore_match = False
                                        break
                    
                    # 如果所有条件都匹配，计算数量
                    if enchants_match and lore_match:
                        total_count += item_stack.amount
                        
                        if total_count >= required_count:
                            return True
            
            # 如果没有找到匹配的物品，打印调试信息
            if total_count < required_count:
                print(f"[DEBUG] 玩家 {player.name} 背包内容:")
                print(f"[DEBUG] 需要物品: {required_type}, 数据: {required_data}, 数量: {required_count}")
                print(f"[DEBUG] 需要附魔: {required_enchants}")
                print(f"[DEBUG] 需要Lore: {required_lore}")
                print(f"[DEBUG] 背包物品:")
                for item in debug_info:
                    print(f"[DEBUG]   槽位{item['slot']}: {item['type']} x{item['amount']} (数据:{item['data']})")
                    if item['enchants']:
                        print(f"[DEBUG]     附魔: {item['enchants']}")
                    if item['lore']:
                        print(f"[DEBUG]     Lore: {item['lore']}")
                print(f"[DEBUG] 找到匹配物品数量: {total_count}")
            
            return False
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Player has item check error: {str(e)}")
            return False

    def _remove_item_from_player(self, player, item_info) -> bool:
        """从玩家背包移除物品"""
        try:
            inventory = player.inventory
            required_type = item_info['type']  # 现在是字符串ID
            required_count = item_info['count']
            required_data = item_info.get('data', 0)
            required_enchants = item_info.get('enchants', {})
            required_lore = item_info.get('lore', [])
            
            remaining_to_remove = required_count
            slots_to_modify = []
            
            # 首先检查是否有足够的物品
            if not self._player_has_item(player, item_info):
                return False
            
            # 收集需要修改的槽位信息
            for slot_index in range(inventory.size):
                if remaining_to_remove <= 0:
                    break
                    
                item_stack = inventory.get_item(slot_index)
                
                if not item_stack or not item_stack.type:
                    continue
                
                # 检查基本类型和数据
                if (item_stack.type.id == required_type and 
                    item_stack.data == required_data):
                    
                    # 检查附魔信息
                    item_enchants = {}
                    if item_stack.item_meta and item_stack.item_meta.enchants:
                        try:
                            if isinstance(item_stack.item_meta.enchants, dict):
                                item_enchants = item_stack.item_meta.enchants.copy()
                            else:
                                for enchant in item_stack.item_meta.enchants:
                                    try:
                                        if hasattr(enchant, 'type') and hasattr(enchant.type, 'id'):
                                            enchant_id = enchant.type.id
                                        else:
                                            enchant_id = str(enchant.type)
                                        
                                        if hasattr(enchant, 'level'):
                                            enchant_level = enchant.level
                                        else:
                                            enchant_level = 1
                                        
                                        item_enchants[enchant_id] = enchant_level
                                    except:
                                        continue
                        except:
                            item_enchants = {}
                    
                    # 检查Lore信息
                    item_lore = []
                    if item_stack.item_meta and item_stack.item_meta.has_lore:
                        try:
                            item_lore = item_stack.item_meta.lore
                            if not isinstance(item_lore, list):
                                item_lore = []
                        except:
                            item_lore = []
                    
                    # 比较附魔和Lore
                    enchants_match = True
                    if required_enchants:
                        if not item_enchants:
                            enchants_match = False
                        else:
                            for enchant_id, level in required_enchants.items():
                                if enchant_id not in item_enchants or item_enchants[enchant_id] != level:
                                    enchants_match = False
                                    break
                    
                    lore_match = True
                    if required_lore:
                        if not item_lore:
                            lore_match = False
                        else:
                            if len(required_lore) != len(item_lore):
                                lore_match = False
                            else:
                                for i, lore_line in enumerate(required_lore):
                                    if i >= len(item_lore) or item_lore[i] != lore_line:
                                        lore_match = False
                                        break
                    
                    # 如果所有条件都匹配，收集槽位信息
                    if enchants_match and lore_match:
                        remove_from_slot = min(remaining_to_remove, item_stack.amount)
                        slots_to_modify.append((slot_index, item_stack, remove_from_slot))
                        remaining_to_remove -= remove_from_slot
            
            # 执行移除操作
            for slot_index, original_stack, remove_count in slots_to_modify:
                new_amount = original_stack.amount - remove_count
                
                if new_amount <= 0:
                    # 清空槽位
                    inventory.set_item(slot_index, None)
                else:
                    # 更新数量
                    original_stack.amount = new_amount
                    inventory.set_item(slot_index, original_stack)
            
            return True
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Remove item from player error: {str(e)}")
            return False

    def _give_item_to_player(self, player, item_info) -> bool:
        """给玩家物品"""
        try:
            from endstone.inventory import ItemStack
            
            inventory = player.inventory
            item_type_id = item_info['type']  # 现在是字符串ID
            total_amount = item_info['count']
            item_data = item_info.get('data', 0)
            
            # 验证数量
            if total_amount <= 0:
                self._safe_log('warning', f"[ARCButtonShop] Invalid item amount: {total_amount}")
                return False
            
            remaining_to_give = total_amount
            
            # 创建物品堆栈并添加到背包
            while remaining_to_give > 0:
                # 计算本次要给予的数量（不超过64）
                current_amount = min(remaining_to_give, 64)
                
                # 确保数量在有效范围内
                if current_amount <= 0:
                    break
                
                # 创建新的ItemStack
                item_stack = ItemStack(
                    type=item_type_id,  # 使用字符串ID
                    amount=current_amount,  # 确保数量在1-255范围内
                    data=item_data
                )
                
                # 应用附魔信息
                if 'enchants' in item_info and item_info['enchants']:
                    for enchant_id, level in item_info['enchants'].items():
                        try:
                            # 这里需要根据EndStone的API来添加附魔
                            # 具体实现可能需要根据EndStone的附魔API调整
                            pass
                        except Exception as e:
                            self._safe_log('warning', f"[ARCButtonShop] Failed to apply enchant {enchant_id}: {str(e)}")
                
                # 应用Lore信息
                if 'lore' in item_info and item_info['lore']:
                    try:
                        # 这里需要根据EndStone的API来设置Lore
                        # 具体实现可能需要根据EndStone的Lore API调整
                        pass
                    except Exception as e:
                        self._safe_log('warning', f"[ARCButtonShop] Failed to apply lore: {str(e)}")
                
                # 尝试添加到背包
                remaining_items = inventory.add_item(item_stack)
                
                if remaining_items:
                    # 如果有剩余物品，说明背包满了
                    try:
                        # 安全地获取剩余物品数量
                        if hasattr(remaining_items, 'get'):
                            first_remaining = remaining_items.get(0)
                        elif isinstance(remaining_items, list) and len(remaining_items) > 0:
                            first_remaining = remaining_items[0]
                        else:
                            first_remaining = None
                        
                        if first_remaining and hasattr(first_remaining, 'amount'):
                            remaining_amount = first_remaining.amount
                        else:
                            remaining_amount = 0
                        
                        added_amount = item_stack.amount - remaining_amount
                        remaining_to_give -= added_amount
                        
                        if added_amount == 0:
                            # 背包完全满了，无法添加任何物品
                            self._safe_log('warning', f"[ARCButtonShop] Player {player.name} inventory is full, could not give {remaining_to_give} items")
                            return False
                    except Exception as e:
                        self._safe_log('warning', f"[ARCButtonShop] Error calculating remaining items: {str(e)}")
                        remaining_to_give -= item_stack.amount
                else:
                    # 成功添加所有物品
                    remaining_to_give -= item_stack.amount
            
            return True
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Give item to player error: {str(e)}")
            return False

    def _handle_shop_manage_command(self, sender: CommandSender, args: list[str]) -> bool:
        """处理商店管理命令"""
        if not sender.is_op:
            sender.send_message(self.language_manager.GetText("NO_PERMISSION"))
            return True
        
        if not args:
            sender.send_message("用法: /shopmanage <list|clear|reload>")
            return True
        
        command = args[0].lower()
        
        if command == "list":
            # 列出所有商店
            shops = self.db_manager.query_all("SELECT * FROM button_shops WHERE is_active = 1")
            sender.send_message(f"当前活跃商店数量: {len(shops)}")
            
        elif command == "clear":
            # 清除所有商店（危险操作）
            self.db_manager.execute("DELETE FROM button_shops")
            self.db_manager.execute("DELETE FROM shop_transactions") 
            self.db_manager.execute("DELETE FROM chunk_index")
            sender.send_message("所有商店数据已清除")
            
        elif command == "reload":
            # 重新加载配置
            sender.send_message("商店系统已重新加载")
            
        return True

    def _show_my_shops_panel(self, player):
        """显示我的商店面板"""
        try:
            my_shops = self.db_manager.query_all(
                "SELECT * FROM button_shops WHERE owner_xuid = ? AND is_active = 1 ORDER BY create_time DESC",
                (str(player.unique_id),)
            )
            
            if not my_shops:
                no_shops_panel = ActionForm(
                    title="我的商店",
                    content="你还没有创建任何商店",
                    on_close=lambda sender: self._show_shop_main_panel(sender)
                )
                player.send_form(no_shops_panel)
                return
            
            # 显示商店列表
            my_shops_panel = ActionForm(
                title="我的商店",
                content=f"你有 {len(my_shops)} 个商店"
            )
            
            for shop in my_shops:
                item_data = json.loads(shop['item_data'])
                button_text = f"{item_data['name']} - 库存:{shop['stock']} - 单价:{shop['unit_price']}"
                
                # 添加附魔和Lore标识
                if item_data.get('enchants'):
                    button_text += " §b[附魔]"
                if item_data.get('lore'):
                    button_text += " §d[Lore]"
                
                my_shops_panel.add_button(
                    button_text,
                    on_click=lambda sender, s=shop: self._show_shop_manage_panel(sender, s)
                )
            
            my_shops_panel.add_button(
                "返回",
                on_click=lambda sender: self._show_shop_main_panel(sender)
            )
            
            player.send_form(my_shops_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show my shops error: {str(e)}")
            player.send_message("显示商店列表时出现错误")

    def _show_nearby_shops_panel(self, player):
        """显示附近商店面板"""
        try:
            player_loc = player.location
            chunk_x, chunk_z = self._get_chunk_coords(int(player_loc.x), int(player_loc.z))
            
            # 搜索附近9个区块的商店
            nearby_shops = []
            for dx in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    search_chunk_x = chunk_x + dx
                    search_chunk_z = chunk_z + dz
                    
                    chunk_shops = self.db_manager.query_all(
                        "SELECT * FROM button_shops WHERE chunk_x = ? AND chunk_z = ? AND dimension = ? AND is_active = 1",
                        (search_chunk_x, search_chunk_z, player_loc.dimension.name)
                    )
                    nearby_shops.extend(chunk_shops)
            
            if not nearby_shops:
                no_shops_panel = ActionForm(
                    title="附近商店",
                    content="附近没有商店",
                    on_close=lambda sender: self._show_shop_main_panel(sender)
                )
                player.send_form(no_shops_panel)
                return
            
            # 显示附近商店
            nearby_panel = ActionForm(
                title="附近商店",
                content=f"找到 {len(nearby_shops)} 个附近的商店"
            )
            
            for shop in nearby_shops[:20]:  # 最多显示20个
                item_data = json.loads(shop['item_data'])
                distance = math.sqrt(
                    (shop['x'] - player_loc.x) ** 2 + 
                    (shop['z'] - player_loc.z) ** 2
                )
                button_text = f"{item_data['name']} - {shop['owner_name']} - {distance:.1f}方块"
                
                # 添加附魔和Lore标识
                if item_data.get('enchants'):
                    button_text += " §b[附魔]"
                if item_data.get('lore'):
                    button_text += " §d[Lore]"
                
                nearby_panel.add_button(
                    button_text,
                    on_click=lambda sender, s=shop: self._show_shop_detail_panel(sender, s)
                )
            
            nearby_panel.add_button(
                "返回",
                on_click=lambda sender: self._show_shop_main_panel(sender)
            )
            
            player.send_form(nearby_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show nearby shops error: {str(e)}")
            player.send_message("显示附近商店时出现错误")

    def _show_shop_manage_panel(self, player, shop_data):
        """显示商店管理面板"""
        try:
            item_data = json.loads(shop_data['item_data'])
            shop_type = shop_data.get('shop_type', 'sell')
            
            manage_info = f"""
商店信息:
物品: {item_data['name']}
库存: {shop_data['stock']}
单价: {shop_data['unit_price']}
位置: ({shop_data['x']}, {shop_data['y']}, {shop_data['z']})
创建时间: {shop_data['create_time']}"""
            
            # 添加附魔信息
            if item_data.get('enchants'):
                manage_info += "\n\n附魔:"
                for enchant_id, level in item_data['enchants'].items():
                    manage_info += f"\n  {enchant_id} [等级 {level}]"
            
            # 添加Lore信息
            if item_data.get('lore'):
                manage_info += "\n\nLore:"
                for lore_line in item_data['lore']:
                    manage_info += f"\n  {lore_line}"
            
            # 收购商店显示收集的物品信息
            if shop_type == "buy":
                collected_items = []
                if shop_data.get('collected_items'):
                    try:
                        collected_items = json.loads(shop_data['collected_items'])
                    except:
                        collected_items = []
                
                total_collected = sum(item['count'] for item in collected_items)
                manage_info += f"\n\n收集的物品: {total_collected} 个"
            
            manage_panel = ActionForm(
                title="管理商店",
                content=manage_info
            )
            
            # 根据商店类型显示不同的按钮
            if shop_type == "sell":
                # 出售商店 - 补充库存按钮
                if shop_data['stock'] < shop_data['quantity']:
                    manage_panel.add_button(
                        "补充库存",
                        on_click=lambda sender: self._show_restock_panel(sender, shop_data)
                    )
            else:
                # 收购商店 - 收取物品按钮
                collected_items = []
                if shop_data.get('collected_items'):
                    try:
                        collected_items = json.loads(shop_data['collected_items'])
                    except:
                        collected_items = []
                
                if collected_items:
                    manage_panel.add_button(
                        "收取物品",
                        on_click=lambda sender: self._show_collect_items_panel(sender, shop_data)
                    )
            
            # 删除商店按钮
            manage_panel.add_button(
                "删除商店",
                on_click=lambda sender: self._show_delete_shop_panel(sender, shop_data)
            )
            
            manage_panel.add_button(
                "返回",
                on_click=lambda sender: self._show_my_shops_panel(sender)
            )
            
            player.send_form(manage_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show shop manage panel error: {str(e)}")
            player.send_message("显示商店管理面板时出现错误")

    def _show_restock_panel(self, player, shop_data):
        """显示补充库存面板"""
        try:
            item_data = json.loads(shop_data['item_data'])
            
            restock_info = f"为 {item_data['name']} 补充库存\n当前库存: {shop_data['stock']}"
            
            # 添加附魔信息
            if item_data.get('enchants'):
                restock_info += "\n\n附魔:"
                for enchant_id, level in item_data['enchants'].items():
                    restock_info += f"\n  {enchant_id} [等级 {level}]"
            
            # 添加Lore信息
            if item_data.get('lore'):
                restock_info += "\n\nLore:"
                for lore_line in item_data['lore']:
                    restock_info += f"\n  {lore_line}"
            
            restock_label = Label(text=restock_info)
            
            quantity_input = TextInput(
                label="补充数量",
                placeholder="输入要补充的数量",
                default_value=""
            )
            
            def process_restock(sender, json_str: str):
                try:
                    data = json.loads(json_str)
                    quantity_str = data[1]
                    
                    try:
                        quantity = int(quantity_str)
                        if quantity <= 0:
                            raise ValueError("Quantity must be positive")
                    except ValueError:
                        error_form = ActionForm(
                            title="补充库存",
                            content="请输入有效的数量",
                            on_close=lambda s: self._show_restock_panel(s, shop_data)
                        )
                        sender.send_form(error_form)
                        return
                    
                    # 检查玩家是否有足够的物品
                    required_item = {
                        'type': item_data['type'],
                        'name': item_data['name'],
                        'count': quantity,
                        'data': item_data.get('data', 0)
                    }
                    
                    if self._player_has_item(sender, required_item) and self._remove_item_from_player(sender, required_item):
                        # 更新库存
                        new_stock = shop_data['stock'] + quantity
                        self.db_manager.update(
                            table='button_shops',
                            data={'stock': new_stock, 'is_active': 1},
                            where='id = ?',
                            params=(shop_data['id'],)
                        )
                        
                        success_form = ActionForm(
                            title="补充库存",
                            content=f"成功补充 {quantity} 个 {item_data['name']}",
                            on_close=lambda s: self._show_my_shops_panel(s)
                        )
                        sender.send_form(success_form)
                    else:
                        error_form = ActionForm(
                            title="补充库存",
                            content="背包中没有足够的物品",
                            on_close=lambda s: self._show_restock_panel(s, shop_data)
                        )
                        sender.send_form(error_form)
                
                except Exception as e:
                    self._safe_log('error', f"[ARCButtonShop] Process restock error: {str(e)}")
                    error_form = ActionForm(
                        title="补充库存",
                        content="补充库存时出现错误",
                        on_close=lambda s: self._show_my_shops_panel(s)
                    )
                    sender.send_form(error_form)
            
            restock_panel = ModalForm(
                title="补充库存",
                controls=[restock_label, quantity_input],
                on_close=lambda sender: self._show_shop_manage_panel(sender, shop_data),
                on_submit=process_restock
            )
            
            player.send_form(restock_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show restock panel error: {str(e)}")
            player.send_message("显示补充库存面板时出现错误")

    def _show_delete_shop_panel(self, player, shop_data):
        """显示删除商店确认面板"""
        try:
            item_data = json.loads(shop_data['item_data'])
            
            confirm_content = f"""
确定要删除这个商店吗？

物品: {item_data['name']}
剩余库存: {shop_data['stock']}"""
            
            # 添加附魔信息
            if item_data.get('enchants'):
                confirm_content += "\n\n附魔:"
                for enchant_id, level in item_data['enchants'].items():
                    confirm_content += f"\n  {enchant_id} [等级 {level}]"
            
            # 添加Lore信息
            if item_data.get('lore'):
                confirm_content += "\n\nLore:"
                for lore_line in item_data['lore']:
                    confirm_content += f"\n  {lore_line}"
            
            confirm_content += "\n\n删除后剩余库存将返还到你的背包中。"
            
            confirm_panel = ActionForm(
                title="删除商店",
                content=confirm_content
            )
            
            confirm_panel.add_button(
                "确定删除",
                on_click=lambda sender: self._execute_delete_shop(sender, shop_data)
            )
            
            confirm_panel.add_button(
                "取消",
                on_click=lambda sender: self._show_shop_manage_panel(sender, shop_data)
            )
            
            player.send_form(confirm_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show delete shop panel error: {str(e)}")
            player.send_message("显示删除确认面板时出现错误")

    def _handle_shop_removal_by_owner(self, player, shop_data):
        """处理店主破坏商店按钮（删除商店）"""
        try:
            item_data = json.loads(shop_data['item_data'])
            shop_type = shop_data.get('shop_type', 'sell')
            
            # 根据商店类型处理剩余物品/资金
            if shop_type == "sell":
                # 出售商店 - 返还剩余库存
                if shop_data['stock'] > 0:
                    return_item = {
                        'type': item_data['type'],
                        'name': item_data['name'],
                        'count': shop_data['stock'],
                        'data': item_data.get('data', 0)
                    }
                    self._give_item_to_player(player, return_item)
                    player.send_message(self.language_manager.GetText("SHOP_REMOVED_BY_OWNER_SELL").format(
                        shop_data['stock'], item_data['name']
                    ))
            else:
                # 收购商店 - 返还剩余预算和收集的物品
                if shop_data['stock'] > 0:
                    self._change_player_money(player.name, shop_data['stock'])
                    player.send_message(self.language_manager.GetText("SHOP_REMOVED_BY_OWNER_BUY").format(
                            shop_data['stock']
                        ))
                
                # 返还收集的物品
                collected_items = []
                if shop_data.get('collected_items'):
                    try:
                        collected_items = json.loads(shop_data['collected_items'])
                    except:
                        collected_items = []
                
                if collected_items:
                    total_items = sum(item['count'] for item in collected_items)
                    for item in collected_items:
                        self._give_item_to_player(player, item)
                    player.send_message(f"商店已删除，{len(collected_items)} 批收集的物品（共 {total_items} 个）已返还到背包")
            
            # 删除商店记录
            self.db_manager.delete(
                table='button_shops',
                where='id = ?',
                params=(shop_data['id'],)
            )
            
            # 更新区块索引
            self._update_chunk_index(shop_data['chunk_x'], shop_data['chunk_z'], shop_data['dimension'], -1)
            
            self._safe_log('info', f"[ARCButtonShop] Shop removed by owner {player.name} at ({shop_data['x']}, {shop_data['y']}, {shop_data['z']})")
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Handle shop removal by owner error: {str(e)}")
            player.send_message(self.language_manager.GetText("SHOP_REMOVAL_ERROR"))

    def _show_collect_items_panel(self, player, shop_data):
        """显示收取物品面板"""
        try:
            collected_items = []
            if shop_data.get('collected_items'):
                try:
                    collected_items = json.loads(shop_data['collected_items'])
                except:
                    collected_items = []
            
            if not collected_items:
                no_items_panel = ActionForm(
                    title="收取物品",
                    content="没有收集到任何物品",
                    on_close=lambda sender: self._show_shop_manage_panel(sender, shop_data)
                )
                player.send_form(no_items_panel)
                return
            
            # 显示收集的物品列表
            collect_panel = ActionForm(
                title="收取物品",
                content=f"收集到 {len(collected_items)} 批物品"
            )
            
            for i, item in enumerate(collected_items):
                button_text = f"{item['name']} x{item['count']} - {item['collect_time']}"
                
                # 添加附魔和Lore标识
                if item.get('enchants'):
                    button_text += " §b[附魔]"
                if item.get('lore'):
                    button_text += " §d[Lore]"
                
                collect_panel.add_button(
                    button_text,
                    on_click=lambda sender, item_data=item, item_index=i: self._collect_single_item(sender, shop_data, item_data, item_index)
                )
            
            # 一键收取所有物品
            collect_panel.add_button(
                "一键收取所有",
                on_click=lambda sender: self._collect_all_items(sender, shop_data)
            )
            
            collect_panel.add_button(
                "返回",
                on_click=lambda sender: self._show_shop_manage_panel(sender, shop_data)
            )
            
            player.send_form(collect_panel)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Show collect items panel error: {str(e)}")
            player.send_message("显示收取物品面板时出现错误")

    def _collect_single_item(self, player, shop_data, item_data, item_index):
        """收取单个物品"""
        try:
            # 尝试给玩家物品
            if self._give_item_to_player(player, item_data):
                # 从商店中移除该物品
                collected_items = []
                if shop_data.get('collected_items'):
                    try:
                        collected_items = json.loads(shop_data['collected_items'])
                    except:
                        collected_items = []
                
                if item_index < len(collected_items):
                    collected_items.pop(item_index)
                
                # 更新商店数据
                self.db_manager.update(
                    table='button_shops',
                    data={'collected_items': json.dumps(collected_items)},
                    where='id = ?',
                    params=(shop_data['id'],)
                )
                
                success_form = ActionForm(
                    title="收取物品",
                    content=f"成功收取 {item_data['count']} 个 {item_data['name']}",
                    on_close=lambda sender: self._show_collect_items_panel(sender, shop_data)
                )
                player.send_form(success_form)
            else:
                error_form = ActionForm(
                    title="收取物品",
                    content="背包空间不足，无法收取物品",
                    on_close=lambda sender: self._show_collect_items_panel(sender, shop_data)
                )
                player.send_form(error_form)
                
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Collect single item error: {str(e)}")
            error_form = ActionForm(
                title="收取物品",
                content="收取物品时出现错误",
                on_close=lambda sender: self._show_collect_items_panel(sender, shop_data)
            )
            player.send_form(error_form)

    def _collect_all_items(self, player, shop_data):
        """一键收取所有物品"""
        try:
            collected_items = []
            if shop_data.get('collected_items'):
                try:
                    collected_items = json.loads(shop_data['collected_items'])
                except:
                    collected_items = []
            
            if not collected_items:
                no_items_panel = ActionForm(
                    title="收取物品",
                    content="没有收集到任何物品",
                    on_close=lambda sender: self._show_shop_manage_panel(sender, shop_data)
                )
                player.send_form(no_items_panel)
                return
            
            # 尝试收取所有物品
            success_count = 0
            failed_items = []
            
            for item in collected_items:
                if self._give_item_to_player(player, item):
                    success_count += 1
                else:
                    failed_items.append(item)
            
            # 更新商店数据（移除成功收取的物品）
            if success_count > 0:
                self.db_manager.update(
                    table='button_shops',
                    data={'collected_items': json.dumps(failed_items)},
                    where='id = ?',
                    params=(shop_data['id'],)
                )
            
            # 显示结果
            if success_count == len(collected_items):
                result_content = f"成功收取所有 {success_count} 批物品"
            elif success_count > 0:
                result_content = f"成功收取 {success_count} 批物品，{len(failed_items)} 批因背包空间不足而保留"
            else:
                result_content = "背包空间不足，无法收取任何物品"
            
            result_form = ActionForm(
                title="收取物品",
                content=result_content,
                on_close=lambda sender: self._show_shop_manage_panel(sender, shop_data)
            )
            player.send_form(result_form)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Collect all items error: {str(e)}")
            error_form = ActionForm(
                title="收取物品",
                content="收取物品时出现错误",
                on_close=lambda sender: self._show_shop_manage_panel(sender, shop_data)
            )
            player.send_form(error_form)

    def _execute_delete_shop(self, player, shop_data):
        """执行删除商店操作"""
        try:
            item_data = json.loads(shop_data['item_data'])
            shop_type = shop_data.get('shop_type', 'sell')
            
            # 根据商店类型处理剩余物品/资金
            if shop_type == "sell":
                # 出售商店 - 返还剩余库存
                if shop_data['stock'] > 0:
                    return_item = {
                        'type': item_data['type'],
                        'name': item_data['name'],
                        'count': shop_data['stock'],
                        'data': item_data.get('data', 0)
                    }
                    self._give_item_to_player(player, return_item)
            else:
                # 收购商店 - 返还剩余预算和收集的物品
                if shop_data['stock'] > 0:
                    self._change_player_money(player.name, shop_data['stock'])
                
                # 返还收集的物品
                collected_items = []
                if shop_data.get('collected_items'):
                    try:
                        collected_items = json.loads(shop_data['collected_items'])
                    except:
                        collected_items = []
                
                for item in collected_items:
                    self._give_item_to_player(player, item)
            
            # 删除商店记录
            self.db_manager.delete(
                table='button_shops',
                where='id = ?',
                params=(shop_data['id'],)
            )
            
            # 更新区块索引
            self._update_chunk_index(shop_data['chunk_x'], shop_data['chunk_z'], shop_data['dimension'], -1)
            
            # 显示结果消息
            if shop_type == "sell":
                result_content = f"商店已成功删除，{shop_data['stock']} 个 {item_data['name']} 已返还到背包"
            else:
                result_content = f"商店已成功删除，剩余预算 {shop_data['stock']} 已返还，收集的物品已返还到背包"
            
            result_form = ActionForm(
                title="删除商店",
                content=result_content,
                on_close=lambda sender: self._show_my_shops_panel(sender)
            )
            player.send_form(result_form)
            
            self._safe_log('info', f"[ARCButtonShop] Shop deleted by {player.name} at ({shop_data['x']}, {shop_data['y']}, {shop_data['z']})")
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Execute delete shop error: {str(e)}")
            error_form = ActionForm(
                title="删除商店",
                content="删除商店时出现错误",
                on_close=lambda sender: self._show_my_shops_panel(sender)
            )
            player.send_form(error_form)

    # API 接口方法
    def api_get_shop_at_position(self, x: int, y: int, z: int, dimension: str) -> dict:
        """获取指定位置的商店信息（API接口）"""
        return self._get_shop_at_position(x, y, z, dimension)
    
    def api_get_player_shops(self, player_xuid: str) -> list:
        """获取玩家的所有商店（API接口）"""
        try:
            return self.db_manager.query_all(
                "SELECT * FROM button_shops WHERE owner_xuid = ? AND is_active = 1 ORDER BY create_time DESC",
                (player_xuid,)
            )
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Get player shops error: {str(e)}")
            return []
    
    def api_get_nearby_shops(self, x: int, z: int, dimension: str, radius: int = 1) -> list:
        """获取指定位置附近的商店（基于区块，用于浏览功能）"""
        try:
            chunk_x, chunk_z = self._get_chunk_coords(x, z)
            nearby_shops = []
            
            # 搜索指定半径内的区块
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    search_chunk_x = chunk_x + dx
                    search_chunk_z = chunk_z + dz
                    
                    chunk_shops = self.db_manager.query_all(
                        "SELECT * FROM button_shops WHERE chunk_x = ? AND chunk_z = ? AND dimension = ? AND is_active = 1",
                        (search_chunk_x, search_chunk_z, dimension)
                    )
                    nearby_shops.extend(chunk_shops)
            
            return nearby_shops
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Get nearby shops error: {str(e)}")
            return []
    
    def api_get_all_active_shops(self) -> list:
        """获取所有活跃的商店"""
        try:
            return self.db_manager.query_all(
                "SELECT * FROM button_shops WHERE is_active = 1 ORDER BY create_time DESC"
            )
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] Get all active shops error: {str(e)}")
            return []
    
    def api_purchase_from_shop(self, shop_id: int, buyer_xuid: str, quantity: int) -> tuple[bool, str]:
        """从商店购买商品（API接口）"""
        try:
            # 获取商店信息
            shop_data = self._get_shop_by_id(shop_id)
            if not shop_data:
                return False, "商店不存在"
            
            # 通过xuid查找买家
            buyer_player = None
            for player in self.server.online_players:
                if str(player.unique_id) == buyer_xuid:
                    buyer_player = player
                    break
            
            if not buyer_player:
                return False, "买家不在线"
            
            # 执行购买
            return self._execute_purchase(buyer_player, shop_data, quantity)
            
        except Exception as e:
            self._safe_log('error', f"[ARCButtonShop] API purchase error: {str(e)}")
            return False, "购买时出现系统错误"

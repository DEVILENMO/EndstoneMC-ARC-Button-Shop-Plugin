# 弧光按钮商店插件 (ARC Button Shop Plugin)

[![版本](https://img.shields.io/badge/版本-0.2.0-blue.svg)](https://github.com/EndstoneMC/python-example-plugin)
[![EndStone](https://img.shields.io/badge/EndStone-0.10+-green.svg)](https://github.com/EndstoneMC/endstone)
[![Python](https://img.shields.io/badge/Python-3.13+-yellow.svg)](https://www.python.org/)

一个复古的 Minecraft 服务器按钮商店系统，基于 EndStone 框架开发。玩家可以使用按钮创建个人商店，实现便捷的物品交易和服务器经济互动。

## 🎯 功能特性

### 🛒 核心功能
- **按钮商店**: 使用按钮创建个人商店，直观易用
- **物品交易**: 支持所有游戏物品的买卖交易
- **智能UI面板**: 现代化图形界面，支持商店创建、管理、浏览
- **价格自定义**: 灵活设置物品单价，自主经营
- **库存管理**: 实时库存显示和补充功能
- **交易记录**: 完整的交易历史记录和统计
- **商店保护**: 自动保护商店按钮，防止恶意破坏

### 👑 OP 系统商店（官方/无限商店）
- **无限出售（系统商店）**: OP 创建商店时可选择「无限出售」——不消耗背包物品，库存无限，玩家购买时系统发放物品（收入不归个人，代表官方）
- **无限收购（系统商店）**: OP 可选择「无限收购」——不预扣预算，收购预算无限，玩家出售物品时系统支付金钱（代表官方回收）
- **管理全部商店**: OP 在主面板可使用「管理全部商店（OP）」查看并管理服务器内所有玩家的商店
- **转换为无限商店**: OP 在任意商店的管理面板中可将该商店「转换为无限商店（系统商店）」，一键变为无限库存/预算的官方商店
- **系统商店标识**: 无限商店在列表和详情中显示「无限」库存/预算及 §e[系统] 标识

### ⚡ 性能优化
- **区块化存储**: 智能区块索引，快速查找附近商店
- **缓存机制**: 高效的数据缓存，减少数据库查询
- **异步处理**: 非阻塞操作，确保服务器流畅运行
- **内存优化**: 智能内存管理，适合大型服务器

### 💰 经济集成
- **经济系统集成**: 支持 ARC Core 或 UMoney（任意其一，自动识别）
- **自动交易**: 安全的资金转账和物品交换
- **防作弊**: 严格的交易验证和错误处理
- **多货币支持**: 支持服务器自定义货币系统
> 自动检测顺序：优先使用 `arc_core`，如果未安装则尝试 `umoney`；两者均不存在时，仅禁用金钱相关功能。

### 🌐 多语言支持
- **中英双语**: 完整的多语言界面支持
- **本地化**: 所有文本可自定义和本地化
- **可扩展**: 易于添加新语言包

## 📦 安装说明

1. **下载插件**: 将插件文件放置到服务器的 `plugins` 目录
2. **安装依赖**: 确保已安装 ARC Core 或 UMoney 经济插件（任意其一）  
   - 插件会自动识别已安装的经济插件（优先 `arc_core`，否则使用 `umoney`）
3. **重启服务器**: 重启服务器或使用插件管理器重新加载
4. **自动初始化**: 插件将自动创建必要的数据库和配置文件
5. **开始使用**: 玩家可以使用 `/shop` 命令开始创建商店

## 🎮 使用指南

### 📋 指令详解

| 指令 | 权限要求 | 语法 | 功能描述 |
|------|----------|------|----------|
| `/shop` | 所有玩家 | `/shop` | 打开商店主面板，管理和浏览商店 |
| `/shopmanage` | OP | `/shopmanage <list\|clear\|reload>` | 管理员商店管理指令 |

### 🏪 创建商店流程

1. **打开界面**: 使用 `/shop` 命令打开商店主面板
2. **选择类型**: 点击「创建商店」，选择「出售商店」或「收购商店」；**OP 额外可选**「无限出售（系统商店）」或「无限收购（系统商店）」
3. **选择物品**: 从背包中选择要出售/收购的物品（无限商店仅用于定义物品类型与单价，不消耗物品或预算）
4. **设置价格**: 输入单价；普通收购商店还需输入预算
5. **放置按钮**: 在想要创建商店的位置放置一个按钮
6. **右键激活**: 右键点击按钮完成商店创建

### 💳 购买商品流程

1. **发现商店**: 右键/点击互动其他玩家创建的商店按钮
2. **查看详情**: 浏览商品信息、价格、库存等
3. **输入数量**: 选择购买数量（不超过库存和资金限制）
4. **确认交易**: 确认购买，系统自动处理资金转账和物品发放

### 🔧 商店管理

#### 我的商店功能
- **库存管理**: 查看和补充商店库存  
- **价格调整**: 修改商品单价（计划中功能）
- **交易记录**: 查看销售历史和收入统计
- **商店删除**: 删除商店并取回剩余库存
- **系统商店**: 无限商店显示「无限」库存/预算，无需补充库存或收取物品

#### OP 管理功能
- **管理全部商店**: OP 在主面板点击「管理全部商店（OP）」可列出服务器内所有活跃商店，点击任意商店进行管理
- **转换为无限商店**: 在商店管理面板中，OP 可将该商店「转换为无限商店（系统商店）」，变为无限库存/预算的官方商店
- **删除他人商店**: OP 从「管理全部商店」删除他人商店时，剩余库存/预算及收集物品会返还给**店主**（店主在线则发放物品）

#### 商店保护机制
- **自动保护**: 商店按钮自动受到保护，防止恶意破坏
- **店主权限**: 只有店主可以破坏自己的商店按钮
- **智能返还**: 店主破坏按钮时自动返还剩余库存/预算
- **友好提示**: 非店主尝试破坏时显示友好提示信息

#### 附近商店浏览
- **智能搜索**: 基于区块快速查找附近商店
- **距离显示**: 显示商店与玩家的距离
- **商品预览**: 快速了解商店出售的商品

## 🔧 技术架构

### 区块化存储优化

插件采用智能区块索引系统，大幅提升性能：

#### 区块索引
- **16x16 区块划分**: 将世界按 Minecraft 标准区块大小划分
- **快速定位**: 玩家交互时先查区块索引，再精确查询位置
- **内存优化**: 避免遍历所有商店数据，性能提升数十倍

### 🏗️ 数据库设计

#### 核心表结构

**button_shops** - 商店信息表
- `shop_uuid` - 商店唯一标识
- `owner_xuid` - 店主XUID（主要标识符，永不变更）
- `owner_name` - 店主名称（用于显示）
- `shop_type` - 商店类型：`sell` 出售 / `buy` 收购
- `x/y/z/dimension` - 商店位置和维度
- `chunk_x/chunk_z` - 区块坐标（索引优化）
- `item_type/item_data` - 商品信息（含附魔、Lore 等）
- `quantity/stock` - 商品数量和库存（无限商店为特殊值表示无限）
- `unit_price` - 单价
- `is_infinite` - 是否无限商店（系统/官方商店，0=否 1=是）
- `create_time` - 创建时间

**chunk_index** - 区块索引表  
- `chunk_x/chunk_z/dimension` - 区块坐标
- `shop_count` - 该区块商店数量

**shop_transactions** - 交易记录表
- `shop_id` - 关联商店ID
- `buyer_xuid` - 买家XUID（主要标识符）
- `buyer_name` - 买家名称（用于显示）
- `quantity/total_price` - 交易数量和金额
- `transaction_time` - 交易时间

> 💡 **XUID说明**：插件使用玩家的XUID作为主要标识符，这确保了即使玩家更改游戏名称，其商店和交易记录仍然保持关联。玩家名称仅用于界面显示。

### 📡 API 接口文档

插件提供完整的 API 接口供其他插件调用：

#### 商店查询接口

##### `api_get_shop_at_position(x: int, y: int, z: int, dimension: str) -> dict | None`
获取指定位置的商店信息
```python
shop_plugin = server.plugin_manager.get_plugin("arc_button_shop")
shop = shop_plugin.api_get_shop_at_position(100, 64, -50, "overworld")
if shop:
    print(f"店主: {shop['owner_name']}")
    print(f"商品: {shop['item_type']}")
    print(f"库存: {shop['stock']}")
```

##### `api_get_player_shops(player_xuid: str) -> list`
获取玩家的所有商店（基于XUID）
```python
player_xuid = "12345678901234567890"  # 玩家的XUID
player_shops = shop_plugin.api_get_player_shops(player_xuid)
print(f"玩家拥有 {len(player_shops)} 个商店")
for shop in player_shops:
    print(f"位置: ({shop['x']}, {shop['y']}, {shop['z']})")
    print(f"店主: {shop['owner_name']}")
```

##### `api_get_nearby_shops(x: int, z: int, dimension: str, radius: int = 1) -> list`
获取指定位置附近的商店（基于区块）
```python
nearby = shop_plugin.api_get_nearby_shops(100, -50, "overworld", radius=2)
print(f"附近有 {len(nearby)} 个商店")
```

#### 交易接口

##### `api_purchase_from_shop(shop_id: int, buyer_xuid: str, quantity: int) -> tuple[bool, str]`
从商店购买商品（基于XUID）
```python
buyer_xuid = "98765432109876543210"  # 买家的XUID
success, message = shop_plugin.api_purchase_from_shop(
    shop_id=123,
    buyer_xuid=buyer_xuid,
    quantity=5
)
if success:
    print("购买成功")
else:
    print(f"购买失败: {message}")
```

##### `api_get_all_active_shops() -> list`
获取所有活跃的商店
```python
all_shops = shop_plugin.api_get_all_active_shops()
print(f"服务器共有 {len(all_shops)} 个活跃商店")
```

### API 使用示例

```python
# 完整的商店系统集成示例
class EconomyPlugin(Plugin):
    def on_enable(self):
        # 获取商店插件实例
        self.shop = self.server.plugin_manager.get_plugin("arc_button_shop")
        
    def get_market_stats(self):
        """获取市场统计信息"""
        all_shops = self.shop.api_get_all_active_shops()
        
        stats = {
            'total_shops': len(all_shops),
            'total_items': sum(shop['stock'] for shop in all_shops),
            'average_price': sum(shop['unit_price'] for shop in all_shops) / len(all_shops) if all_shops else 0,
            'top_sellers': self._get_top_sellers(all_shops)
        }
        
        return stats
    
    def create_automated_shop(self, location, item_data, price):
        """自动创建商店（管理员功能）"""
        # 这里可以集成自动商店创建逻辑
        pass
```

## 📊 数据存储

插件使用 SQLite 数据库进行数据持久化存储：

**数据库文件位置**: `plugins/ARCButtonShop/button_shop.db`

### 存储优势
- **轻量级**: SQLite 无需独立服务器，内嵌式存储
- **高性能**: 针对商店查询进行索引优化
- **数据安全**: 支持事务，确保交易数据一致性
- **易维护**: 单文件数据库，便于备份和迁移

## ⚙️ 配置系统

### 🌐 语言文件配置

语言文件位于项目根目录：
- `CN.txt` - 中文语言包
- `EN.txt` - 英文语言包

### 自定义文本

您可以编辑语言文件来自定义所有游戏内提示信息：

```ini
# CN.txt 示例 - 商店系统文本
SHOP_MAIN_PANEL_TITLE=§6按钮商店系统
SHOP_CREATE_BUTTON=§a创建商店
SHOP_PURCHASE_SUCCESS=§a购买成功！获得 {0} 个 {1}，花费 {2}
SHOP_SALE_NOTIFICATION=§a你的商店有新交易！§f{0} 购买了 {1} 个 {2}，收入 {3}
# ... 更多配置项
```

### 配置参数

```python
# 插件内置配置参数
CHUNK_SIZE = 16              # 区块大小（标准 Minecraft 区块）
MAX_SHOPS_PER_PLAYER = 50    # 每个玩家最大商店数量（计划功能）
TRANSACTION_LOG_DAYS = 30    # 交易记录保留天数（计划功能）
```

### 🎒 背包操作集成

插件基于 [EndStone Inventory API](https://endstone.dev/latest/reference/python/inventory/) 实现了完整的背包操作：

#### 支持的操作
- **📦 物品检测**：自动扫描玩家背包中的所有物品
- **➖ 物品移除**：安全地从背包中移除指定数量的物品  
- **➕ 物品添加**：智能地将物品添加到背包空位
- **🔍 库存验证**：交易前验证物品和资金充足性

#### 背包API特性
```python
# 基于EndStone标准API
inventory = player.inventory
item_stack = inventory.get_item(slot_index)
inventory.add_item(item_stack)
inventory.set_item(slot_index, item_stack)

# 支持ItemStack属性
item_stack.type      # 物品类型
item_stack.amount    # 物品数量  
item_stack.data      # 物品数据值
item_stack.item_meta # 物品元数据
```

#### 安全机制
- **事务性操作**：确保物品和金钱的原子性转移
- **错误恢复**：操作失败时自动回滚所有变更
- **背包检查**：防止背包满时的物品丢失

## 🛡️ 系统要求

- **EndStone**: 0.10 或更高版本  
- **Python**: 3.13 或更高版本
- **经济插件**: ARC Core 或 UMoney（二选一，自动识别）
- **操作系统**: Windows, Linux, macOS
- **内存**: 建议至少 1GB 可用内存
- **存储**: 约 5MB 磁盘空间（不含数据库增长）

## 🎮 使用场景

### 🏪 玩家经济服务器
- 建立完整的玩家交易生态系统
- 支持大型商业区建设
- 实现去中心化的商品流通

### 🏛️ 城镇建设服务器  
- 每个城镇可建立特色商店集群
- 支持区域性商业发展
- 促进玩家间合作与竞争

### 🎲 生存/冒险服务器
- 资源交易和装备买卖
- 稀有物品拍卖系统
- 探险收获变现渠道

### 🎪 小游戏服务器
- 游戏奖励兑换商店
- 临时活动商品销售
- 积分消费和奖品发放

## 📝 更新日志

### v0.2.0 (当前版本)

#### 基础功能
- ✨ 全新的按钮商店系统
- 🎨 现代化UI面板界面
- 🌍 完整多语言支持（中英双语）
- ⚡ 区块化存储优化，大幅提升性能
- 💰 经济系统集成：支持 ARC Core 或 UMoney（二选一）  
- 🔌 完整的API接口供其他插件调用
- 📊 SQLite数据库高效存储
- 🛒 支持商店管理、库存补充、交易记录
- 🔍 智能附近商店搜索功能
- 🆔 **XUID支持**：使用玩家XUID确保数据永久关联
- 🎒 **标准背包API**：基于EndStone官方inventory API
- 🔒 **事务安全**：完整的交易回滚和错误恢复机制
- 🛡️ **商店保护**：自动保护商店按钮，防止恶意破坏

#### OP 与系统商店（新增）
- 👑 **无限出售（系统商店）**：OP 创建商店时可选择「无限出售」——不消耗背包物品、库存无限，玩家购买时由系统发放物品（代表官方）
- 👑 **无限收购（系统商店）**：OP 可选择「无限收购」——不预扣预算、预算无限，玩家出售物品时由系统支付金钱（代表官方回收）
- 📋 **管理全部商店**：OP 主面板新增「管理全部商店（OP）」入口，可查看并管理服务器内所有商店；删除他人商店时返还给店主
- 🔄 **转换为无限商店**：OP 在任意商店管理面板可将该商店「转换为无限商店（系统商店）」
- 🏷️ **系统商店标识**：无限商店在列表中显示「无限」库存/预算及 §e[系统] 标识；数据库新增 `is_infinite` 字段并支持旧库自动迁移

### 计划功能 (v0.3.0)
- 🏷️ 商品分类和搜索系统
- 📈 价格历史和市场分析  
- 🎯 商店推广和广告系统
- 👥 商店合作和连锁经营
- 📱 Web管理面板

## 🤝 贡献指南

我们热烈欢迎社区贡献！

### 🐛 报告问题
- 使用 GitHub Issues 报告 bug
- 提供详细的错误信息和复现步骤
- 包含 EndStone 版本和插件版本信息
- 附上相关的日志文件

### 💡 功能建议
- 在 Issues 中提出新功能建议  
- 详细描述功能需求和使用场景
- 考虑功能的可行性和实用性
- 参与社区讨论和投票

### 👨‍💻 代码贡献
- Fork 项目并创建功能分支
- 遵循 PEP 8 Python 代码风格
- 添加必要的单元测试
- 更新相关文档
- 提交清晰的 Pull Request

### 🌍 本地化支持
- 翻译语言文件到其他语言
- 改进现有翻译质量
- 适配不同地区的使用习惯

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)，您可以：
- ✅ 自由使用和修改源代码
- ✅ 用于商业和非商业目的  
- ✅ 分发修改后的版本
- ⚠️ 需要保留原始许可证声明

## 📞 技术支持

获取帮助的多种方式：

- 📧 **邮箱支持**: DEVILENMO@gmail.com
- 🐛 **问题反馈**: [GitHub Issues](https://github.com/DEVILENMO/EndstoneMC-ARC-Button-Shop-Plugin/issues)
- 💬 **社区讨论**: 参与项目讨论区
- 📚 **文档中心**: 查阅完整文档和教程

### 常见问题快速解答
1. **Q**: 插件需要哪些依赖？  
   **A**: 需要安装经济插件中的任意一个：ARC Core 或 UMoney（插件会自动检测并优先使用 ARC Core）。

2. **Q**: 如何备份商店数据？  
   **A**: 复制 `plugins/ARCButtonShop/button_shop.db` 文件

3. **Q**: 商店数量有限制吗？  
   **A**: 目前无限制，后续版本将添加配置选项

---

**🛒 弧光按钮商店插件** - 打造您的 Minecraft 服务器专属经济生态！

*Built with ❤️ for the Minecraft community by DEVILENMO*
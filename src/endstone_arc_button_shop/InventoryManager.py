# -*- coding: utf-8 -*-
"""
背包管理类：统一负责玩家背包的读取、匹配、移除与发放。
复用附魔/洛尔等 Endstone API 的转换与比较逻辑，便于维护与扩展。
Endstone ItemMeta.enchants 返回 dict[Enchantment, int]，键不可哈希会报错，
故通过 get_enchant_level(id: str) 逐个查询已知附魔 id 获取等级。
"""
import traceback
from typing import Any, Dict, List

# Endstone 已知附魔 id 列表（minecraft:xxx），用于 get_enchant_level 逐个查询，避免访问 .enchants
_ENCHANT_IDS: List[str] = []


def _normalize_enchant_id(eid: str) -> str:
    """统一为 minecraft:xxx 格式，兼容旧数据中的短 id。"""
    if not eid:
        return eid
    if eid.startswith("minecraft:"):
        return eid
    return "minecraft:" + eid.replace(" ", "_").lower()


def _build_enchant_ids() -> List[str]:
    """从 endstone.enchantments.Enchantment 收集所有附魔字符串 id（仅执行一次）。"""
    global _ENCHANT_IDS
    if _ENCHANT_IDS:
        return _ENCHANT_IDS
    try:
        from endstone.enchantments import Enchantment
        for name in dir(Enchantment):
            if name.isupper():
                val = getattr(Enchantment, name, None)
                if isinstance(val, str) and val.startswith("minecraft:"):
                    _ENCHANT_IDS.append(val)
    except Exception:
        pass
    if not _ENCHANT_IDS:
        _ENCHANT_IDS = [
            "minecraft:aqua_affinity", "minecraft:bane_of_arthropods",
            "minecraft:blast_protection", "minecraft:breach", "minecraft:channeling",
            "minecraft:binding", "minecraft:vanishing", "minecraft:density",
            "minecraft:depth_strider", "minecraft:efficiency", "minecraft:feather_falling",
            "minecraft:fire_aspect", "minecraft:fire_protection", "minecraft:flame",
            "minecraft:frost_walker", "minecraft:impaling", "minecraft:infinity",
            "minecraft:knockback", "minecraft:looting", "minecraft:loyalty",
            "minecraft:luck_of_the_sea", "minecraft:lure", "minecraft:mending",
            "minecraft:multishot", "minecraft:piercing", "minecraft:power",
            "minecraft:projectile_protection", "minecraft:protection", "minecraft:punch",
            "minecraft:quick_charge", "minecraft:respiration", "minecraft:riptide",
            "minecraft:sharpness", "minecraft:silk_touch", "minecraft:smite",
            "minecraft:soul_speed", "minecraft:swift_sneak", "minecraft:thorns",
            "minecraft:unbreaking", "minecraft:wind_burst",
        ]
    return _ENCHANT_IDS


class InventoryManager:
    """
    专门负责玩家背包物品管理的类。
    依赖插件实例以使用 _safe_log 与 server（如语言翻译）。
    """

    def __init__(self, plugin: Any):
        """
        :param plugin: 插件实例，需提供 _safe_log(level, message) 与 server
        """
        self._plugin = plugin
        self._server = getattr(plugin, "server", None)

    def _log(self, level: str, message: str) -> None:
        if hasattr(self._plugin, "_safe_log") and self._plugin._safe_log:
            self._plugin._safe_log(level, message)
        else:
            print(f"[{level.upper()}] {message}")

    def _get_item_enchants(self, item_stack: Any) -> Dict[str, int]:
        """
        从 ItemStack 安全读取附魔信息（str->int）。
        不访问 ItemMeta.enchants（会触发 unhashable），改用 get_enchant_level(id) 逐个查询。
        """
        if not item_stack or not getattr(item_stack, "item_meta", None):
            return {}
        meta = item_stack.item_meta
        if not getattr(meta, "has_enchants", False):
            return {}
        result: Dict[str, int] = {}
        get_level = getattr(meta, "get_enchant_level", None)
        if not callable(get_level):
            return {}
        try:
            for enchant_id in _build_enchant_ids():
                try:
                    level = get_level(enchant_id)
                    if level and int(level) > 0:
                        result[enchant_id] = int(level)
                except Exception:
                    continue
        except Exception as enc_e:
            self._log(
                "warning",
                f"[ARCButtonShop] Get enchants (get_enchant_level) failed: {enc_e}\n{traceback.format_exc()}",
            )
        return result

    def _get_item_lore(self, item_stack: Any) -> List[str]:
        """从 ItemStack 安全读取 Lore。"""
        if not item_stack or not getattr(item_stack, "item_meta", None):
            return []
        if not getattr(item_stack.item_meta, "has_lore", False):
            return []
        try:
            lore = item_stack.item_meta.lore
            return list(lore) if isinstance(lore, list) else []
        except Exception:
            return []

    def _item_stack_matches_info(
        self,
        item_stack: Any,
        required_type: str,
        required_data: int,
        required_enchants: Dict[str, int],
        required_lore: List[str],
    ) -> bool:
        """判断单个 ItemStack 是否与 item_info 要求一致（类型、data、附魔、Lore）。"""
        if not item_stack or not item_stack.type:
            return False
        if item_stack.type.id != required_type or item_stack.data != required_data:
            return False
        item_enchants = self._get_item_enchants(item_stack)
        item_lore = self._get_item_lore(item_stack)
        if required_enchants:
            for eid, level in required_enchants.items():
                key = eid if eid in item_enchants else _normalize_enchant_id(eid)
                if item_enchants.get(key) != level:
                    return False
        if required_lore:
            if len(required_lore) != len(item_lore):
                return False
            for i, line in enumerate(required_lore):
                if i >= len(item_lore) or item_lore[i] != line:
                    return False
        return True

    def get_inventory_items(self, player: Any) -> List[Dict[str, Any]]:
        """
        获取玩家背包中所有有效物品的列表。
        每项为 dict：type, type_translation_key, name, count, data, enchants, lore, slot_index。
        """
        items: List[Dict[str, Any]] = []
        try:
            inventory = player.inventory
            for slot_index in range(inventory.size):
                try:
                    item_stack = inventory.get_item(slot_index)
                except Exception as slot_e:
                    self._log(
                        "warning",
                        f"[ARCButtonShop] get_item(slot={slot_index}) failed: {slot_e}",
                    )
                    continue
                if not item_stack or not item_stack.type or item_stack.amount <= 0:
                    continue
                try:
                    item_type_id = item_stack.type.id
                    item_type_translation_key = item_stack.type.translation_key
                    display_name = item_type_id
                    if self._server and hasattr(self._server, "language"):
                        try:
                            display_name = self._server.language.translate(
                                item_type_translation_key,
                                None,
                                getattr(player, "locale", None),
                            )
                        except Exception:
                            pass
                    if item_stack.item_meta and getattr(
                        item_stack.item_meta, "has_display_name", False
                    ):
                        display_name = item_stack.item_meta.display_name
                    enchants = self._get_item_enchants(item_stack)
                    lore = self._get_item_lore(item_stack)
                    items.append(
                        {
                            "type": item_type_id,
                            "type_translation_key": item_type_translation_key,
                            "name": display_name,
                            "count": item_stack.amount,
                            "data": item_stack.data,
                            "enchants": enchants,
                            "lore": lore,
                            "slot_index": slot_index,
                        }
                    )
                except Exception as item_e:
                    self._log(
                        "warning",
                        f"[ARCButtonShop] Slot {slot_index} item build failed: "
                        f"{item_e}\n{traceback.format_exc()}",
                    )
            return items
        except Exception as e:
            self._log(
                "error",
                f"[ARCButtonShop] Get player inventory error: {str(e)}\n{traceback.format_exc()}",
            )
            return []

    def has_item(self, player: Any, item_info: Dict[str, Any]) -> bool:
        """检查玩家背包是否拥有至少 item_info 要求数量、类型、data、附魔、Lore 一致的物品。"""
        try:
            inventory = player.inventory
            required_type = item_info["type"]
            required_count = item_info["count"]
            required_data = item_info.get("data", 0)
            required_enchants = item_info.get("enchants", {})
            required_lore = item_info.get("lore", [])
            total_count = 0
            for slot_index in range(inventory.size):
                item_stack = inventory.get_item(slot_index)
                if not self._item_stack_matches_info(
                    item_stack,
                    required_type,
                    required_data,
                    required_enchants,
                    required_lore,
                ):
                    continue
                total_count += item_stack.amount
                if total_count >= required_count:
                    return True
            return False
        except Exception as e:
            self._log("error", f"[ARCButtonShop] Player has item check error: {str(e)}")
            return False

    def remove_item(self, player: Any, item_info: Dict[str, Any]) -> bool:
        """从玩家背包移除与 item_info 匹配的物品（数量、类型、data、附魔、Lore）。"""
        try:
            inventory = player.inventory
            required_type = item_info["type"]
            required_count = item_info["count"]
            required_data = item_info.get("data", 0)
            required_enchants = item_info.get("enchants", {})
            required_lore = item_info.get("lore", [])
            if not self.has_item(player, item_info):
                return False
            remaining_to_remove = required_count
            slots_to_modify: List[tuple] = []
            for slot_index in range(inventory.size):
                if remaining_to_remove <= 0:
                    break
                item_stack = inventory.get_item(slot_index)
                if not self._item_stack_matches_info(
                    item_stack,
                    required_type,
                    required_data,
                    required_enchants,
                    required_lore,
                ):
                    continue
                remove_from_slot = min(remaining_to_remove, item_stack.amount)
                slots_to_modify.append((slot_index, item_stack, remove_from_slot))
                remaining_to_remove -= remove_from_slot
            for slot_index, original_stack, remove_count in slots_to_modify:
                new_amount = original_stack.amount - remove_count
                if new_amount <= 0:
                    inventory.set_item(slot_index, None)
                else:
                    original_stack.amount = new_amount
                    inventory.set_item(slot_index, original_stack)
            return True
        except Exception as e:
            self._log(
                "error", f"[ARCButtonShop] Remove item from player error: {str(e)}"
            )
            return False

    def give_item(self, player: Any, item_info: Dict[str, Any]) -> bool:
        """向玩家背包发放物品（类型、数量、data；附魔/Lore 若 API 支持则应用）。"""
        try:
            from endstone.inventory import ItemStack

            inventory = player.inventory
            item_type_id = item_info["type"]
            total_amount = item_info["count"]
            item_data = item_info.get("data", 0)
            if total_amount <= 0:
                self._log("warning", f"[ARCButtonShop] Invalid item amount: {total_amount}")
                return False
            remaining_to_give = total_amount
            while remaining_to_give > 0:
                current_amount = min(remaining_to_give, 64)
                if current_amount <= 0:
                    break
                item_stack = ItemStack(
                    type=item_type_id,
                    amount=current_amount,
                    data=item_data,
                )
                if item_info.get("enchants") or item_info.get("lore"):
                    try:
                        meta = item_stack.item_meta
                        if meta and item_info.get("enchants"):
                            for enchant_id, level in item_info["enchants"].items():
                                try:
                                    if hasattr(meta, "add_enchant"):
                                        meta.add_enchant(str(enchant_id), int(level))
                                except Exception as e:
                                    self._log(
                                        "warning",
                                        f"[ARCButtonShop] Failed to apply enchant {enchant_id}: {e}",
                                    )
                        if meta and item_info.get("lore") and hasattr(meta, "lore"):
                            try:
                                meta.lore = list(item_info["lore"])
                            except Exception as e:
                                self._log(
                                    "warning",
                                    f"[ARCButtonShop] Failed to apply lore: {e}",
                                )
                        if meta and hasattr(item_stack, "set_item_meta"):
                            item_stack.set_item_meta(meta)
                    except Exception as e:
                        self._log("warning", f"[ARCButtonShop] Apply item meta: {e}")
                remaining_items = inventory.add_item(item_stack)
                if remaining_items:
                    try:
                        if hasattr(remaining_items, "get"):
                            first_remaining = remaining_items.get(0)
                        elif isinstance(remaining_items, dict):
                            first_remaining = next(iter(remaining_items.values()), None)
                        else:
                            first_remaining = (
                                remaining_items[0]
                                if isinstance(remaining_items, list)
                                and len(remaining_items) > 0
                                else None
                            )
                        remaining_amount = (
                            getattr(first_remaining, "amount", 0)
                            if first_remaining is not None
                            else 0
                        )
                        added_amount = item_stack.amount - remaining_amount
                        remaining_to_give -= added_amount
                        if added_amount == 0:
                            self._log(
                                "warning",
                                f"[ARCButtonShop] Player {player.name} inventory full",
                            )
                            return False
                    except Exception as e:
                        self._log(
                            "warning",
                            f"[ARCButtonShop] Error calculating remaining: {e}",
                        )
                        remaining_to_give -= item_stack.amount
                else:
                    remaining_to_give -= item_stack.amount
            return True
        except Exception as e:
            self._log(
                "error", f"[ARCButtonShop] Give item to player error: {str(e)}"
            )
            return False

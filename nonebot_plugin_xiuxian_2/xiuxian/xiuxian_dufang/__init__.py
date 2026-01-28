import random
import json
import os
from pathlib import Path
from datetime import datetime
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent,
    PrivateMessageEvent,
    MessageSegment
)
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage
from ..xiuxian_utils.utils import check_user, get_msg_pic, handle_send, number_to, log_message
from ..xiuxian_config import XiuConfig

sql_message = XiuxianDateManage()
PLAYERSDATA = Path() / "data" / "xiuxian" / "players"

# 共享用户数据文件路径
SHARING_DATA_PATH = Path(__file__).parent / "unseal_sharing.json"
BANNED_UNSEAL_IDS = XiuConfig().banned_unseal_ids  # 禁止鉴石的群

# 初始化共享数据文件
if not SHARING_DATA_PATH.exists():
    with open(SHARING_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump({"users": []}, f, ensure_ascii=False, indent=4)

# 加载共享用户数据
def load_sharing_users():
    with open(SHARING_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["users"]

# 保存共享用户数据
def save_sharing_users(users):
    with open(SHARING_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump({"users": users}, f, ensure_ascii=False, indent=4)

# 添加共享用户
def add_sharing_user(user_id):
    users = load_sharing_users()
    if user_id not in users:
        users.append(user_id)
        save_sharing_users(users)
        return True
    return False

# 移除共享用户
def remove_sharing_user(user_id):
    users = load_sharing_users()
    if user_id in users:
        users.remove(user_id)
        save_sharing_users(users)
        return True
    return False

# 检查是否在共享列表中
def is_sharing_user(user_id):
    users = load_sharing_users()
    return user_id in users

# 获取随机共享用户(排除自己)
def get_random_sharing_users(user_id, count=3):
    users = [uid for uid in load_sharing_users() if uid != user_id]
    if not users:
        return []
    count = min(count, len(users))
    return random.sample(users, count)

# 鉴石数据管理
# 修改默认数据格式
def get_unseal_data(user_id):
    user_id = str(user_id)
    file_path = PLAYERSDATA / user_id / "unseal_data.json"
    
    default_data = {
        "unseal_info": {
            "count": 0,
            "total_cost": 0,
            "profit": 0,
            "loss": 0
        },
        "sharing_info": {
            "shared_profit": 0,
            "shared_loss": 0,
            "received_profit": 0,
            "received_loss": 0
        },
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if not file_path.exists():
        os.makedirs(file_path.parent, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 确保所有字段都存在
    for key in default_data:
        if key not in data:
            data[key] = default_data[key]
    
    return data

def save_unseal_data(user_id, data):
    user_id = str(user_id)
    file_path = PLAYERSDATA / user_id / "unseal_data.json"
    
    data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ========== 新增：猜骰子数据管理 ==========
def get_dice_data(user_id):
    """获取用户猜骰子数据"""
    user_id = str(user_id)
    file_path = PLAYERSDATA / user_id / "dice_data.json"
    
    default_data = {
        "dice_info": {
            "total_play": 0,      # 总玩次数
            "win_count": 0,       # 赢的次数
            "lose_count": 0,      # 输的次数
            "total_bet": 0,       # 总投注金额
            "total_win": 0,       # 总赢取金额
            "total_lose": 0       # 总输掉金额
        },
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if not file_path.exists():
        os.makedirs(file_path.parent, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 确保所有字段都存在
    for key in default_data:
        if key not in data:
            data[key] = default_data[key]
    
    return data

def save_dice_data(user_id, data):
    """保存用户猜骰子数据"""
    user_id = str(user_id)
    file_path = PLAYERSDATA / user_id / "dice_data.json"
    
    data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 鉴石命令
unseal = on_command("鉴石", priority=9, block=True)
unseal_share_on = on_command("鉴石共享开启", priority=10, block=True)
unseal_share_off = on_command("鉴石共享关闭", priority=10, block=True)
unseal_help = on_command("鉴石帮助", priority=10, block=True)
unseal_message = on_command("鉴石信息", priority=10, block=True)
# ========== 新增：猜骰子命令 ==========
golden_square_dice = on_command("金银坊", priority=9, block=True)
dice_help = on_command("猜骰子帮助", priority=10, block=True)
dice_record = on_command("骰子记录", priority=10, block=True)

# 鉴石帮助
@unseal_help.handle(parameterless=[Cooldown(cd_time=1.4)])
async def unseal_help_(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent):
    help_msg = """※※ 鉴石系统帮助 ※※
【鉴石】- 消耗灵石解封尘封之物
【鉴石共享开启】- 开启鉴石结果共享
【鉴石共享关闭】- 关闭鉴石结果共享
【鉴石信息】- 查看鉴石统计数据

◆ 基础消耗500灵石
◆ 可传入灵石作为额外消耗(最多当前灵石的10%)
◆ 共享开启后，你的鉴石结果可能会影响其他共享开启的道友
◆ 共享事件可能带来连锁反应，福祸难料"""
    await handle_send(bot, event, help_msg, md_type="鉴石", k1="鉴石", v1="鉴石", k2="信息", v2="鉴石信息", k3="灵石", v3="灵石")

# ========== 新增：猜骰子帮助 ==========
@dice_help.handle(parameterless=[Cooldown(cd_time=1.4)])
async def dice_help_(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent):
    help_msg = """※※ 金银坊猜骰子帮助 ※※
【金银坊 猜数 投注金额】- 参与猜骰子游戏
  示例：金银坊 奇 5000 、金银坊 3 8000
◆ 猜数规则：可猜1-6的数字，或猜"奇"/"偶"
◆ 投注规则：单次投注最低100灵石，最高为当前灵石的40%
◆ 奖励规则：
  - 猜具体数字（1-6）：猜对获得投注金额2.5倍灵石
  - 猜奇偶：猜对获得投注金额1.5倍灵石
  - 猜错均扣除投注金额
◆ 查看记录：发送【骰子记录】可查看猜骰子统计数据"""
    await handle_send(bot, event, help_msg, md_type="金银坊", k1="金银坊", v1="猜骰子", k2="信息", v2="骰子帮助", k3="灵石", v3="灵石")

# ========== 新增：骰子记录查询 ==========
@dice_record.handle(parameterless=[Cooldown(cd_time=1.4)])
async def dice_record_(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent):
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await handle_send(bot, event, msg, md_type="我要修仙")
        return
    
    user_id = user_info['user_id']
    data = get_dice_data(user_id)
    dice_info = data["dice_info"]
    
    # 计算胜率
    win_rate = (dice_info["win_count"] / dice_info["total_play"] * 100) if dice_info["total_play"] > 0 else 0
    # 计算净收益
    net_profit = dice_info["total_win"] - dice_info["total_lose"]
    
    msg = (
        "※※ 金银坊猜骰子记录 ※※\n"
        f"【总玩次数】: {dice_info['total_play']}次\n"
        f"【赢的次数】: {dice_info['win_count']}次\n"
        f"【输的次数】: {dice_info['lose_count']}次\n"
        f"【胜率】: {win_rate:.1f}%\n\n"
        f"【总投注】: {number_to(dice_info['total_bet'])}灵石\n"
        f"【总赢取】: {number_to(dice_info['total_win'])}灵石\n"
        f"【总输掉】: {number_to(dice_info['total_lose'])}灵石\n"
        f"【净收益】: {number_to(net_profit)}灵石\n\n"
        f"最后更新: {data['last_update']}"
    )
    
    await handle_send(bot, event, msg, md_type="金银坊", k1="金银坊", v1="猜骰子", k2="信息", v2="骰子记录", k3="灵石", v3="灵石")

# 共享开启
@unseal_share_on.handle(parameterless=[Cooldown(cd_time=1.4)])
async def unseal_share_on_(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent):
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await handle_send(bot, event, msg, md_type="我要修仙")
        return
    
    user_id = user_info['user_id']
    if is_sharing_user(user_id):
        msg = "你已经开启了鉴石结果共享！"
    else:
        add_sharing_user(user_id)
        msg = "成功开启鉴石结果共享！你的鉴石过程可能会对其他道友产生影响。"
        log_message(user_id, "开启了鉴石结果共享功能")
    
    await handle_send(bot, event, msg, md_type="鉴石", k1="鉴石", v1="鉴石", k2="信息", v2="鉴石信息", k3="关闭", v3="鉴石共享关闭")

# 共享关闭
@unseal_share_off.handle(parameterless=[Cooldown(cd_time=1.4)])
async def unseal_share_off_(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent):
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await handle_send(bot, event, msg, md_type="我要修仙")
        return
    
    user_id = user_info['user_id']
    if not is_sharing_user(user_id):
        msg = "你尚未开启鉴石结果共享！"
    else:
        remove_sharing_user(user_id)
        msg = "成功关闭鉴石结果共享！你的鉴石过程将不再影响其他道友。"
        log_message(user_id, "关闭了鉴石结果共享功能")
    
    await handle_send(bot, event, msg, md_type="鉴石", k1="鉴石", v1="鉴石", k2="信息", v2="鉴石信息", k3="开启", v3="鉴石共享开启")

# 处理共享事件
async def handle_shared_event(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent, user_id: str, current_cost: int, total_cost: int, result_type: str):
    """
    处理共享事件
    :param current_cost: 本次鉴石消耗的灵石
    :param total_cost: 累计鉴石总消耗
    """
    sharing_users = get_random_sharing_users(user_id, random.randint(1, 3))
    if not sharing_users:
        return None, None
    
    # 获取当前用户信息
    user_info = sql_message.get_user_info_with_id(user_id)
    if not user_info:
        return None, None
    
    user_name = user_info['user_name']
    
    # 计算共享基数 (本次鉴石消耗×0.1)
    base_amount = int(current_cost * 0.1)
    
    # 计算消耗倍率 (每10亿增加1%，最多50%)
    cost_bonus = min(total_cost // 1000000000, 50) / 100
    
    # 最终影响值 = 基数 × (1 + 倍率)
    effect_amount = int(base_amount * (1 + cost_bonus))
    
    # 根据鉴石结果类型选择共享事件类型
    if result_type in ["great_success", "success"]:
        event_type = "profit"  # 正面事件
        eligible_events = [e for e in SHARING_EVENTS if "福泽" in e["title"]]
    else:
        event_type = "loss"    # 负面事件
        eligible_events = [e for e in SHARING_EVENTS if "福泽" not in e["title"]]
    
    if not eligible_events:
        return None, None
    
    event_data = random.choice(eligible_events)
    
    # 处理共享用户的损失/收益
    affected_users = []
    effect_amount_all = 0
    actual_shared_loss_all = 0
    for target_id in sharing_users:
        target_info = sql_message.get_user_info_with_id(target_id)
        if not target_info:
            continue
            
        target_name = target_info.get('user_name', '未知道友')
        target_stone = int(target_info.get('stone', 0))
        target_data = get_unseal_data(target_id)
        
        if event_type == "profit":
            # 增加灵石
            sql_message.update_ls(target_id, effect_amount, 1)
            target_data["sharing_info"]["received_profit"] += effect_amount
            effect_amount_all += effect_amount
            amount = effect_amount_all
            affected_users.append(f"{target_name}(+{number_to(effect_amount)})")
            
            log_message(target_id, 
                f"受到道友{user_name}的鉴石福泽共享，获得灵石：{number_to(effect_amount)}枚")
            
            log_message(user_id,
                f"鉴石福泽共享给道友{target_name}，共享灵石：{number_to(effect_amount)}枚")
        else:
            # 减少灵石
            actual_shared_loss = min(effect_amount, target_stone)
            if actual_shared_loss > 0:
                sql_message.update_ls(target_id, actual_shared_loss, 2)
                target_data["sharing_info"]["received_loss"] += actual_shared_loss
                actual_shared_loss_all += actual_shared_loss
                amount = actual_shared_loss_all
                affected_users.append(f"{target_name}(-{number_to(actual_shared_loss)})")
                
                log_message(target_id,
                    f"受到道友{user_name}的鉴石影响，损失灵石：{number_to(actual_shared_loss)}枚")
                
                log_message(user_id,
                    f"鉴石影响波及道友{target_name}，造成损失：{number_to(actual_shared_loss)}枚")
        
        save_unseal_data(target_id, target_data)
    
    if not affected_users:
        return None, None
    
    # 构建消息
    msg = [
        f"\n※※ {event_data['title']} ※※",
        event_data['desc'],
        f"\n共享倍率: +{int(cost_bonus*100)}%",
        f"\n受影响道友: {', '.join(affected_users)}"
    ]
    
    return "\n".join(msg), amount

# 鉴石信息
@unseal_message.handle(parameterless=[Cooldown(cd_time=1.4)])
async def unseal_message_(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent):
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await handle_send(bot, event, msg, md_type="我要修仙")
        return
    
    user_id = user_info['user_id']
    data = get_unseal_data(user_id)
    
    msg = (
        "※※ 鉴石统计信息 ※※\n"
        f"【鉴石次数】: {data['unseal_info']['count']}次\n"
        f"【总消耗】: {number_to(data['unseal_info'].get('total_cost', 0))}灵石\n"
        f"【总收益】: {number_to(data['unseal_info']['profit'])}灵石\n"
        f"【总损失】: {number_to(data['unseal_info']['loss'])}灵石\n\n"
        "※※ 共享统计信息 ※※\n"
        f"【共享福泽】: {number_to(data['sharing_info']['shared_profit'])}灵石\n"
        f"【共享损失】: {number_to(data['sharing_info']['shared_loss'])}灵石\n"
        f"【获得福泽】: {number_to(data['sharing_info']['received_profit'])}灵石\n"
        f"【承受损失】: {number_to(data['sharing_info']['received_loss'])}灵石\n\n"
        f"最后更新: {data['last_update']}"
    )
    
    await handle_send(bot, event, msg, md_type="鉴石", k1="鉴石", v1="鉴石", k2="信息", v2="鉴石信息", k3="灵石", v3="灵石")

# ========== 猜骰子主逻辑（修改后） ==========
@golden_square_dice.handle(parameterless=[Cooldown(stamina_cost=5)])
async def golden_square_dice_(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await handle_send(bot, event, msg, md_type="我要修仙")
        return
    
    user_id = user_info['user_id']
    current_stone = int(user_info['stone'])
    
    # 解析参数
    arg_text = args.extract_plain_text().strip()
    args_list = arg_text.split()
    
    # 参数校验
    if len(args_list) != 2:
        msg = "参数格式错误！正确格式：金银坊 猜数 投注金额\n示例：金银坊 奇 5000 、金银坊 3 8000"
        await handle_send(bot, event, msg, md_type="金银坊", k1="金银坊", v1="猜骰子", k2="信息", v2="骰子帮助", k3="灵石", v3="灵石")
        return
    
    guess_str, bet_str = args_list
    
    # 校验投注金额
    if not bet_str.isdigit():
        msg = "投注金额必须为数字！"
        await handle_send(bot, event, msg, md_type="金银坊", k1="金银坊", v1="猜骰子", k2="信息", v2="骰子帮助", k3="灵石", v3="灵石")
        return
    
    bet_amount = int(bet_str)
    # 投注金额限制：最低100，最高当前灵石的40%
    min_bet = 100000
    max_bet = current_stone // 40
    
    if bet_amount < min_bet:
        msg = f"单次投注最低{min_bet}灵石！"
        await handle_send(bot, event, msg, md_type="金银坊", k1="金银坊", v1="猜骰子", k2="信息", v2="骰子帮助", k3="灵石", v3="灵石")
        return
    
    if bet_amount > max_bet:
        msg = f"单次投注最高为当前灵石的40%（{number_to(max_bet)}灵石）！"
        await handle_send(bot, event, msg, md_type="金银坊", k1="金银坊", v1="猜骰子", k2="信息", v2="骰子帮助", k3="灵石", v3="灵石")
        return
    
    if current_stone < bet_amount:
        msg = f"当前灵石不足！需要{number_to(bet_amount)}灵石，仅有{number_to(current_stone)}灵石。"
        await handle_send(bot, event, msg, md_type="金银坊", k1="金银坊", v1="猜骰子", k2="信息", v2="骰子帮助", k3="灵石", v3="灵石")
        return
    
    # 生成随机骰子数（1-6）
    dice_num = random.randint(1, 6)
    
    # 解析用户猜测
    is_correct = False
    guess_desc = ""
    reward_rate = 1.5  # 默认倍率（猜奇偶）
    
    if guess_str.isdigit():
        # 猜具体数字 - 难度更高，奖励倍率2.5倍
        guess_num = int(guess_str)
        if guess_num < 1 or guess_num > 6:
            msg = "猜数只能是1-6的数字，或'奇'/'偶'！"
            await handle_send(bot, event, msg, md_type="金银坊", k1="金银坊", v1="猜骰子", k2="信息", v2="骰子帮助", k3="灵石", v3="灵石")
            return
        
        guess_desc = f"数字{guess_num}"
        is_correct = (guess_num == dice_num)
        reward_rate = 2.5  # 猜具体数字的奖励倍率
    elif guess_str in ["奇", "偶"]:
        # 猜奇偶 - 基础倍率1.5倍
        guess_desc = guess_str
        if guess_str == "奇":
            is_correct = (dice_num % 2 == 1)
        else:
            is_correct = (dice_num % 2 == 0)
    else:
        msg = "猜数格式错误！只能是1-6的数字，或'奇'/'偶'。"
        await handle_send(bot, event, msg, md_type="金银坊", k1="金银坊", v1="猜骰子", k2="信息", v2="骰子帮助", k3="灵石", v3="灵石")
        return
    
    # 处理游戏结果
    dice_data = get_dice_data(user_id)
    dice_info = dice_data["dice_info"]
    
    # 更新总投注次数和金额
    dice_info["total_play"] += 1
    dice_info["total_bet"] += bet_amount
    
    if is_correct:
        # 猜对：根据不同玩法计算奖励
        win_amount = int(bet_amount * reward_rate)
        sql_message.update_ls(user_id, win_amount, 1)
        new_stone = current_stone + win_amount - bet_amount  # 先扣投注，再加奖励
        
        # 更新统计
        dice_info["win_count"] += 1
        dice_info["total_win"] += win_amount
        
        # 构建消息（区分不同玩法的奖励说明）
        result_msg = (
            f"※※ 金银坊猜骰子 ※※\n"
            f"你投注了{number_to(bet_amount)}灵石，猜测：{guess_desc}\n"
            f"骰子摇出：{dice_num}点\n"
            f"🎉 恭喜猜对！获得{number_to(win_amount)}灵石奖励（倍率{reward_rate}倍）！\n"
            f"当前灵石：{number_to(new_stone)}"
        )
        
        log_message(user_id, f"猜骰子猜对！投注{number_to(bet_amount)}灵石，获得{number_to(win_amount)}灵石奖励（倍率{reward_rate}倍）")
    else:
        # 猜错：扣除投注金额（所有玩法扣除规则一致）
        sql_message.update_ls(user_id, bet_amount, 2)
        new_stone = current_stone - bet_amount
        
        # 更新统计
        dice_info["lose_count"] += 1
        dice_info["total_lose"] += bet_amount
        
        # 构建消息
        result_msg = (
            f"※※ 金银坊猜骰子 ※※\n"
            f"你投注了{number_to(bet_amount)}灵石，猜测：{guess_desc}\n"
            f"骰子摇出：{dice_num}点\n"
            f"❌ 很遗憾猜错了！扣除{number_to(bet_amount)}灵石\n"
            f"当前灵石：{number_to(new_stone)}"
        )
        
        log_message(user_id, f"猜骰子猜错！投注{number_to(bet_amount)}灵石，扣除{number_to(bet_amount)}灵石")
    
    # 保存骰子数据
    save_dice_data(user_id, dice_data)
    
    # 发送结果
    await handle_send(bot, event, result_msg, md_type="金银坊", k1="金银坊", v1="猜骰子", k2="结果", v2="骰子结果", k3="灵石", v3="灵石")

# 鉴石主逻辑
@unseal.handle(parameterless=[Cooldown(stamina_cost=20)])
async def unseal_(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await handle_send(bot, event, msg, md_type="我要修仙")
        return
    
    user_id = user_info['user_id']
    current_stone = int(user_info['stone'])
    
    # 灵石门槛检查
    if current_stone < 10000000:
        needed = 10000000 - current_stone
        msg = f"金银阁暂不接待灵石不足的道友，还需{number_to(needed)}灵石"
        await handle_send(bot, event, msg, md_type="鉴石", k1="鉴石", v1="鉴石", k2="信息", v2="鉴石信息", k3="灵石", v3="灵石")
        return
    
    if str(send_group_id) in BANNED_UNSEAL_IDS:
        msg = f"本群不可鉴石！"
        await handle_send(bot, event, msg, md_type="鉴石", k1="鉴石", v1="鉴石", k2="信息", v2="鉴石信息", k3="灵石", v3="灵石")
        return
    
    # 处理传入的灵石参数
    arg = args.extract_plain_text().strip()
    if arg.isdigit():
        input_stone = int(arg)
        max_stone = current_stone // 10  # 最大可传入灵石为当前灵石的40%
        max_stone = min(max_stone, 1000000000)
        cost = min(input_stone, max_stone) if max_stone > 0 else 0
        if cost <= 0:
            msg = "传入的灵石无效，将使用基础解封消耗100万灵石"
            cost = 1000000
    else:
        cost = 1000000  # 基础解封消耗
    
    if current_stone < cost:
        msg = f"解封需要{cost}枚灵石作为法力消耗，当前仅有{current_stone}枚！"
        await handle_send(bot, event, msg, md_type="鉴石", k1="鉴石", v1="鉴石", k2="信息", v2="鉴石信息", k3="灵石", v3="灵石")
        return
    
    # 扣除消耗
    sql_message.update_ls(user_id, cost, 2)
    current_stone = (current_stone - cost)
    
    # 获取/初始化鉴石数据
    unseal_data = get_unseal_data(user_id)
    unseal_data["unseal_info"]["count"] += 1
    unseal_data["unseal_info"]["total_cost"] = unseal_data["unseal_info"].get("total_cost", 0) + cost
    
    # 随机选择封印物
    entity = random.choice(SEALED_ENTITIES)
    base_msg = [
        f"\n※※ 发现{entity['name']} ※※",
        f"{entity['desc']}",
        "你开始谨慎地解封这个尘封已久的..."
    ]
    
    # 添加随机解封过程
    base_msg.append(random.choice(UNSEAL_PROCESS))
    
    # 结果判定 (大成功15%, 成功50%, 失败30%, 大失败5%)
    result = random.choices(
        ["great_success", "success", "failure", "critical_failure"],
        weights=[15, 50, 30, 5]
    )[0]
    
    # 筛选符合当前物品类型的事件
    eligible_events = [
        e for e in UNSEAL_EVENTS[result] 
        if "all" in e["type"] or entity["type"] in e["type"]
    ]
    events = random.choice(eligible_events) if eligible_events else random.choice(UNSEAL_EVENTS[result])
    
    base_ratio = events["effect"]()
    if result in ["great_success", "success"]:  # 成功情况
        gain = int(cost * base_ratio)
        sql_message.update_ls(user_id, gain, 1)
        effect_text = f"获得 {number_to(gain)} 灵石"
        unseal_data["unseal_info"]["profit"] += gain
        log_message(user_id, f"进行鉴石，消耗灵石：{number_to(cost)}枚\n鉴石成功！获得灵石：{number_to(gain)}枚")
    else:  # 失败情况
        loss = int(cost * base_ratio)
        actual_loss = min(loss, current_stone)
        sql_message.update_ls(user_id, actual_loss, 2)
        effect_text = f"损失 {number_to(actual_loss)} 灵石"
        unseal_data["unseal_info"]["loss"] += actual_loss
        log_message(user_id, f"进行鉴石，消耗灵石：{number_to(cost)}枚\n鉴石失败！损失灵石：{number_to(actual_loss)}枚")
    
    user_info = sql_message.get_user_info_with_id(user_id)
    current_stone = int(user_info['stone'])
    
    # 构建完整消息
    full_msg = [
        "\n".join(base_msg),
        f"\n\n※※ {events['title']} ※※",
        events['desc'],
        f"\n{events['outcome']}，{effect_text}",
        f"\n\n消耗：{number_to(cost)}灵石",
        f"\n当前灵石：{current_stone}({number_to(current_stone)})"
    ]
    
    final_msg = "\n".join(full_msg)
    await handle_send(bot, event, final_msg, md_type="鉴石", k1="鉴石", v1="鉴石", k2="信息", v2="鉴石信息", k3="灵石", v3="灵石")
    
    # 处理共享事件
    if is_sharing_user(user_id):
        # 负面结果有20%概率触发共享，大失败100%触发
        if (result in ["failure", "critical_failure"] and random.random() < 0.2) or result == "critical_failure":
            shared_event_msg, amount = await handle_shared_event(
                bot, event, 
                user_id=user_id,
                current_cost=cost,          # 本次鉴石消耗
                total_cost=unseal_data["unseal_info"]["total_cost"],  # 总消耗
                result_type=result
            )
            if shared_event_msg:
                await handle_send(bot, event, shared_event_msg, md_type="鉴石", k1="鉴石", v1="鉴石", k2="信息", v2="鉴石信息", k3="灵石", v3="灵石")
                # 根据结果类型更新统计
                if result in ["great_success", "success"]:
                    unseal_data["sharing_info"]["shared_profit"] += amount
                else:
                    unseal_data["sharing_info"]["shared_loss"] += amount
        # 正面结果有10%概率触发共享，大成功100%触发
        elif (result == "success" and random.random() < 0.1) or (result == "great_success"):
            shared_event_msg, amount = await handle_shared_event(
                bot, event,
                user_id=user_id,
                current_cost=cost,          # 本次鉴石消耗
                total_cost=unseal_data["unseal_info"]["total_cost"],  # 总消耗
                result_type=result
            )
            if shared_event_msg:
                await handle_send(bot, event, shared_event_msg, md_type="鉴石", k1="鉴石", v1="鉴石", k2="信息", v2="鉴石信息", k3="灵石", v3="灵石")
                # 根据结果类型更新统计
                if result in ["great_success", "success"]:
                    unseal_data["sharing_info"]["shared_profit"] += amount
                else:
                    unseal_data["sharing_info"]["shared_loss"] += amount
    
    # 保存鉴石数据
    save_unseal_data(user_id, unseal_data)


# 尘封之物类型（共20种）
SEALED_ENTITIES = [
    {"name": "上古玉简", "desc": "一块泛着微光的古老玉简，表面符文流转", "type": "传承"},
    {"name": "灵兽卵", "desc": "一枚布满奇异纹路的卵，生命气息时强时弱", "type": "灵宠"},
    {"name": "古剑残片", "desc": "一截断裂的剑尖，仍散发着凌厉剑气", "type": "法宝"},
    {"name": "封印石匣", "desc": "表面刻有九重禁制的青灰色石匣", "type": "容器"},
    {"name": "妖族大能", "desc": "一位被玄冰封印的妖族修士，面容模糊", "type": "存在"},
    {"name": "丹鼎碎片", "desc": "破损的炼丹炉残片，隐约有药香残留", "type": "器具"},
    {"name": "灵植种子", "desc": "几粒干瘪的种子，却蕴含着惊人生命力", "type": "灵材"},
    {"name": "洞府令牌", "desc": "一块青铜令牌，刻有'玄天'二字", "type": "钥匙"},
    {"name": "破损阵盘", "desc": "残缺的阵法核心，复杂纹路依稀可辨", "type": "阵法"},
    {"name": "古修遗蜕", "desc": "一具盘坐的干尸，身着古老道袍", "type": "遗物"},
    {"name": "灵泉结晶", "desc": "拳头大小的透明晶体，内含水状灵气", "type": "灵材"},
    {"name": "魔修法器", "desc": "一件血色铃铛，轻轻摇动却无声响", "type": "法宝"},
    {"name": "天外陨铁", "desc": "漆黑如墨的金属，表面有星辰纹路", "type": "材料"},
    {"name": "古佛舍利", "desc": "一颗金色骨珠，散发着祥和佛光", "type": "佛宝"},
    {"name": "龙族逆鳞", "desc": "一片巴掌大的七彩鳞片，坚硬无比", "type": "材料"},
    {"name": "鬼修魂灯", "desc": "一盏青铜古灯，灯焰呈幽绿色", "type": "鬼器"},
    {"name": "仙酿玉壶", "desc": "玲珑剔透的玉壶，壶口有灵雾缭绕", "type": "container"},
    {"name": "巫族图腾", "desc": "刻有狰狞兽首的黑色木牌", "type": "巫器"},
    {"name": "剑仙剑意", "desc": "一缕被封存的凌厉剑气", "type": "意境"},
    {"name": "时空碎片", "desc": "不规则的透明薄片，周围空间微微扭曲", "type": "奇物"}
]

# 解封结果事件（共40种不同事件）
UNSEAL_EVENTS = {
    "great_success": [
        {
            "title": "上古传承现世",
            "desc": "玉简突然大放光明，海量信息直接灌入你的识海！",
            "outcome": "你将这份完整传承复刻后高价拍卖",
            "effect": lambda: random.uniform(2.0, 2.5),  # 200%-250%收益
            "type": ["传承"]
        },
        {
            "title": "灵兽认主",
            "desc": "卵壳破裂，一只稀有灵兽破壳而出，立即与你缔结契约！",
            "outcome": "各大宗门争相出价购买这只潜力无限的灵兽",
            "effect": lambda: random.uniform(1.8, 2.3),  # 180%-230%收益
            "type": ["灵宠"]
        },
        {
            "title": "法宝认主",
            "desc": "残剑突然发出龙吟之声，化作流光融入你的丹田！",
            "outcome": "这件古宝主动认你为主，引起轰动",
            "effect": lambda: random.uniform(1.7, 2.2),  # 170%-220%收益
            "type": ["法宝"]
        },
        {
            "title": "秘境开启",
            "desc": "石匣中飞出一把钥匙，在空中划出一道空间裂隙！",
            "outcome": "你将秘境入口信息出售给修真联盟",
            "effect": lambda: random.uniform(2.2, 2.7),  # 220%-270%收益
            "type": ["容器", "钥匙"]
        },
        {
            "title": "前辈指点",
            "desc": "妖族大能苏醒后，为感谢你解封之恩传授秘法！",
            "outcome": "你将部分功法心得出售",
            "effect": lambda: random.uniform(1.6, 2.1),  # 160%-210%收益
            "type": ["存在"]
        }
    ],
    "success": [
        {
            "title": "残缺功法",
            "desc": "玉简中记载着一部残缺的上古功法",
            "outcome": "将残篇出售给收藏家",
            "effect": lambda: random.uniform(1.5, 1.8),  # 150%-180%收益
            "type": ["传承"]
        },
        {
            "title": "灵材现世",
            "desc": "解封出一批珍贵的炼器材料",
            "outcome": "炼器师们高价收购",
            "effect": lambda: random.uniform(1.5, 1.9),  # 150%-190%收益
            "type": ["灵材", "材料"]
        },
        {
            "title": "古丹方",
            "desc": "发现几张古老的丹药配方",
            "outcome": "炼丹师们争相购买",
            "effect": lambda: random.uniform(1.5, 1.8),  # 150%-180%收益
            "type": ["器具", "传承"]
        },
        {
            "title": "灵宠幼体",
            "desc": "孵化出一只普通灵兽",
            "outcome": "灵兽店老板出价收购",
            "effect": lambda: random.uniform(1.5, 1.7),  # 150%-170%收益
            "type": ["灵宠"]
        },
        {
            "title": "法器残件",
            "desc": "解封出几件尚可使用的法器",
            "outcome": "低阶修士抢购这些古物",
            "effect": lambda: random.uniform(1.5, 1.7),  # 150%-170%收益
            "type": ["法宝", "器具"]
        }
    ],
    "failure": [
        {
            "title": "禁制反噬",
            "desc": "解封时触发防御禁制，狂暴灵气将你击伤！",
            "outcome": "不得不花费灵石购买疗伤丹药",
            "effect": lambda: 0.5,  # 50%损失
            "type": ["all"]
        },
        {
            "title": "灵性尽失",
            "desc": "解封手法不当，物品灵性尽失化为凡物",
            "outcome": "白白浪费了法力",
            "effect": lambda: 0,  # 0%损失
            "type": ["all"]
        },
        {
            "title": "劫修偷袭",
            "desc": "就在你专注解封时，一伙劫修突然袭击！",
            "outcome": "被抢走部分灵石",
            "effect": lambda: 0.2,  # 20%损失
            "type": ["all"]
        },
        {
            "title": "邪气侵蚀",
            "desc": "解封过程中冒出诡异黑雾，污染了你的灵石",
            "outcome": "不得不丢弃被污染的灵石",
            "effect": lambda: 0.3,  # 30%损失
            "type": ["all"]
        },
        {
            "title": "幻境困阵",
            "desc": "陷入物品自带的幻阵，耗费大量法力才脱困",
            "outcome": "修为损耗严重",
            "effect": lambda: 0.1,  # 10%损失
            "type": ["all"]
        }
    ],
    "critical_failure": [
        {
            "title": "魔头出世",
            "desc": "不慎释放出被封印的千年魔头！天地为之变色！",
            "outcome": "魔头抢走你全部灵石后扬长而去",
            "effect": lambda: 1.0,  # 100%损失
            "type": ["存在", "鬼器", "魔器"]
        },
        {
            "title": "古老诅咒",
            "desc": "触发物品上的恶毒诅咒，厄运缠身！",
            "outcome": "花费巨资请高人解咒",
            "effect": lambda: 0.8,  # 80%损失
            "type": ["遗物", "巫器"]
        },
        {
            "title": "灵气暴走",
            "desc": "引发恐怖的灵气风暴，摧毁了周围一切！",
            "outcome": "赔偿损失耗尽积蓄",
            "effect": lambda: 0.9,  # 90%损失
            "type": ["奇物", "意境"]
        },
        {
            "title": "时空乱流",
            "desc": "被卷入狂暴的时空裂隙，九死一生才逃脱！",
            "outcome": "疗伤花费巨大",
            "effect": lambda: 0.7,  # 70%损失
            "type": ["时空碎片"]
        },
        {
            "title": "宗门追责",
            "desc": "解封的物品竟是某大宗门失窃的至宝！",
            "outcome": "被迫交出全部身家作为赔偿",
            "effect": lambda: 1.0,  # 100%损失
            "type": ["佛宝", "传承"]
        }
    ]
}

# 解封过程描述（20种）
UNSEAL_PROCESS = [
    "周围灵气突然剧烈波动，古老符文在空中若隐若现...",
    "一股强大的威压让你呼吸困难，解封过程异常艰难...",
    "物品表面开始浮现出复杂的道纹，闪烁着奇异光芒...",
    "耳边响起神秘的低语，仿佛来自远古的呼唤...",
    "解封法诀打出后，物品突然悬浮到半空中...",
    "周围的温度急剧下降，呼出的气息都凝结成了白霜...",
    "地面微微震颤，仿佛有什么可怕的存在正在苏醒...",
    "你的法力如潮水般被物品吸收，几乎要被抽干...",
    "物品突然发出刺目的强光，让你不得不闭上眼睛...",
    "时间仿佛在这一刻变得异常缓慢，每一个动作都无比费力...",
    "解封过程中，你恍惚看到了远古战场的幻象...",
    "物品周围的空间开始扭曲变形，产生细小的裂痕...",
    "一股沁人心脾的异香突然弥漫开来，让人精神一振...",
    "你的神识被拉入一个奇异空间，面对着一个古老意志...",
    "解封到关键时刻，天空突然乌云密布，雷声隆隆...",
    "物品表面渗出暗红色的液体，如同鲜血般诡异...",
    "四周突然陷入绝对的黑暗，连神识都无法感知...",
    "你感受到一股充满恶意的视线正从物品内部窥视着你...",
    "解封法诀引发了小型灵气漩涡，周围的物品都被卷起...",
    "物品突然发出刺耳的尖啸声，几乎要震破耳膜..."
]

# 共享事件类型
SHARING_EVENTS = [
    {
        "title": "劫修团伙",
        "desc": "你解封时引发的灵气波动引来了劫修团伙！",
        "effect": lambda cost: int(cost * random.uniform(0.4, 0.6)),  # 40%-60%损失
        "message": "这群劫修顺着灵气波动又袭击了附近的其他道友！"
    },
    {
        "title": "灵气污染",
        "desc": "解封过程中产生了危险的灵气污染！",
        "effect": lambda cost: int(cost * random.uniform(0.3, 0.5)),  # 30%-50%损失
        "message": "污染的灵气扩散开来，影响了附近修炼的其他道友！"
    },
    {
        "title": "诅咒蔓延",
        "desc": "物品上的古老诅咒开始向外扩散！",
        "effect": lambda cost: int(cost * random.uniform(0.35, 0.55)),  # 35%-55%损失
        "message": "诅咒之力蔓延，不幸波及了附近的其他道友！"
    },
    {
        "title": "福泽共享",
        "desc": "解封产生的祥瑞之气扩散开来！",
        "effect": lambda cost: int(cost * random.uniform(0.3, 0.5)),  # 30%-50%收益
        "message": "祥瑞之气惠及了附近的其他道友！"
    }
]
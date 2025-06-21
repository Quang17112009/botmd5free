import telebot
from telebot import types
import random
import string
import json
import time
from keep_alive import keep_alive

keep_alive()

BOT_TOKEN = "7581761997:AAFPeyJDvTYQoVob-P3MDuXpaEByrEtbVT8"  # Đảm bảo đây là token chính xác
ADMIN_IDS = [6915752059]
SUPPORT_GROUP_LINK = "https://t.me/+cd71g9Cwx9Y1ZTM1"
SUPPORT_GROUP_ID = -1002781947864 # Thay thế bằng ID nhóm thực tế của bạn

bot = telebot.TeleBot(BOT_TOKEN)

history = []
profit = 0
user_coins = {}
user_free_trial_end_time = {} # Giữ lại nhưng không dùng, để tránh lỗi nếu có trong data.json cũ
referral_links = {}
user_pending_confirmation = {}
CTV_IDS = []

DATA_FILE = "data.json"

# Hằng số cho hệ thống xu
COIN_PER_MD5_ANALYZE = 1 # Đã sửa: Mỗi lần phân tích MD5 chỉ trừ 1 xu
REFERRAL_BONUS_COINS = 15
GROUP_JOIN_BONUS_COINS = 30

def generate_nap_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def analyze_md5(md5_hash):
    global history

    algo1 = int(md5_hash[-2:], 16) % 2
    result1 = "Tài" if algo1 == 0 else "Xỉu"

    total_hex = sum(int(md5_hash[i:i+2], 16) for i in range(0, 8, 2))
    result2 = "Tài" if total_hex % 2 == 0 else "Xỉu"

    full_sum = sum(int(md5_hash[i:i+2], 16) for i in range(0, 32, 2))
    result3 = "Tài" if full_sum % 5 < 3 else "Xỉu"

    results = [result1, result2, result3]
    final_result = max(set(results), key=results.count)

    prediction = {
        "md5": md5_hash,
        "dự đoán": final_result,
        "thuật toán": {
            "thuật toán 1": result1,
            "thuật toán 2": result2,
            "thuật toán 3": result3,
        },
        "kết quả thực tế": None
    }
    history.append(prediction)

    return (f"✅ KẾT QUẢ PHÂN TÍCH PHIÊN TÀI XỈU MD5:\n"
            f"🔹 MD5: {md5_hash}\n\n"
            f"📊 Kết quả theo từng thuật toán:\n"
            f"   - Thuật toán 1 (2 ký tự cuối): {result1}\n"
            f"   - Thuật toán 2 (4 byte đầu): {result2}\n"
            f"   - Thuật toán 3 (Tổng toàn MD5): {result3}\n\n"
            f"✅ Kết luận cuối cùng: {final_result} | 🎯 Tín hiệu mạnh!\n"
            f"💡 Gợi ý: Cầu {final_result} đang lên mạnh!")

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            "user_coins": user_coins,
            "history": history,
            "profit": profit,
            "user_free_trial_end_time": user_free_trial_end_time,
            "referral_links": referral_links,
            "user_pending_confirmation": user_pending_confirmation,
            "CTV_IDS": CTV_IDS
        }, f)

def load_data():
    global user_coins, history, profit, user_free_trial_end_time, referral_links, user_pending_confirmation, CTV_IDS
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            user_coins = data.get("user_coins", {})
            history = data.get("history", [])
            profit = data.get("profit", 0)
            user_free_trial_end_time = data.get("user_free_trial_end_time", {})
            referral_links = data.get("referral_links", {})
            user_pending_confirmation = data.get("user_pending_confirmation", {})
            CTV_IDS = data.get("CTV_IDS", [])
    except FileNotFoundError:
        save_data()

load_data()

def is_user_member(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['member', 'creator', 'administrator']
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 400 and "user not found" in e.description:
            return False
        elif e.error_code == 400 and "chat not found" in e.description:
            print(f"Error: Chat ID {chat_id} not found. Please ensure the bot is in the group and the ID is correct.")
            return False
        print(f"Error checking user membership: {e}")
        return False

def is_admin_or_ctv(user_id):
    return user_id in ADMIN_IDS or user_id in CTV_IDS


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    referrer_id = None
    if len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
            if referrer_id == user_id:
                referrer_id = None
        except ValueError:
            referrer_id = None

    response_text = ("👋 Chào mừng đến với BOT TÀI XỈU VIP!\n\n"
                     "Để nhận **30 xu** miễn phí và sử dụng bot, "
                     "vui lòng tham gia nhóm sau và nhấn nút 'Xác nhận đã tham gia nhóm':\n"
                     f"{SUPPORT_GROUP_LINK}\n\n"
                     "Các lệnh bạn có thể sử dụng:\n"
                     "🔹 /tx <mã MD5> → Dự đoán kết quả (trừ {COIN_PER_MD5_ANALYZE} xu).\n"
                     "🔹 /nap <số tiền> → Mua xu dùng.\n"
                     "🔹 /dabank <số tiền> <nội dung> → Gửi thông tin giao dịch ngân hàng để admin duyệt.\n"
                     "🔹 /history → Xem lịch sử & số xu.\n"
                     "🔹 /support → Liên hệ hỗ trợ.\n"
                     "🔹 /moiban → Tạo link giới thiệu để nhận thêm xu.")

    markup = types.InlineKeyboardMarkup()
    btn_confirm = types.InlineKeyboardButton("✅ Xác nhận đã tham gia nhóm", callback_data='confirm_group_join')
    markup.add(btn_confirm)

    bot.reply_to(message, response_text, reply_markup=markup)

    user_pending_confirmation[user_id] = True
    save_data()

    if referrer_id and referrer_id != user_id:
        if str(user_id) not in referral_links or referral_links.get(str(user_id)) != referrer_id:
            user_coins[referrer_id] = user_coins.get(referrer_id, 0) + REFERRAL_BONUS_COINS
            referral_links[str(user_id)] = referrer_id
            save_data()
            bot.send_message(referrer_id,
                             f"🎉 Bạn vừa giới thiệu thành công một người dùng mới "
                             f"và được cộng thêm {REFERRAL_BONUS_COINS} xu!\n"
                             f"Tổng xu hiện tại: {user_coins.get(referrer_id, 0)}")
            print(f"User {referrer_id} gained {REFERRAL_BONUS_COINS} coins from referral by {user_id}.")


@bot.callback_query_handler(func=lambda call: call.data == 'confirm_group_join')
def handle_confirm_group_join(call):
    user_id = call.from_user.id
    if not user_pending_confirmation.get(user_id, False):
        bot.answer_callback_query(call.id, "Bạn đã xác nhận hoặc không có yêu cầu chờ xử lý.")
        return

    if is_user_member(SUPPORT_GROUP_ID, user_id):
        user_coins[user_id] = user_coins.get(user_id, 0) + GROUP_JOIN_BONUS_COINS
        if user_id in user_pending_confirmation:
            del user_pending_confirmation[user_id]
        save_data()

        bot.send_message(user_id,
                         f"✅ Chúc mừng! Bạn đã xác nhận thành công và được cộng {GROUP_JOIN_BONUS_COINS} xu!\n"
                         f"Tổng xu hiện tại của bạn: {user_coins.get(user_id, 0)}\n"
                         f"Bây giờ bạn có thể dùng lệnh /tx để dự đoán.")
        bot.answer_callback_query(call.id, f"Bạn đã nhận {GROUP_JOIN_BONUS_COINS} xu!")
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        print(f"User {user_id} confirmed group join and received {GROUP_JOIN_BONUS_COINS} coins.")
    else:
        bot.answer_callback_query(call.id, "❌ Bạn chưa tham gia nhóm. Vui lòng tham gia nhóm trước khi xác nhận.")
        bot.send_message(user_id, f"⚠️ Vui lòng tham gia nhóm này trước khi nhấn nút xác nhận: {SUPPORT_GROUP_LINK}")


@bot.message_handler(commands=['tx'])
def get_tx_signal(message):
    user_id = message.from_user.id
    parts = message.text.split()

    if len(parts) < 2 or len(parts[1]) != 32:
        bot.reply_to(message, "❌ Vui lòng nhập mã MD5 hợp lệ!\n🔹 Ví dụ: /tx d41d8cd98f00b204e9800998ecf8427e")
        return

    coins = user_coins.get(user_id, 0)

    if coins < COIN_PER_MD5_ANALYZE:
        bot.reply_to(message, f"⚠️ Bạn không đủ xu! Vui lòng dùng lệnh /nap <số tiền> để mua thêm "
                              f"hoặc tham gia nhóm hỗ trợ để nhận {GROUP_JOIN_BONUS_COINS} xu: "
                              f"{SUPPORT_GROUP_LINK} và nhấn nút xác nhận.")
        return

    user_coins[user_id] = coins - COIN_PER_MD5_ANALYZE
    save_data()
    md5_hash = parts[1]
    result_analysis = analyze_md5(md5_hash)

    bot.reply_to(message, result_analysis + f"\n\n💰 Xu còn lại: {user_coins[user_id]}")


@bot.message_handler(commands=['result'])
def set_actual_result(message):
    global profit
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Bạn không có quyền sử dụng lệnh này!")
        return

    parts = message.text.split()
    if len(parts) < 2 or parts[1].lower() not in ["tài", "xỉu", "gãy"]:
        bot.reply_to(message, "❌ Nhập kết quả hợp lệ! (tài/xỉu/gãy)")
        return

    actual_result = parts[1].capitalize()
    if not history:
        bot.reply_to(message, "⚠️ Chưa có dự đoán nào!")
        return

    last_prediction = history[-1]
    last_prediction["kết quả thực tế"] = actual_result

    status_message = ""
    if last_prediction["dự đoán"] == actual_result:
        profit += 1
        status_message = "✅ Thắng kèo! 📈 (+1 điểm)"
    elif actual_result.lower() == "gãy":
        profit -= 1
        status_message = "❌ Gãy kèo! 📉 (-1 điểm)"
    else:
        profit -= 1
        status_message = "❌ Thua kèo! 📉 (-1 điểm)"

    save_data()
    bot.reply_to(message, f"📢 Cập nhật kết quả: {actual_result}\n{status_message}\n💰 Tổng lãi/lỗ: {profit} điểm")

@bot.message_handler(commands=['history'])
def show_history(message):
    if not history:
        bot.reply_to(message, "📭 Chưa có dữ liệu lịch sử!")
        return

    history_text = "📜 LỊCH SỬ DỰ ĐOÁN & KẾT QUẢ:\n"
    for idx, entry in enumerate(history[-5:], start=max(0, len(history) - 5) + 1):
        history_text += f"🔹 Lần {idx}:\n"
        history_text += f"   - 📊 Dự đoán: {entry['dự đoán']}\n"
        history_text += f"   - 🎯 Kết quả thực tế: {entry['kết quả thực tế'] or '❓ Chưa có'}\n"

    user_id = message.from_user.id
    coins = user_coins.get(user_id, 0)
    history_text += f"\n💰 Tổng lãi/lỗ: {profit} điểm\n💰 Xu còn lại: {coins}"

    bot.reply_to(message, history_text)

@bot.message_handler(commands=['nap'])
def handle_nap(message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "❌ Vui lòng nhập số tiền hợp lệ! Ví dụ: /nap 100000")
        return

    amount = int(parts[1])
    user_id = message.from_user.id
    # Tính xu dựa trên 1000đ = 10 xu, hoặc 1 xu = 100đ
    # Để đơn giản, nếu 1 lần sài tốn 1 xu, thì bạn có thể thiết lập 1000đ = 10 xu
    # Hoặc nếu bạn muốn 1000đ = 100 xu, tức là 1 xu = 10đ
    # Tôi sẽ giữ tỷ lệ 1000đ = 10 xu để mua số xu lớn hơn dễ hơn.
    # coins_to_add = (amount // 1000) * COIN_PER_MD5_ANALYZE # Cái này sai, nó sẽ nhân với 1 xu
    # Đúng ra là 1000đ = X xu, thì tổng xu là (số tiền / 1000) * X
    # Giả sử 1000đ = 10 xu:
    coins_to_add = (amount // 1000) * 10 # 1000đ = 10 xu
    
    # Giới hạn số xu mua: min (10000đ = 100 xu), max (10,000,000đ = 100,000 xu)
    if coins_to_add < 100 or coins_to_add > 100000:
        bot.reply_to(message, f"⚠️ Bạn chỉ được mua từ 100 xu đến 100,000 xu "
                              f"(tương ứng từ 10,000đ đến 10,000,000đ).")
        return

    code = generate_nap_code()
    reply = (f"💳 HƯỚNG DẪN NẠP TIỀN MUA XU\n\n"
             f"➡️ Số tài khoản: 497720088\n"
             f"➡️ Ngân hàng: MB Bank\n"
             f"➡️ Số tiền: {amount} VNĐ\n"
             f"➡️ Nội dung chuyển khoản: NAP{code}\n\n"
             f"⏳ Sau khi chuyển khoản, admin sẽ duyệt và cộng {coins_to_add} xu cho bạn.")

    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"📥 YÊU CẦU NẠP TIỀN\n"
                                   f"👤 User ID: {user_id}\n"
                                   f"💰 Số tiền: {amount} VNĐ\n"
                                   f"💰 Xu mua: {coins_to_add}\n"
                                   f"📝 Nội dung: NAP{code}\n\n"
                                   f"Duyệt bằng lệnh: /approve {user_id} {coins_to_add}")

    bot.reply_to(message, reply)

@bot.message_handler(commands=['approve'])
def approve_nap(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    parts = message.text.split()
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        bot.reply_to(message, "❌ Sai cú pháp. Dùng /approve <user_id> <số xu>")
        return

    uid = int(parts[1])
    coins = int(parts[2])
    user_coins[uid] = user_coins.get(uid, 0) + coins

    save_data()
    bot.send_message(uid, f"✅ Bạn đã được cộng {coins} xu dùng!\n🎯 Dùng lệnh /tx <md5> để dự đoán.")
    bot.reply_to(message, f"Đã cộng {coins} xu cho user {uid}.")

@bot.message_handler(commands=['dabank'])
def handle_dabank(message):
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "❌ Vui lòng nhập đầy đủ thông tin giao dịch. Ví dụ: /dabank 100000 Nội dung chuyển tiền")
        return

    amount = parts[1]
    content = " ".join(parts[2:])
    user_id = message.from_user.id

    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"📥 YÊU CẦU NẠP TIỀN (GIAO DỊCH NGÂN HÀNG)\n"
                                   f"👤 User ID: {user_id}\n"
                                   f"💰 Số tiền: {amount} VNĐ\n"
                                   f"📝 Nội dung: {content}\n\n"
                                   f"Duyệt bằng lệnh: /approve {user_id} <số xu>")

    bot.reply_to(message, f"⏳ Đang chờ admin duyệt giao dịch.\n"
                          f"Sau khi admin duyệt, bạn sẽ nhận được xu dùng.\n"
                          f"💰 Số tiền: {amount} VNĐ\n"
                          f"📝 Nội dung: {content}")

@bot.message_handler(commands=['support'])
def handle_support(message):
    # Đã sửa: Thông tin liên hệ admin
    bot.reply_to(message, "📩 Nếu bạn cần hỗ trợ, vui lòng liên hệ với admin tại: @heheviptool")

@bot.message_handler(commands=['moiban'])
def handle_moiban(message):
    user_id = message.from_user.id
    referral_link = f"https://t.me/your_bot_username?start={user_id}" # THAY 'your_bot_username' BẰNG USERNAME CỦA BOT BẠN
    bot.reply_to(message, f"🔗 Đây là link giới thiệu của bạn:\n`{referral_link}`\n\n"
                          f"Mỗi khi có người mới sử dụng link này và nhấn /start, "
                          f"bạn sẽ được cộng thêm {REFERRAL_BONUS_COINS} xu!")


@bot.message_handler(commands=['addxu'])
def add_coins(message):
    user_id_requester = message.from_user.id
    if not is_admin_or_ctv(user_id_requester):
        bot.reply_to(message, "⛔ Bạn không có quyền sử dụng lệnh này!")
        return

    parts = message.text.split()
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        bot.reply_to(message, "❌ Sai cú pháp. Dùng /addxu <user_id> <số_xu>")
        return

    target_user_id = int(parts[1])
    amount = int(parts[2])

    if amount <= 0:
        bot.reply_to(message, "❌ Số xu cần cộng phải lớn hơn 0.")
        return

    user_coins[target_user_id] = user_coins.get(target_user_id, 0) + amount
    save_data()

    bot.reply_to(message, f"✅ Đã cộng {amount} xu cho người dùng {target_user_id}.")
    try:
        bot.send_message(target_user_id,
                         f"🎉 Bạn đã được cộng thêm {amount} xu bởi Admin/CTV!\n"
                         f"Tổng xu hiện tại: {user_coins.get(target_user_id, 0)}")
    except Exception as e:
        print(f"Không thể gửi tin nhắn cho user {target_user_id}: {e}")
        bot.reply_to(message, f"⚠️ Đã cộng xu nhưng không thể gửi thông báo cho người dùng {target_user_id} (có thể họ đã chặn bot).")


@bot.message_handler(commands=['ctv'])
def grant_ctv_role(message):
    user_id_requester = message.from_user.id
    if user_id_requester not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Bạn không có quyền sử dụng lệnh này! Lệnh này chỉ dành cho Admin.")
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "❌ Sai cú pháp. Dùng /ctv <user_id>")
        return

    target_user_id = int(parts[1])

    if target_user_id in ADMIN_IDS:
        bot.reply_to(message, f"Người dùng {target_user_id} đã là Admin rồi.")
        return

    if target_user_id in CTV_IDS:
        bot.reply_to(message, f"Người dùng {target_user_id} đã là CTV rồi.")
        return

    CTV_IDS.append(target_user_id)
    save_data()

    bot.reply_to(message, f"✅ Đã cấp quyền CTV cho người dùng {target_user_id}.")
    try:
        bot.send_message(target_user_id,
                         f"🎉 Chúc mừng! Bạn đã được cấp quyền Cộng tác viên (CTV)!\n"
                         f"Bây giờ bạn có thể sử dụng lệnh /addxu <user_id> <số_xu> để cộng xu cho người dùng khác.")
    except Exception as e:
        print(f"Không thể gửi tin nhắn cho user {target_user_id}: {e}")
        bot.reply_to(message, f"⚠️ Đã cấp quyền CTV nhưng không thể gửi thông báo cho người dùng {target_user_id}.")


bot.polling()

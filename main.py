import telebot
import random
import string
import json
import time
from keep_alive import keep_alive

keep_alive()

BOT_TOKEN = "7581761997:AAFPeyJDvTYQoVob-P3MDuXpaEByrEtbVT8"  # Đảm bảo đây là token chính xác
ADMIN_IDS = [6915752059]
SUPPORT_GROUP_LINK = "https://t.me/+cd71g9Cwx9Y1ZTM1" # Link nhóm hỗ trợ
# ID của nhóm bạn muốn người dùng tham gia để nhận free trial
# Bạn cần lấy ID này bằng cách thêm bot vào nhóm và dùng một bot khác để lấy chat ID, hoặc in message.chat.id từ bot của bạn
SUPPORT_GROUP_ID = -1002781947864 # Thay thế bằng ID nhóm thực tế của bạn

bot = telebot.TeleBot(BOT_TOKEN)

history = []
profit = 0
user_turns = {}
user_free_trial_end_time = {} # Thêm để lưu thời gian kết thúc free trial
referral_links = {} # Lưu trữ link giới thiệu
DATA_FILE = "data.json"

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
            "user_turns": user_turns,
            "history": history,
            "profit": profit,
            "user_free_trial_end_time": user_free_trial_end_time,
            "referral_links": referral_links
        }, f)

def load_data():
    global user_turns, history, profit, user_free_trial_end_time, referral_links
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            user_turns = data.get("user_turns", {})
            history = data.get("history", [])
            profit = data.get("profit", 0)
            user_free_trial_end_time = data.get("user_free_trial_end_time", {})
            referral_links = data.get("referral_links", {})
    except FileNotFoundError:
        save_data()

load_data()

# Hàm kiểm tra xem người dùng có phải là thành viên của nhóm không
def is_user_member(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['member', 'creator', 'administrator']
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 400 and "user not found" in e.description:
            return False # Người dùng không tồn tại trong nhóm
        elif e.error_code == 400 and "chat not found" in e.description:
            print(f"Error: Chat ID {chat_id} not found. Please ensure the bot is in the group and the ID is correct.")
            return False
        print(f"Error checking user membership: {e}")
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    referrer_id = None
    # Kiểm tra xem có tham số referral trong lệnh start không
    if len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
            # Đảm bảo người giới thiệu không phải là chính họ
            if referrer_id == user_id:
                referrer_id = None
        except ValueError:
            referrer_id = None

    response_text = ("👋 Chào mừng đến với BOT TÀI XỈU VIP!\n"
                     "Để sử dụng bot miễn phí trong 7 ngày, vui lòng tham gia nhóm sau:\n"
                     f"{SUPPORT_GROUP_LINK}\n\n"
                     "Sau khi tham gia nhóm, bot sẽ tự động kiểm tra và cấp quyền cho bạn. "
                     "Nếu bot không cấp quyền tự động, vui lòng liên hệ admin.\n\n"
                     "Các lệnh bạn có thể sử dụng:\n"
                     "🔹 /tx <mã MD5> → Dự đoán kết quả (mỗi lần trừ 1 lượt).\n"
                     "🔹 /nap <số tiền> → Mua lượt dùng.\n"
                     "🔹 /dabank <số tiền> <nội dung> → Gửi thông tin giao dịch ngân hàng để admin duyệt.\n"
                     "🔹 /history → Xem lịch sử & lãi/lỗ.\n"
                     "🔹 /support → Liên hệ hỗ trợ.\n"
                     "🔹 /moiban → Tạo link giới thiệu để nhận thêm lượt.")

    bot.reply_to(message, response_text)

    # Kiểm tra và cấp free trial nếu chưa có hoặc đã hết hạn
    if user_id not in user_free_trial_end_time or user_free_trial_end_time[user_id] < time.time():
        if is_user_member(SUPPORT_GROUP_ID, user_id):
            user_free_trial_end_time[user_id] = time.time() + (7 * 24 * 60 * 60) # 7 ngày
            user_turns[user_id] = user_turns.get(user_id, 0) + 7 # Cấp 7 lượt
            save_data()
            bot.send_message(user_id, "🎉 Chúc mừng! Bạn đã nhận được 7 ngày dùng thử miễn phí (7 lượt)! "
                                      "Hãy dùng lệnh /tx để bắt đầu dự đoán.")
            print(f"User {user_id} granted 7-day free trial.")
        else:
            bot.send_message(user_id, "⚠️ Để nhận 7 ngày dùng thử miễn phí, bạn cần tham gia nhóm hỗ trợ!")

    # Xử lý người giới thiệu
    if referrer_id and referrer_id != user_id:
        if str(user_id) not in referral_links: # Chỉ cộng lượt cho người giới thiệu nếu đây là lượt giới thiệu mới
            user_turns[referrer_id] = user_turns.get(referrer_id, 0) + 1
            referral_links[str(user_id)] = referrer_id # Lưu lại để tránh cộng nhiều lần
            save_data()
            bot.send_message(referrer_id, f"🎉 Bạn vừa giới thiệu thành công một người dùng mới và được cộng thêm 1 lượt dùng!")
            print(f"User {referrer_id} gained 1 turn from referral by {user_id}.")


@bot.message_handler(commands=['tx'])
def get_tx_signal(message):
    user_id = message.from_user.id
    parts = message.text.split()

    if len(parts) < 2 or len(parts[1]) != 32:
        bot.reply_to(message, "❌ Vui lòng nhập mã MD5 hợp lệ!\n🔹 Ví dụ: /tx d41d8cd98f00b204e9800998ecf8427e")
        return

    # Kiểm tra xem user có free trial đang hoạt động không
    is_free_trial_active = user_id in user_free_trial_end_time and user_free_trial_end_time[user_id] > time.time()
    turns = user_turns.get(user_id, 0)

    if not is_free_trial_active and turns <= 0:
        bot.reply_to(message, "⚠️ Bạn đã hết lượt dùng! Vui lòng dùng lệnh /nap <số tiền> để mua thêm "
                              "hoặc tham gia nhóm hỗ trợ để nhận 7 ngày miễn phí: "
                              f"{SUPPORT_GROUP_LINK}")
        return

    if is_free_trial_active:
        # Trong thời gian free trial, không trừ lượt từ user_turns
        # Giả định mỗi lượt MD5 tương ứng với 1 ngày trong free trial hoặc bạn muốn free trial là không giới hạn lượt trong 7 ngày
        # Ở đây tôi sẽ dùng model là mỗi lượt trừ 1 lượt trong free trial, nhưng không giới hạn số lượt nếu người dùng có lượt mua
        # Hoặc bạn có thể đơn giản là cho phép dùng không giới hạn trong 7 ngày nếu user có free trial

        # Cách 1: Free trial cho phép dùng không giới hạn lượt trong 7 ngày
        pass # Không trừ lượt

        # Cách 2: Free trial cấp số lượt nhất định (ví dụ 7 lượt)
        # Nếu bạn muốn free trial chỉ cấp 7 lượt, thì phải có một biến đếm riêng cho free trial
        # Để đơn giản, tôi sẽ cho phép dùng miễn phí nếu free trial đang hoạt động.
        # Nếu muốn giới hạn số lượt trong free trial, bạn cần thêm logic phức tạp hơn.
    else:
        # Nếu không có free trial hoặc đã hết hạn, trừ lượt từ user_turns
        user_turns[user_id] = turns - 1
        save_data()

    md5_hash = parts[1]
    result_analysis = analyze_md5(md5_hash)

    remaining_info = ""
    if is_free_trial_active:
        remaining_time = int(user_free_trial_end_time[user_id] - time.time())
        days = remaining_time // (24 * 60 * 60)
        hours = (remaining_time % (24 * 60 * 60)) // (60 * 60)
        remaining_info = f"⏳ Thời gian dùng thử miễn phí còn lại: {days} ngày {hours} giờ"
    else:
        remaining_info = f"🎫 Lượt còn lại: {user_turns[user_id]}"

    bot.reply_to(message, result_analysis + f"\n\n{remaining_info}")


@bot.message_handler(commands=['result'])
def set_actual_result(message):
    global profit
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Bạn không có quyền sử dụng lệnh này!")
        return

    parts = message.text.split()
    if len(parts) < 2 or parts[1].lower() not in ["tài", "xỉu", "gãy"]: # Thêm "gãy"
        bot.reply_to(message, "❌ Nhập kết quả hợp lệ! (tài/xỉu/gãy)")
        return

    actual_result = parts[1].capitalize()
    if not history:
        bot.reply_to(message, "⚠️ Chưa có dự đoán nào!")
        return

    last_prediction = history[-1]
    last_prediction["kết quả thực tế"] = actual_result

    # Sử dụng thông tin từ ngày 2025-06-03: Cứ 2 lần MD5 'Gãy' thì có 1 lần khác
    # Đây là logic phức tạp, tôi sẽ giả định 'Gãy' là một trường hợp thua đặc biệt
    # và sẽ không ảnh hưởng trực tiếp đến việc tính profit theo cách thông thường.
    # Nếu 'Gãy' là kết quả thực tế, và dự đoán không phải 'Gãy', thì vẫn là thua.
    # Nếu 'Gãy' được coi là một trạng thái đặc biệt không liên quan đến Tài/Xỉu,
    # thì bạn cần định nghĩa rõ hơn cách nó ảnh hưởng đến profit.
    # Hiện tại, tôi sẽ xử lý 'Gãy' như một kết quả thua bình thường.

    status_message = ""
    if last_prediction["dự đoán"] == actual_result:
        profit += 1
        status_message = "✅ Thắng kèo! 📈 (+1 điểm)"
    elif actual_result.lower() == "gãy":
        profit -= 1 # Coi như thua khi Gãy
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
    # Lấy 5 mục cuối cùng hoặc ít hơn nếu lịch sử không đủ
    for idx, entry in enumerate(history[-5:], start=max(0, len(history) - 5) + 1):
        history_text += f"🔹 Lần {idx}:\n"
        history_text += f"   - 📊 Dự đoán: {entry['dự đoán']}\n"
        history_text += f"   - 🎯 Kết quả thực tế: {entry['kết quả thực tế'] or '❓ Chưa có'}\n"

    user_id = message.from_user.id
    turns = user_turns.get(user_id, 0)
    history_text += f"\n💰 Tổng lãi/lỗ: {profit} điểm\n🎫 Lượt còn lại: {turns}"

    if user_id in user_free_trial_end_time and user_free_trial_end_time[user_id] > time.time():
        remaining_time = int(user_free_trial_end_time[user_id] - time.time())
        days = remaining_time // (24 * 60 * 60)
        hours = (remaining_time % (24 * 60 * 60)) // (60 * 60)
        history_text += f"\n⏳ Thời gian dùng thử miễn phí còn lại: {days} ngày {hours} giờ"

    bot.reply_to(message, history_text)

@bot.message_handler(commands=['nap'])
def handle_nap(message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "❌ Vui lòng nhập số tiền hợp lệ! Ví dụ: /nap 100000")
        return

    amount = int(parts[1])
    user_id = message.from_user.id
    # Mỗi 1000đ = 1 lượt
    turns_to_add = amount // 1000
    if turns_to_add < 10 or turns_to_add > 10000:
        bot.reply_to(message, "⚠️ Bạn chỉ được mua từ 10 đến 10000 lượt (tương ứng từ 10,000đ đến 10,000,000đ).")
        return

    code = generate_nap_code()
    reply = (f"💳 HƯỚNG DẪN NẠP TIỀN MUA LƯỢT\n\n"
             f"➡️ Số tài khoản: 497720088\n"
             f"➡️ Ngân hàng: MB Bank\n"
             f"➡️ Số tiền: {amount} VNĐ\n"
             f"➡️ Nội dung chuyển khoản: NAP{code}\n\n"
             f"⏳ Sau khi chuyển khoản, admin sẽ duyệt và cộng {turns_to_add} lượt cho bạn.")

    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"📥 YÊU CẦU NẠP TIỀN\n"
                                   f"👤 User ID: {user_id}\n"
                                   f"💰 Số tiền: {amount} VNĐ\n"
                                   f"🎫 Lượt mua: {turns_to_add}\n"
                                   f"📝 Nội dung: NAP{code}\n\n"
                                   f"Duyệt bằng lệnh: /approve {user_id} {turns_to_add}")

    bot.reply_to(message, reply)

@bot.message_handler(commands=['approve'])
def approve_nap(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    parts = message.text.split()
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        bot.reply_to(message, "❌ Sai cú pháp. Dùng /approve <user_id> <số lượt>")
        return

    uid = int(parts[1])
    turns = int(parts[2])
    user_turns[uid] = user_turns.get(uid, 0) + turns

    save_data()
    bot.send_message(uid, f"✅ Bạn đã được cộng {turns} lượt dùng!\n🎯 Dùng lệnh /tx <md5> để dự đoán.")
    bot.reply_to(message, f"Đã cộng {turns} lượt cho user {uid}.")

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
                                   f"Duyệt bằng lệnh: /approve {user_id} <số lượt>")

    bot.reply_to(message, f"⏳ Đang chờ admin duyệt giao dịch.\n"
                          f"Sau khi admin duyệt, bạn sẽ nhận được lượt dùng.\n"
                          f"💰 Số tiền: {amount} VNĐ\n"
                          f"📝 Nội dung: {content}")

@bot.message_handler(commands=['support'])
def handle_support(message):
    bot.reply_to(message, "📩 Nếu bạn cần hỗ trợ, vui lòng liên hệ với admin tại: @cskhtool88")

@bot.message_handler(commands=['moiban'])
def handle_moiban(message):
    user_id = message.from_user.id
    referral_link = f"https://t.me/your_bot_username?start={user_id}" # Thay 'your_bot_username' bằng username của bot bạn
    bot.reply_to(message, f"🔗 Đây là link giới thiệu của bạn:\n`{referral_link}`\n\n"
                          "Mỗi khi có người mới sử dụng link này và nhấn /start, bạn sẽ được cộng thêm 1 lượt dùng!")

bot.polling()

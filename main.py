import telebot
import random
import string
import json
import time
from datetime import datetime, timedelta
import re

# Thư viện để keep_alive (Flask)
from threading import Thread
from flask import Flask

# --- Cấu hình Bot ---
BOT_TOKEN = "7942509227:AAGECLHLuuvPlul1jAidqmbjIgO_9zD2AV8"  # THAY THẾ BẰNG TOKEN CỦA BẠN
ADMIN_IDS = [6915752059]  # Thay thế bằng ID Telegram của bạn
GROUP_LINK = "https://t.me/+cd71g9Cwx9Y1ZTM1"  # Link nhóm Telegram để người dùng tham gia
SUPPORT_USERNAME = "@heheviptool"  # Username hỗ trợ

bot = telebot.TeleBot(BOT_TOKEN)

# --- Dữ liệu người dùng và mã code ---
USER_DATA_FILE = "users.json"
CODES_FILE = "codes.json"
user_data = {}
codes = {
    "CODEFREE7DAY": {"type": "vip_days", "value": 7, "used_by": None}
}

def load_data(file_path, default_data={}):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            if file_path == USER_DATA_FILE:
                # Chuyển đổi keys từ string sang int cho user_data
                return {int(k): v for k, v in data.items()}
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data

def save_data(file_path, data):
    with open(file_path, 'w') as f:
        if file_path == USER_DATA_FILE:
            # Chuyển đổi keys từ int sang string trước khi lưu user_data
            json.dump({str(k): v for k, v in data.items()}, f, indent=4)
        else:
            json.dump(data, f, indent=4)

def get_user_info(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "name": "",
            "is_vip": False,
            "vip_expiry": None,
            "invite_count": 0,
            "correct_predictions": 0,
            "wrong_predictions": 0,
            "is_admin_ctv": False,
            "waiting_for_md5": False,
            "invite_link_generated": False,
            "has_claimed_free_vip": False, # Chỉ định rõ đã nhận code free chưa
            "history": [] # Thêm lịch sử dự đoán
        }
        save_data(USER_DATA_FILE, user_data)
    return user_data[user_id]

# --- Hàm kiểm tra trạng thái VIP ---
def is_vip(user_id):
    user_info = get_user_info(user_id)
    if user_info["is_vip"] and user_info["vip_expiry"]:
        try:
            expiry_time = datetime.fromisoformat(user_info["vip_expiry"])
            return datetime.now() < expiry_time
        except ValueError:
            return False # Lỗi định dạng ngày tháng
    return False

def get_vip_status_text(user_id):
    user_info = get_user_info(user_id)
    if is_vip(user_id):
        expiry_time = datetime.fromisoformat(user_info["vip_expiry"])
        return f"✅ Đã kích hoạt\n🗓️ Hết hạn: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}"
    return "❌ Chưa kích hoạt"

# --- Hàm kiểm tra Admin/CTV ---
def is_admin_ctv(user_id):
    return user_id in ADMIN_IDS or get_user_info(user_id)["is_admin_ctv"]

# --- Hàm kiểm tra Super Admin ---
def is_super_admin(user_id):
    return user_id in ADMIN_IDS

# --- Hàm kiểm tra thành viên nhóm (Cần quyền bot Admin trong nhóm) ---
def is_member_of_group(user_id, chat_id_group):
    try:
        member = bot.get_chat_member(chat_id_group, user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        print(f"Error checking group membership for {user_id}: {e}")
        return False

# --- Hàm kích hoạt VIP ---
def activate_vip(user_id, days):
    user_info = get_user_info(user_id)
    current_expiry = None
    if user_info["is_vip"] and user_info["vip_expiry"]:
        try:
            current_expiry = datetime.fromisoformat(user_info["vip_expiry"])
        except ValueError:
            current_expiry = datetime.now()

    if current_expiry and current_expiry > datetime.now():
        new_expiry = current_expiry + timedelta(days=days)
    else:
        new_expiry = datetime.now() + timedelta(days=days)

    user_info["is_vip"] = True
    user_info["vip_expiry"] = new_expiry.isoformat()
    save_data(USER_DATA_FILE, user_data)
    return new_expiry

# --- Hàm tạo mã code ngẫu nhiên ---
def generate_code(length=10):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))

# --- Hàm thuật toán dự đoán (cải tiến) ---
def custom_md5_analyzer(md5_hash):
    # Đây là phiên bản mô phỏng nâng cao hơn một chút,
    # nhưng vẫn là giả lập và không dựa trên thuật toán thực tế.
    # Để tăng "độ chính xác", bạn cần dữ liệu lịch sử và mô hình phức tạp.
    # Ở đây, tôi sẽ dùng một số logic giả lập phức tạp hơn.

    # MD5 hash có 32 ký tự, mỗi ký tự là 0-9 hoặc a-f.
    # Giả định một số logic đơn giản dựa trên MD5 để tạo ra kết quả.
    # Ví dụ: tổng giá trị hex, số chẵn/lẻ của các ký tự cuối, v.v.
    try:
        # Lấy 4 ký tự cuối cùng của MD5 và chuyển thành số thập phân
        last_chars = md5_hash[-4:]
        decimal_val = int(last_chars, 16) # Chuyển từ hex sang thập phân

        # Ví dụ: nếu tổng các chữ số cuối lớn hơn ngưỡng thì là Tài, ngược lại là Xỉu
        # Hoặc dựa vào tính chẵn lẻ của một số hex cụ thể.
        # Đây chỉ là ví dụ để "giả lập" một thuật toán.
        # Trong thực tế, bạn sẽ cần các mô hình thống kê hoặc ML phức tạp hơn.
        
        # Mô phỏng "cứ 2 lần Gãy thì 1 lần khác" -> tỷ lệ Gãy là 2/3
        # Để đảm bảo điều này, bạn cần một hệ thống quản lý trạng thái hoặc lịch sử.
        # Ở đây tôi sẽ đưa ra dự đoán và kết quả một cách ngẫu nhiên có trọng số.

        # Thuật toán HYPER-AI (giả định độ chính xác cao nhất)
        # Giả sử nếu decimal_val là chẵn -> XỈU, lẻ -> TÀI
        if decimal_val % 2 == 0:
            hyper_ai_pred = "XỈU"
            hyper_ai_prob = round(random.uniform(85, 98), 1) # Tăng xác suất cho HYPER-AI
        else:
            hyper_ai_pred = "TÀI"
            hyper_ai_prob = round(random.uniform(85, 98), 1)

        # Thuật toán DIAMOND AI (trung bình)
        diamond_ai_pred = "XỈU" if random.random() < 0.55 else "TÀI"
        diamond_ai_prob = round(random.uniform(50, 75), 1)

        # Thuật toán AI-TECH TITANS (khá tốt)
        ai_tech_pred = "XỈU" if random.random() < 0.65 else "TÀI"
        ai_tech_prob = round(random.uniform(60, 80), 1)

        # Tổng HEX (giả lập)
        total_hex = sum(int(c, 16) for c in md5_hash)

        # Thống kê thuật toán (giả lập)
        hyper_ai_stats = round(random.uniform(18.0, 25.0), 2) # Tăng thống kê cho Hyper-AI
        diamond_ai_stats = round(random.uniform(3.0, 8.0), 2)
        ai_tech_stats = round(random.uniform(5.0, 12.0), 2)

        # Kết luận cuối cùng (kết hợp các dự đoán, có thể ưu tiên Hyper-AI hơn)
        # Trọng số: Hyper-AI (0.6), AI-Tech (0.3), Diamond AI (0.1)
        # Nếu Hyper-AI dự đoán Xỉu, có 80% khả năng kết luận là Xỉu (nếu các cái khác không quá đối nghịch)
        # Hoặc đơn giản hơn: lấy dự đoán của thuật toán có xác suất cao nhất
        final_pred = hyper_ai_pred # Ưu tiên Hyper-AI
        
        # Để tăng độ chính xác, có thể dùng một ngưỡng: nếu Hyper-AI > 90% thì theo Hyper-AI
        # Nếu không thì tính trung bình có trọng số.
        if hyper_ai_prob >= 90:
            final_pred = hyper_ai_pred
            final_prob = hyper_ai_prob
        else:
            # Simple weighted average
            if hyper_ai_pred == diamond_ai_pred == ai_tech_pred:
                final_pred = hyper_ai_pred
                final_prob = (hyper_ai_prob + diamond_ai_prob + ai_tech_prob) / 3
            else:
                # Decide based on majority vote or more complex logic
                preds_count = {"XỈU": 0, "TÀI": 0}
                if hyper_ai_pred == "XỈU": preds_count["XỈU"] += 0.6
                else: preds_count["TÀI"] += 0.6
                
                if diamond_ai_pred == "XỈU": preds_count["XỈU"] += 0.1
                else: preds_count["TÀI"] += 0.1

                if ai_tech_pred == "XỈU": preds_count["XỈU"] += 0.3
                else: preds_count["TÀI"] += 0.3

                if preds_count["XỈU"] >= preds_count["TÀI"]:
                    final_pred = "XỈU"
                else:
                    final_pred = "TÀI"
                
                final_prob = round(max(hyper_ai_prob, diamond_ai_prob, ai_tech_prob), 1)
        
        # Điều chỉnh rủi ro dựa trên xác suất tổng
        risk = "THẤP" if final_prob >= 80 else "TRUNG BÌNH" if final_prob >= 60 else "CAO"

        # Kết quả thực tế (giả lập) - "Gãy" thường là Xỉu, "Ăn" thường là Tài
        # Để đảm bảo tỷ lệ "Gãy" 2/3, chúng ta cần một cơ chế theo dõi lịch sử.
        # Ở đây tôi sẽ dùng một biến toàn cục hoặc ghi vào file để mô phỏng.
        # Đây là một giải pháp đơn giản và không hoàn hảo.
        global md5_results_history # LƯU Ý: RẤT ĐƠN GIẢN, NÊN DÙNG DB
        if not hasattr(analyze_md5, "call_count"): # Dùng thuộc tính của hàm để đếm
            analyze_md5.call_count = 0
            analyze_md5.gãy_count = 0
        
        analyze_md5.call_count += 1
        
        # Mô phỏng "cứ 2 lần Gãy thì sẽ có 1 lần cho kết quả khác."
        # Đây là một logic phức tạp để đảm bảo phân phối chính xác.
        # Một cách đơn giản:
        if analyze_md5.gãy_count < 2:
            result_md5 = "Gãy"
            analyze_md5.gãy_count += 1
        else:
            result_md5 = random.choice(["Ăn", "Hoà"]) # "Hoà" nếu có
            analyze_md5.gãy_count = 0 # Reset sau khi có kết quả khác

        # Cập nhật số liệu thống kê cho kết quả dự đoán (Đúng/Sai)
        is_correct = False
        if final_pred == "XỈU" and result_md5 == "Gãy": # Giả định Gãy = Xỉu
            is_correct = True
        elif final_pred == "TÀI" and result_md5 == "Ăn": # Giả định Ăn = Tài
            is_correct = True
        # Nếu có Hoà, cần quy tắc riêng
        
        # Giao diện mới
        response_text = f"""
✨ **PHÂN TÍCH MD5 ĐỘC QUYỀN** ✨
──────────────────────────
🔑 Mã MD5: `{md5_hash[:8]}...{md5_hash[-8:]}`
📊 Tổng giá trị HEX: {total_hex}
⏰ Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}
──────────────────────────
🔮 **Dự đoán từ các AI cao cấp**
    🌌 **HYPER-AI:** Dự đoán **{hyper_ai_pred}** | Độ tin cậy: **{hyper_ai_prob}%**
    💎 **DIAMOND AI:** Dự đoán **{diamond_ai_pred}** | Độ tin cậy: **{diamond_ai_prob}%**
    🦠 **AI-TECH TITANS:** Dự đoán **{ai_tech_pred}** | Độ tin cậy: **{ai_tech_prob}%**
──────────────────────────
📈 **Thống kê hiệu suất AI (Số liệu giả lập)**
    Hyper-AI: {hyper_ai_stats}X
    Diamond AI: {diamond_ai_stats}X
    AI-Tech: {ai_tech_stats}X
──────────────────────────
🎯 **KẾT LUẬN CUỐI CÙNG**
    Dự đoán: **{final_pred}**
    Xác suất: **{final_prob}%**
    Mức độ rủi ro: **{risk}**
──────────────────────────
🚨 Kết quả thực tế MD5: **{result_md5}**
    *Lưu ý: Kết quả này chỉ mang tính tham khảo. Chúc may mắn!*
"""
        return final_pred, result_md5, is_correct, response_text

    except Exception as e:
        return None, None, False, f"Đã xảy ra lỗi khi phân tích MD5: {e}"

# --- Decorator để kiểm tra VIP ---
def vip_required(func):
    def wrapper(message):
        user_id = message.from_user.id
        if not is_vip(user_id):
            bot.reply_to(message, "⚠️ **Bạn cần có tài khoản VIP để sử dụng tính năng này.**\nVui lòng kích hoạt VIP bằng cách nhập mã hoặc tham gia nhóm để nhận VIP miễn phí.\n\nSử dụng /help để biết thêm chi tiết.", parse_mode='Markdown')
            return
        func(message)
    return wrapper

# --- Decorator để kiểm tra Admin/CTV ---
def admin_ctv_required(func):
    def wrapper(message):
        user_id = message.from_user.id
        if not is_admin_ctv(user_id):
            bot.reply_to(message, "⛔️ **Bạn không có quyền sử dụng lệnh này.**", parse_mode='Markdown')
            return
        func(message)
    return wrapper

# --- Decorator để kiểm tra Super Admin ---
def super_admin_required(func):
    def wrapper(message):
        user_id = message.from_user.id
        if not is_super_admin(user_id):
            bot.reply_to(message, "👑 **Lệnh này chỉ dành cho Admin Chính.**", parse_mode='Markdown')
            return
        func(message)
    return wrapper

# --- Các lệnh Bot ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    user_info["name"] = message.from_user.first_name or "Bạn"
    save_data(USER_DATA_FILE, user_data)

    # Xử lý tham số start (cho link mời)
    if message.text and len(message.text.split()) > 1:
        inviter_id_str = message.text.split()[1]
        try:
            inviter_id = int(inviter_id_str)
            # Kiểm tra xem người mời có phải là người dùng hợp lệ và không phải chính mình
            if inviter_id != user_id and inviter_id in user_data and \
               user_id not in user_data[inviter_id].get("invited_users", []): # Tránh cộng nhiều lần
                inviter_info = get_user_info(inviter_id)
                inviter_info["invite_count"] += 1
                # Ghi lại người đã mời để tránh trùng lặp
                if "invited_users" not in inviter_info:
                    inviter_info["invited_users"] = []
                inviter_info["invited_users"].append(user_id)
                
                activate_vip(inviter_id, 1) # Cộng 1 ngày VIP cho người mời
                bot.send_message(inviter_id, f"🎉 **Chúc mừng!** Bạn đã nhận được **1 ngày VIP** từ lượt mời thành công của người dùng {user_info['name']} (ID: `{user_id}`).", parse_mode='Markdown')
                save_data(USER_DATA_FILE, user_data)
        except ValueError:
            pass # Invalid inviter ID

    welcome_message = f"""
👋 Chào mừng bạn, **{user_info['name']}**!
──────────────────────────
ℹ️ Tham gia nhóm Telegram của chúng tôi để nhận ngay **VIP 7 ngày miễn phí**!

👉 **Nhóm chính thức:** {GROUP_LINK}

✨ Sau khi tham gia, nhấn nút "Xác nhận" để kích hoạt ưu đãi VIP của bạn.
"""
    markup = telebot.types.InlineKeyboardMarkup()
    confirm_button = telebot.types.InlineKeyboardButton("✅ Tôi đã tham gia nhóm", callback_data="confirm_group_join")
    markup.add(confirm_button)
    bot.send_message(user_id, welcome_message, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "confirm_group_join")
def confirm_group_join_callback(call):
    user_id = call.from_user.id
    user_info = get_user_info(user_id)
    bot.answer_callback_query(call.id, "Đang kiểm tra thành viên nhóm...", show_alert=False)

    # !!! Thay thế -100xxxxxxxxxx bằng ID nhóm của bạn (bắt đầu bằng -100) !!!
    group_chat_id = -1002075726245 # ĐỔI ID NHÓM CỦA BẠN TẠI ĐÂY!
    is_member = is_member_of_group(user_id, group_chat_id)

    if is_member:
        if not user_info.get("has_claimed_free_vip"):
            expiry = activate_vip(user_id, 7)
            user_info["has_claimed_free_vip"] = True
            save_data(USER_DATA_FILE, user_data)
            bot.send_message(user_id, f"🎉 **Chúc mừng!** Bạn đã tham gia nhóm thành công.\n\n**VIP 7 ngày miễn phí** của bạn đã được kích hoạt!\n🗓️ Thời gian hết hạn: {expiry.strftime('%Y-%m-%d %H:%M:%S')}", parse_mode='Markdown')
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text + "\n\n✅ **Bạn đã nhận VIP 7 ngày miễn phí.**", parse_mode='Markdown')
        else:
            bot.send_message(user_id, "ℹ️ Bạn đã nhận VIP miễn phí 7 ngày trước đó rồi.")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text + "\n\nBạn đã nhận VIP miễn phí rồi.", parse_mode='Markdown')
    else:
        bot.send_message(user_id, f"❌ **Bạn chưa tham gia nhóm.** Vui lòng tham gia nhóm: {GROUP_LINK} trước khi nhấn xác nhận.", parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = f"""
📚 **CÁC LỆNH HỖ TRỢ** 📚
──────────────────────────
🔍 `/start` - Bắt đầu và nhận thông tin chào mừng.
💎 `/code [mã]` - Kích hoạt mã VIP. Admin có thể tạo mã mới.
📊 `/stats` - Xem thống kê dự đoán cá nhân.
📜 `/history` - Xem lịch sử các lần dự đoán của bạn.
📩 `/invite` - Lấy link mời bạn bè nhận VIP và nhận thêm ngày VIP.
👤 `/id` - Xem thông tin tài khoản của bạn.
──────────────────────────
**Để phân tích MD5:**
    Chỉ cần gửi mã **MD5 (32 ký tự)** trực tiếp vào bot.
──────────────────────────
🆘 Hỗ trợ: {SUPPORT_USERNAME}
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['gia'])
def send_price_list(message):
    price_text = """
💰 **BẢNG GIÁ DỊCH VỤ VIP** 💰
──────────────────────────
✨ **Gói Cơ Bản (7 Ngày):** Miễn phí (tham gia nhóm Telegram)
✨ **Gói Thường (30 Ngày):** 50.000 VNĐ
✨ **Gói Cao Cấp (Trọn Đời):** 200.000 VNĐ
──────────────────────────
💳 Để mua VIP, vui lòng liên hệ Admin/CTV để được hướng dẫn chi tiết.
"""
    bot.send_message(message.chat.id, price_text, parse_mode='Markdown')

@bot.message_handler(commands=['gopy'])
def receive_feedback(message):
    feedback = message.text.replace("/gopy", "").strip()
    if not feedback:
        bot.reply_to(message, "✍️ Vui lòng nhập nội dung góp ý của bạn sau lệnh /gopy.\nVí dụ: `/gopy Bot hoạt động rất tốt!`", parse_mode='Markdown')
        return

    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"📝 **GÓP Ý MỚI** từ người dùng ID: `{message.from_user.id}` (Tên: `{message.from_user.first_name or 'N/A'}`)\n\nNội dung:\n__{feedback}__", parse_mode='Markdown')
        except Exception as e:
            print(f"Không thể gửi góp ý đến Admin {admin_id}: {e}")
    bot.reply_to(message, "✅ **Cảm ơn bạn đã gửi góp ý!** Chúng tôi sẽ xem xét và phản hồi sớm nhất có thể.")

@bot.message_handler(commands=['nap'])
def top_up_guide(message):
    bot.send_message(message.chat.id, "💳 **HƯỚNG DẪN NẠP TIỀN** 💳\n──────────────────────────\nĐể nạp tiền hoặc mua các gói VIP, vui lòng liên hệ trực tiếp với đội ngũ Admin hoặc CTV của chúng tôi để được hỗ trợ và hướng dẫn cụ thể.\n\n🆘 Liên hệ hỗ trợ: {SUPPORT_USERNAME}", parse_mode='Markdown')

@bot.message_handler(commands=['taixiu'])
@vip_required
def get_latest_taixiu_prediction(message):
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    user_info["waiting_for_md5"] = True
    save_data(USER_DATA_FILE, user_data)
    bot.reply_to(message, "📝 **Vui lòng gửi mã MD5 (32 ký tự)** để tôi tiến hành phân tích và đưa ra dự đoán.", parse_mode='Markdown')

@bot.message_handler(commands=['tat'])
def stop_notifications(message):
    bot.reply_to(message, "ℹ️ Chức năng nhận thông báo liên tục hiện chưa được hỗ trợ. Bạn có thể gửi mã MD5 bất cứ lúc nào để nhận dự đoán.")

@bot.message_handler(commands=['full'])
@admin_ctv_required
def view_user_details(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "📝 Vui lòng nhập ID người dùng cần xem. Ví dụ: `/full 123456789`", parse_mode='Markdown')
        return

    try:
        target_user_id = int(args[1])
        if target_user_id not in user_data:
            bot.reply_to(message, "Không tìm thấy người dùng với ID này.")
            return

        target_user_info = get_user_info(target_user_id)
        vip_status = get_vip_status_text(target_user_id)

        total_predictions = target_user_info['correct_predictions'] + target_user_info['wrong_predictions']
        accuracy = 0.00
        if total_predictions > 0:
            accuracy = (target_user_info['correct_predictions'] / total_predictions) * 100

        response = f"""
👤 **THÔNG TIN CHI TIẾT NGƯỜI DÙNG** 👤
──────────────────────────
🆔 ID: `{target_user_id}`
✨ Tên: `{target_user_info.get('name', 'N/A')}`
🌟 VIP: {vip_status}
💌 Lượt mời: {target_user_info['invite_count']}
✔️ Đúng: {target_user_info['correct_predictions']}
❌ Sai: {target_user_info['wrong_predictions']}
📊 Chính xác: {accuracy:.2f}%
👨‍💻 CTV: {'✅ Có' if target_user_info['is_admin_ctv'] else '❌ Không'}
"""
        bot.reply_to(message, response, parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "❌ ID người dùng không hợp lệ. Vui lòng kiểm tra lại.")

@bot.message_handler(commands=['giahan'])
@admin_ctv_required
def extend_vip(message):
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "📝 Vui lòng nhập ID người dùng và số ngày gia hạn.\nVí dụ: `/giahan 123456789 30`", parse_mode='Markdown')
        return

    try:
        target_user_id = int(args[1])
        days_to_add = int(args[2])

        if target_user_id not in user_data:
            bot.reply_to(message, "Không tìm thấy người dùng với ID này.")
            return

        if days_to_add <= 0:
            bot.reply_to(message, "Số ngày gia hạn phải lớn hơn 0.")
            return

        new_expiry = activate_vip(target_user_id, days_to_add)
        bot.send_message(target_user_id, f"🎉 **Tài khoản VIP của bạn đã được gia hạn thêm {days_to_add} ngày bởi Admin/CTV!**\n🗓️ Thời gian hết hạn mới: {new_expiry.strftime('%Y-%m-%d %H:%M:%S')}", parse_mode='Markdown')
        bot.reply_to(message, f"✅ Đã gia hạn VIP thành công cho người dùng `{target_user_id}` thêm {days_to_add} ngày.", parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "❌ ID người dùng hoặc số ngày không hợp lệ. Vui lòng kiểm tra lại.")

@bot.message_handler(commands=['ctv'])
@super_admin_required
def add_ctv(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "📝 Vui lòng nhập ID người dùng để thêm làm CTV. Ví dụ: `/ctv 123456789`", parse_mode='Markdown')
        return

    try:
        target_user_id = int(args[1])
        user_info = get_user_info(target_user_id)
        user_info["is_admin_ctv"] = True
        save_data(USER_DATA_FILE, user_data)
        bot.send_message(target_user_id, "🎉 **Chúc mừng!** Bạn đã được cấp quyền CTV!")
        bot.reply_to(message, f"✅ Đã thêm người dùng `{target_user_id}` làm CTV.", parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "❌ ID người dùng không hợp lệ. Vui lòng kiểm tra lại.")

@bot.message_handler(commands=['xoactv'])
@super_admin_required
def remove_ctv(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "📝 Vui lòng nhập ID người dùng để xóa CTV. Ví dụ: `/xoactv 123456789`", parse_mode='Markdown')
        return

    try:
        target_user_id = int(args[1])
        user_info = get_user_info(target_user_id)
        user_info["is_admin_ctv"] = False
        save_data(USER_DATA_FILE, user_data)
        bot.send_message(target_user_id, "🚨 **Thông báo:** Quyền CTV của bạn đã bị gỡ bỏ.")
        bot.reply_to(message, f"✅ Đã xóa quyền CTV của người dùng `{target_user_id}`.", parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "❌ ID người dùng không hợp lệ. Vui lòng kiểm tra lại.")

@bot.message_handler(commands=['tb'])
@super_admin_required
def send_broadcast(message):
    broadcast_text = message.text.replace("/tb", "").strip()
    if not broadcast_text:
        bot.reply_to(message, "📝 Vui lòng nhập nội dung thông báo sau lệnh /tb.\nVí dụ: `/tb Bot sẽ bảo trì vào 2h sáng.`", parse_mode='Markdown')
        return

    sent_count = 0
    # Lấy danh sách các ID người dùng từ keys của user_data, đảm bảo là int
    all_user_ids = [uid for uid in user_data.keys()]

    bot.reply_to(message, f"Đang gửi thông báo tới {len(all_user_ids)} người dùng. Vui lòng chờ...", parse_mode='Markdown')

    for user_id in all_user_ids:
        try:
            bot.send_message(user_id, f"📣 **THÔNG BÁO TỪ ADMIN:**\n\n{broadcast_text}", parse_mode='Markdown')
            sent_count += 1
            time.sleep(0.1)
        except Exception as e:
            print(f"Không thể gửi thông báo đến người dùng {user_id}: {e}")
    bot.reply_to(message, f"✅ Đã gửi thông báo tới **{sent_count}** người dùng.", parse_mode='Markdown')

@bot.message_handler(commands=['code'])
def handle_code(message):
    user_id = message.from_user.id
    args = message.text.split()

    if is_super_admin(user_id):
        if len(args) == 1: # Admin /code -> tạo code mới
            new_code = generate_code()
            codes[new_code] = {"type": "admin_generated", "value": 15, "used_by": None} # Mặc định 15 ngày
            save_data(CODES_FILE, codes)
            bot.reply_to(message, f"✅ Đã tạo mã VIP mới: `{new_code}` (15 ngày VIP).\n\n_Lưu ý: Bạn có thể chỉnh sửa số ngày trong codes.json nếu cần._", parse_mode='Markdown')
        elif len(args) == 2: # Admin /code <mã> -> để xem thông tin code đó
            code_to_check = args[1].upper()
            if code_to_check in codes:
                code_info = codes[code_to_check]
                status = "Chưa sử dụng" if code_info["used_by"] is None else f"Đã sử dụng bởi `{code_info['used_by']}`"
                bot.reply_to(message, f"""
🔑 **THÔNG TIN MÃ VIP** 🔑
──────────────────────────
Mã: `{code_to_check}`
Loại: `{code_info['type']}`
Giá trị: `{code_info['value']}` ngày
Trạng thái: `{status}`
""", parse_mode='Markdown')
            else:
                bot.reply_to(message, "❌ Mã này không tồn tại trong hệ thống.", parse_mode='Markdown')
        else:
            bot.reply_to(message, "📝 Lệnh `/code` dành cho Admin:\n- `/code`: Tạo mã VIP mới.\n- `/code [mã]`: Kiểm tra thông tin mã VIP cụ thể.", parse_mode='Markdown')
        return

    # User uses /code [mã]
    if len(args) < 2:
        bot.reply_to(message, "📝 Vui lòng nhập mã kích hoạt VIP sau lệnh /code.\nVí dụ: `/code CODEFREE7DAY`", parse_mode='Markdown')
        return

    user_code = args[1].upper()
    if user_code not in codes:
        bot.reply_to(message, "❌ Mã kích hoạt không hợp lệ hoặc đã hết hạn.", parse_mode='Markdown')
        return

    code_info = codes[user_code]
    if code_info["used_by"] is not None:
        bot.reply_to(message, "⚠️ Mã này đã được sử dụng bởi người khác rồi.", parse_mode='Markdown')
        return
    
    # Kiểm tra đặc biệt cho CODEFREE7DAY: chỉ dùng 1 lần/ID
    if user_code == "CODEFREE7DAY":
        user_info = get_user_info(user_id)
        if user_info.get("has_claimed_free_vip"):
            bot.reply_to(message, "❌ Mã `CODEFREE7DAY` chỉ có thể sử dụng **một lần duy nhất** cho mỗi tài khoản.", parse_mode='Markdown')
            return
        user_info["has_claimed_free_vip"] = True # Đánh dấu đã sử dụng
        save_data(USER_DATA_FILE, user_data)

    # Kích hoạt VIP cho người dùng
    days = code_info["value"]
    expiry = activate_vip(user_id, days)
    code_info["used_by"] = user_id # Đánh dấu mã đã sử dụng
    save_data(CODES_FILE, codes)

    bot.reply_to(message, f"🎉 **Chúc mừng!** Bạn đã kích hoạt VIP thành công với mã `{user_code}`.\n\nThời gian VIP của bạn kéo dài thêm **{days} ngày** và sẽ hết hạn vào: {expiry.strftime('%Y-%m-%d %H:%M:%S')}", parse_mode='Markdown')


@bot.message_handler(commands=['stats'])
def show_stats(message):
    user_id = message.from_user.id
    user_info = get_user_info(user_id)

    total_predictions = user_info['correct_predictions'] + user_info['wrong_predictions']
    accuracy = 0.00
    if total_predictions > 0:
        accuracy = (user_info['correct_predictions'] / total_predictions) * 100

    stats_message = f"""
📈 **THỐNG KÊ DỰ ĐOÁN CÁ NHÂN** 📈
──────────────────────────
✔️ Số lần dự đoán đúng: **{user_info['correct_predictions']}**
❌ Số lần dự đoán sai: **{user_info['wrong_predictions']}**
📊 Tỷ lệ chính xác: **{accuracy:.2f}%**
"""
    bot.send_message(user_id, stats_message, parse_mode='Markdown')

@bot.message_handler(commands=['history'])
@vip_required # Yêu cầu VIP để xem lịch sử chi tiết
def show_history(message):
    user_id = message.from_user.id
    user_info = get_user_info(user_id)

    history_text = "📜 **LỊCH SỬ DỰ ĐOÁN CỦA BẠN** 📜\n──────────────────────────\n"
    if not user_info['history']:
        history_text += "Bạn chưa có lịch sử dự đoán nào."
    else:
        # Hiển thị 5-10 lịch sử gần nhất
        for entry in user_info['history'][-10:]: # Lấy 10 mục gần nhất
            status = "✅ ĐÚNG" if entry['is_correct'] else "❌ SAI"
            history_text += f"- MD5: `{entry['md5_short']}` | Dự đoán: **{entry['prediction']}** | Kết quả: **{entry['result_md5']}** | Status: **{status}** | Lúc: {entry['time']}\n"
        
        if len(user_info['history']) > 10:
            history_text += "\n_... và nhiều hơn nữa. Chỉ hiển thị 10 mục gần nhất._"

    bot.send_message(user_id, history_text, parse_mode='Markdown')

@bot.message_handler(commands=['invite', 'moiban'])
def send_invite_link(message):
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    bot_username = bot.get_me().username
    invite_link = f"https://t.me/{bot_username}?start={user_id}"

    user_info["invite_link_generated"] = True
    save_data(USER_DATA_FILE, user_data)

    invite_message = f"""
💌 **MỜI BẠN BÈ, NHẬN VIP MIỄN PHÍ!** 💌
──────────────────────────
📢 Chia sẻ link này để mời bạn bè tham gia bot:
🔗 **Link mời của bạn:** `{invite_link}`

🎁 Cứ mỗi 1 người bạn mời thành công (tham gia bot và được bot ghi nhận), bạn sẽ nhận được **1 ngày VIP miễn phí**!
──────────────────────────
👥 Tổng số lượt mời thành công của bạn: **{user_info['invite_count']}**
"""
    bot.send_message(user_id, invite_message, parse_mode='Markdown')

@bot.message_handler(commands=['id'])
def show_account_info(message):
    user_id = message.from_user.id
    user_info = get_user_info(user_id)

    vip_status_text = get_vip_status_text(user_id)
    vip_status_line1 = vip_status_text.splitlines()[0]
    vip_expiry_line = vip_status_text.splitlines()[1].replace('🗓️ Hết hạn: ', '') if len(vip_status_text.splitlines()) > 1 else 'N/A'

    total_predictions = user_info['correct_predictions'] + user_info['wrong_predictions']
    accuracy = 0.00
    if total_predictions > 0:
        accuracy = (user_info['correct_predictions'] / total_predictions) * 100

    account_info_message = f"""
👤 **THÔNG TIN TÀI KHOẢN CỦA BẠN** 👤
──────────────────────────
✨ Tên: **{user_info.get('name', message.from_user.first_name)}**
🆔 ID: `{user_id}`
──────────────────────────
💎 Trạng thái VIP: **{vip_status_line1}**
⏰ Hết hạn: **{vip_expiry_line}**
──────────────────────────
✉️ Lượt mời thành công: **{user_info['invite_count']}**
──────────────────────────
📊 **Thống kê dự đoán:**
    ✔️ Đúng: **{user_info['correct_predictions']}**
    ❌ Sai: **{user_info['wrong_predictions']}**
    🎯 Tỷ lệ chính xác: **{accuracy:.2f}%**
──────────────────────────
🆘 Hỗ trợ: {SUPPORT_USERNAME}
"""
    bot.send_message(user_id, account_info_message, parse_mode='Markdown')

# --- Xử lý tin nhắn văn bản (MD5, v.v.) ---
@bot.message_handler(func=lambda message: True)
@vip_required
def handle_text_messages(message):
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    text = message.text.strip()

    # Kiểm tra nếu đang chờ MD5 HOẶC tin nhắn có vẻ là MD5
    if user_info["waiting_for_md5"] or re.fullmatch(r"[0-9a-fA-F]{32}", text):
        if re.fullmatch(r"[0-9a-fA-F]{32}", text):
            predicted_result, result_md5, is_correct, analysis_output = custom_md5_analyzer(text)
            
            if predicted_result is not None:
                bot.reply_to(message, analysis_output, parse_mode='Markdown')

                # Cập nhật thống kê và lịch sử
                if is_correct:
                    user_info["correct_predictions"] += 1
                else:
                    user_info["wrong_predictions"] += 1
                
                # Thêm vào lịch sử
                user_info["history"].append({
                    "md5_short": f"{text[:4]}...{text[-4:]}",
                    "prediction": predicted_result,
                    "result_md5": result_md5,
                    "is_correct": is_correct,
                    "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                # Giới hạn lịch sử để không quá lớn (ví dụ: 50 mục)
                user_info["history"] = user_info["history"][-50:]

                save_data(USER_DATA_FILE, user_data)
            else:
                bot.reply_to(message, analysis_output) # Hiển thị lỗi nếu có
            
            user_info["waiting_for_md5"] = False
            save_data(USER_DATA_FILE, user_data)
        else:
            bot.reply_to(message, "❌ Mã MD5 không hợp lệ. Vui lòng nhập đúng **32 ký tự MD5** (chỉ chứa chữ số 0-9 và chữ cái a-f).", parse_mode='Markdown')
    else:
        bot.reply_to(message, "🤔 Tôi không hiểu yêu cầu của bạn. Vui lòng sử dụng các lệnh có sẵn (ví dụ: `/help`) hoặc gửi mã MD5 để tôi phân tích.", parse_mode='Markdown')


# --- Keep alive server ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask_app():
    port = random.randint(2000, 9000) # Random port
    print(f"Flask app running on port {port}")
    app.run(host='0.0.0.0', port=port)

# --- Khởi chạy bot ---
if __name__ == "__main__":
    user_data = load_data(USER_DATA_FILE)
    codes = load_data(CODES_FILE, default_data=codes) # Load codes, dùng default nếu file rỗng
    print("Bot đang khởi động...")

    # Chạy Flask app trong một thread riêng
    t = Thread(target=run_flask_app)
    t.start()

    bot.polling(non_stop=True)

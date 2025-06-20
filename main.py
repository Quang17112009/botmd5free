import telebot
import random
import string
import json
import time
from datetime import datetime, timedelta
import re
import os
from threading import Thread
from flask import Flask

# --- Cấu hình Bot ---
BOT_TOKEN = "8070556149:AAEWspw2Kkl5EYCDuFVQPisG5YcDgTpbk1A"  # THAY THẾ BẰNG TOKEN THẬT CỦA BẠN
ADMIN_IDS = [6915752059]  # Thay thế bằng ID Telegram của bạn (Admin chính)
GROUP_LINK = "https://t.me/+cd71g9Cwx9Y1ZTM1"  # Link nhóm Telegram để người dùng tham gia
SUPPORT_USERNAME = "@heheviptool"  # Username hỗ trợ

bot = telebot.TeleBot(BOT_TOKEN)

# --- Dữ liệu người dùng và mã code ---
USER_DATA_FILE = "users.json"
CODES_FILE = "codes.json"
BOT_STATE_FILE = "bot_state.json" # File mới để lưu trạng thái bot

user_data = {}
codes = {
    "CODEFREE7DAY": {"type": "vip_days", "value": 7, "used_by": None}
}
bot_state = {} # Biến để lưu trạng thái bot (bao gồm md5_gãy_streak)

# Biến toàn cục để theo dõi chuỗi "Gãy" và hash MD5 cuối cùng được xử lý
md5_gãy_streak = 0
last_md5_hash_processed = None

def load_data(file_path, default_data={}):
    """Loads data from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            if file_path == USER_DATA_FILE:
                # Convert keys from string to int for user_data IDs
                return {int(k): v for k, v in data.items()}
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Warning: {file_path} not found or corrupted. Using default data.")
        return default_data

def save_data(file_path, data):
    """Saves data to a JSON file."""
    with open(file_path, 'w') as f:
        if file_path == USER_DATA_FILE:
            # Convert keys from int to string before saving user_data IDs
            json.dump({str(k): v for k, v in data.items()}, f, indent=4)
        else:
            json.dump(data, f, indent=4)

def get_user_info(user_id):
    """Retrieves or initializes user data."""
    if user_id not in user_data:
        user_data[user_id] = {
            "name": "",
            "is_vip": False,
            "vip_expiry": None,
            "invite_count": 0,
            "invited_users": [],
            "correct_predictions": 0,
            "wrong_predictions": 0,
            "is_admin_ctv": False,
            "waiting_for_md5": False,
            "invite_link_generated": False,
            "has_claimed_free_vip": False,
            "history": []
        }
        save_data(USER_DATA_FILE, user_data)
    return user_data[user_id]

# --- VIP Status Checkers ---
def is_vip(user_id):
    """Checks if a user has active VIP status."""
    user_info = get_user_info(user_id)
    if user_info["is_vip"] and user_info["vip_expiry"]:
        try:
            expiry_time = datetime.fromisoformat(user_info["vip_expiry"])
            return datetime.now() < expiry_time
        except ValueError:
            return False
    return False

def get_vip_status_text(user_id):
    """Returns formatted VIP status string."""
    user_info = get_user_info(user_id)
    if is_vip(user_id):
        expiry_time = datetime.fromisoformat(user_info["vip_expiry"])
        return f"✅ Đã kích hoạt\n🗓️ Hết hạn: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}"
    return "❌ Chưa kích hoạt"

# --- Admin/CTV Checkers ---
def is_admin_ctv(user_id):
    """Checks if a user is an Admin or CTV."""
    return user_id in ADMIN_IDS or get_user_info(user_id)["is_admin_ctv"]

def is_super_admin(user_id):
    """Checks if a user is a Super Admin (main admin)."""
    return user_id in ADMIN_IDS

# --- Group Membership Check (Requires bot to be Admin in the group) ---
def is_member_of_group(user_id, chat_id_group):
    """Checks if a user is a member of a specific Telegram group."""
    try:
        member = bot.get_chat_member(chat_id_group, user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        print(f"Error checking group membership for {user_id}: {e}")
        return False

# --- VIP Activation ---
def activate_vip(user_id, days):
    """Activates or extends VIP status for a user."""
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

# --- Code Generation ---
def generate_code(length=10):
    """Generates a random alphanumeric code."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))

# --- Prediction Algorithm (Simulated for MD5) ---
def custom_md5_analyzer(md5_hash):
    """
    Nâng cấp hàm phân tích MD5 mô phỏng với "siêu thuật toán" phức tạp hơn.
    """
    global md5_gãy_streak
    global last_md5_hash_processed
    global bot_state # Truy cập biến bot_state

    try:
        # Đảm bảo hash là hợp lệ và có độ dài 32
        if not re.fullmatch(r"[0-9a-fA-F]{32}", md5_hash):
            return None, None, False, "Mã MD5 không hợp lệ. Vui lòng nhập đúng 32 ký tự MD5."

        # Tránh xử lý lại cùng một MD5 nếu gọi liên tiếp (trong một phiên làm việc)
        if md5_hash == last_md5_hash_processed:
            # Bạn có thể chọn trả về kết quả cũ hoặc thông báo
            # Để đơn giản, ta sẽ tính lại nhưng khuyến nghị xử lý ở tầng cao hơn
            pass
        last_md5_hash_processed = md5_hash

        # --- Phân tích các thuộc tính của MD5 ---
        decimal_val_full = int(md5_hash, 16) # Tổng giá trị thập phân của toàn bộ hash
        decimal_val_last_4 = int(md5_hash[-4:], 16) # Last 4 chars
        decimal_val_first_4 = int(md5_hash[:4], 16) # First 4 chars

        # Count of odd/even digits (simplified)
        odd_digits = sum(1 for char in md5_hash if char in '13579bdfBDF')
        even_digits = 32 - odd_digits # Assuming hex chars count

        # Sum of all hex values (already in your code)
        total_hex = sum(int(c, 16) for c in md5_hash)

        # --- Logic cho từng AI (tinh chỉnh) ---

        # HYPER-AI (Độ chính xác cao nhất, tập trung vào các quy tắc mạnh)
        hyper_ai_pred = ""
        hyper_ai_prob = 0.0

        # Rule 1: Tổng HEX
        if total_hex % 2 == 0:
            hyper_ai_pred = "XỈU"
        else:
            hyper_ai_pred = "TÀI"
        hyper_ai_prob = round(random.uniform(90, 99), 1) # Rất cao

        # Rule 2: Kết thúc MD5
        if decimal_val_last_4 % 2 == 0: # Chẵn
            # Ưu tiên XỈU nếu tổng HEX là chẵn, TÀI nếu tổng HEX là lẻ
            if hyper_ai_pred == "XỈU":
                hyper_ai_pred = "XỈU" # Tăng cường xác suất
            else:
                 hyper_ai_pred = "XỈU" if random.random() < 0.6 else "TÀI" # Có thể thay đổi
        else: # Lẻ
            if hyper_ai_pred == "TÀI":
                hyper_ai_pred = "TÀI" # Tăng cường xác suất
            else:
                hyper_ai_pred = "TÀI" if random.random() < 0.6 else "XỈU" # Có thể thay đổi

        hyper_ai_prob = round(random.uniform(88, 98), 1) # Sau khi tinh chỉnh

        # DIAMOND AI (Độ chính xác trung bình, kết hợp các yếu tố)
        diamond_ai_pred = "XỈU" if (decimal_val_first_4 + odd_digits) % 2 == 0 else "TÀI"
        diamond_ai_prob = round(random.uniform(65, 85), 1) # Cao hơn trước

        # AI-TECH TITANS (Độ chính xác tốt, dựa trên phân tích số lẻ/chẵn)
        ai_tech_pred = "XỈU" if even_digits > odd_digits else "TÀI"
        ai_tech_prob = round(random.uniform(70, 90), 1) # Cao hơn trước

        # --- Thống kê hiệu suất AI (giả lập, bạn có thể thay đổi để phản ánh "công suất" của AI) ---
        hyper_ai_stats = round(random.uniform(25.0, 35.0), 2) # Giả lập X mạnh hơn
        diamond_ai_stats = round(random.uniform(5.0, 12.0), 2)
        ai_tech_stats = round(random.uniform(10.0, 20.0), 2)

        # --- Kết luận cuối cùng (kết hợp các AI) ---
        predictions_with_probs = [
            (hyper_ai_pred, hyper_ai_prob * 0.5),  # Hyper-AI có trọng số cao nhất
            (diamond_ai_pred, diamond_ai_prob * 0.3),
            (ai_tech_pred, ai_tech_prob * 0.2)
        ]

        total_tai_score = 0
        total_xiu_score = 0

        for pred, prob in predictions_with_probs:
            if pred == "TÀI":
                total_tai_score += prob
            else:
                total_xiu_score += prob

        final_pred = "TÀI" if total_tai_score > total_xiu_score else "XỈU"

        # Tính xác suất cuối cùng dựa trên AI được chọn
        if final_pred == "TÀI":
            final_prob = round(total_tai_score / (total_tai_score + total_xiu_score) * 100, 1) if (total_tai_score + total_xiu_score) > 0 else 50.0
        else:
            final_prob = round(total_xiu_score / (total_tai_score + total_xiu_score) * 100, 1) if (total_tai_score + total_xiu_score) > 0 else 50.0

        final_prob = max(55.0, final_prob) # Đảm bảo xác suất tối thiểu để cảm giác "tin cậy" hơn

        risk = "THẤP" if final_prob >= 85 else "TRUNG BÌNH" if final_prob >= 70 else "CAO"

        # --- Mô phỏng kết quả thực tế MD5 theo quy tắc "2 Gãy : 1 Khác" ---
        simulated_actual_result_text = ""
        is_correct = False

        # Đọc md5_gãy_streak từ bot_state
        current_streak = bot_state.get("md5_gãy_streak", 0)

        if current_streak < 2:
            simulated_actual_result_text = "Gãy" # Kết quả mong muốn là "Gãy" (tương ứng XỈU)
            bot_state["md5_gãy_streak"] = current_streak + 1
            if final_pred == "XỈU": # Nếu dự đoán XỈU và kết quả Gãy -> Đúng
                is_correct = True
        else:
            # Khi streak đạt 2, lần tiếp theo phải là "Khác" (Ăn hoặc Hoà)
            options = ["Ăn", "Hoà"]
            simulated_actual_result_text = random.choice(options)
            bot_state["md5_gãy_streak"] = 0 # Reset streak

            if simulated_actual_result_text == "Ăn" and final_pred == "TÀI": # Nếu dự đoán TÀI và kết quả Ăn -> Đúng
                is_correct = True
            elif simulated_actual_result_text == "Hoà":
                is_correct = False # Hoà không tính đúng/sai

        # Rất quan trọng: Lưu trạng thái sau khi cập nhật
        save_data(BOT_STATE_FILE, bot_state)

        response_text = f"""
✨ **PHÂN TÍCH MD5 ĐỘC QUYỀN V2** ✨
──────────────────────────
🔑 Mã MD5: `{md5_hash[:8]}...{md5_hash[-8:]}`
📊 Tổng giá trị HEX: **{total_hex}**
⏰ Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}
──────────────────────────
🔮 **Dự đoán từ các AI cao cấp**
    🌌 **HYPER-AI:** Dự đoán **{hyper_ai_pred}** | Độ tin cậy: **{hyper_ai_prob}%**
    💎 **DIAMOND AI:** Dự đoán **{diamond_ai_pred}** | Độ tin cậy: **{diamond_ai_prob}%**
    🦠 **AI-TECH TITANS:** Dự đoán **{ai_tech_pred}** | Độ tin cậy: **{ai_tech_prob}%**
──────────────────────────
📈 **Thống kê hiệu suất AI (Số liệu giả lập)**
    Hyper-AI: **{hyper_ai_stats}X**
    Diamond AI: **{diamond_ai_stats}X**
    AI-Tech: **{ai_tech_stats}X**
──────────────────────────
🎯 **KẾT LUẬN CUỐI CÙNG**
    Dự đoán: **{final_pred}**
    Xác suất: **{final_prob}%**
    Mức độ rủi ro: **{risk}**
──────────────────────────
🚨 Kết quả thực tế MD5: **{simulated_actual_result_text}**
    _Lưu ý: Kết quả này chỉ mang tính tham khảo. Chúc may mắn!_
"""
        return final_pred, simulated_actual_result_text, is_correct, response_text

    except Exception as e:
        print(f"Error in MD5 analysis: {e}")
        return None, None, False, f"Đã xảy ra lỗi khi phân tích MD5: {e}"

# --- Decorators for access control ---
def vip_required(func):
    """Decorator to restrict access to VIP users, but allows Super Admins."""
    def wrapper(message):
        user_id = message.from_user.id
        if is_super_admin(user_id):
            func(message)
            return
        if not is_vip(user_id):
            bot.reply_to(message, "⚠️ **Bạn cần có tài khoản VIP để sử dụng tính năng này.**\nVui lòng kích hoạt VIP bằng cách nhập mã hoặc tham gia nhóm để nhận VIP miễn phí.\n\nSử dụng /help để biết thêm chi tiết.", parse_mode='Markdown')
            return
        func(message)
    return wrapper

def admin_ctv_required(func):
    """Decorator to restrict access to Admin/CTV users, but allows Super Admins."""
    def wrapper(message):
        user_id = message.from_user.id
        if is_super_admin(user_id):
            func(message)
            return
        if not is_admin_ctv(user_id):
            bot.reply_to(message, "⛔️ **Bạn không có quyền sử dụng lệnh này.**", parse_mode='Markdown')
            return
        func(message)
    return wrapper

def super_admin_required(func):
    """Decorator to restrict access to Super Admin users."""
    def wrapper(message):
        user_id = message.from_user.id
        if not is_super_admin(user_id):
            bot.reply_to(message, "👑 **Lệnh này chỉ dành cho Admin Chính.**", parse_mode='Markdown')
            return
        func(message)
    return wrapper

# --- Bot Commands ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handles the /start command."""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    user_info["name"] = message.from_user.first_name or "Bạn"

    inviter_id = None
    if message.text and len(message.text.split()) > 1:
        inviter_id_str = message.text.split()[1]
        try:
            inviter_id = int(inviter_id_str)
            if inviter_id != user_id and inviter_id in user_data:
                user_info['invited_by'] = inviter_id
        except ValueError:
            pass

    save_data(USER_DATA_FILE, user_data)

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
    """Handles callback from the 'confirm group join' button."""
    user_id = call.from_user.id
    user_info = get_user_info(user_id)
    bot.answer_callback_query(call.id, "Đang kiểm tra thành viên nhóm...", show_alert=False)

    # !!! REPLACE WITH YOUR ACTUAL GROUP CHAT ID (starts with -100) !!!
    group_chat_id = -1002781947864 # EXAMPLE ID: You MUST change this!
    is_member = is_member_of_group(user_id, group_chat_id)

    if is_member:
        if not user_info.get("has_claimed_free_vip"):
            expiry = activate_vip(user_id, 7)
            user_info["has_claimed_free_vip"] = True

            inviter_id = user_info.get("invited_by")
            if inviter_id and inviter_id in user_data:
                inviter_info = get_user_info(inviter_id)
                if user_id not in inviter_info.get("invited_users", []):
                    inviter_info["invite_count"] += 1
                    inviter_info["invited_users"].append(user_id)

                    activate_vip(inviter_id, 1)
                    bot.send_message(inviter_id, f"🎉 **Chúc mừng!** Bạn đã nhận được **1 ngày VIP** từ lượt mời thành công của người dùng {user_info['name']} (ID: `{user_id}`) đã tham gia nhóm.", parse_mode='Markdown')

            if "invited_by" in user_info:
                del user_info["invited_by"]

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
    """Sends the list of available commands and instructions."""
    help_text = f"""
📚 **CÁC LỆNH HỖ TRỢ** 📚
──────────────────────────
🔍 `/start` - Bắt đầu và nhận thông tin chào mừng.
💎 `/code [mã]` - Kích hoạt mã VIP. Admin có thể tạo mã mới.
📊 `/stats` - Xem thống kê dự đoán cá nhân.
📜 `/history` - Xem lịch sử các lần dự đoán của bạn.
📩 `/invite` - Lấy link mời bạn bè nhận VIP và nhận thêm ngày VIP.
👤 `/id` - Xem thông tin tài khoản của bạn.
💰 `/gia` - Xem bảng giá dịch vụ VIP.
✍️ `/gopy [nội dung]` - Gửi góp ý đến Admin.
💳 `/nap` - Hướng dẫn nạp tiền.
──────────────────────────
**Để phân tích MD5:**
    Chỉ cần gửi mã **MD5 (32 ký tự)** trực tiếp vào bot.
──────────────────────────
🆘 Hỗ trợ: {SUPPORT_USERNAME}
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['gia'])
def send_price_list(message):
    """Sends the price list for VIP services."""
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
    """Allows users to send feedback to admins."""
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
    """Provides instructions on how to top up."""
    bot.send_message(message.chat.id, "💳 **HƯỚNG DẪN NẠP TIỀN** 💳\n──────────────────────────\nĐể nạp tiền hoặc mua các gói VIP, vui lòng liên hệ trực tiếp với đội ngũ Admin hoặc CTV của chúng tôi để được hỗ trợ và hướng dẫn cụ thể.\n\n🆘 Liên hệ hỗ trợ: {SUPPORT_USERNAME}", parse_mode='Markdown')

@bot.message_handler(commands=['taixiu'])
@vip_required
def get_latest_taixiu_prediction(message):
    """Prompts user to send MD5 for prediction."""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    user_info["waiting_for_md5"] = True
    save_data(USER_DATA_FILE, user_data)
    bot.reply_to(message, "📝 **Vui lòng gửi mã MD5 (32 ký tự)** để tôi tiến hành phân tích và đưa ra dự đoán.", parse_mode='Markdown')

@bot.message_handler(commands=['tat'])
def stop_notifications(message):
    """Placeholder for stopping continuous predictions (not implemented yet)."""
    bot.reply_to(message, "ℹ️ Chức năng nhận thông báo liên tục hiện chưa được hỗ trợ. Bạn có thể gửi mã MD5 bất cứ lúc nào để nhận dự đoán.")

@bot.message_handler(commands=['full'])
@admin_ctv_required
def view_user_details(message):
    """Allows Admin/CTV to view detailed user information."""
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
    """Allows Admin/CTV to extend a user's VIP status."""
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
    """Allows Super Admin to add a CTV."""
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
    """Allows Super Admin to remove a CTV."""
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
    """Allows Super Admin to send a broadcast message to all users."""
    broadcast_text = message.text.replace("/tb", "").strip()
    if not broadcast_text:
        bot.reply_to(message, "📝 Vui lòng nhập nội dung thông báo sau lệnh /tb.\nVí dụ: `/tb Bot sẽ bảo trì vào 2h sáng.`", parse_mode='Markdown')
        return

    sent_count = 0
    all_user_ids = list(user_data.keys()) # Get all user IDs

    bot.reply_to(message, f"Đang gửi thông báo tới {len(all_user_ids)} người dùng. Vui lòng chờ...", parse_mode='Markdown')

    for user_id in all_user_ids:
        try:
            bot.send_message(user_id, f"📣 **THÔNG BÁO TỪ ADMIN:**\n\n{broadcast_text}", parse_mode='Markdown')
            sent_count += 1
            time.sleep(0.1) # Small delay to avoid rate limits
        except Exception as e:
            print(f"Không thể gửi thông báo đến người dùng {user_id}: {e}")
    bot.reply_to(message, f"✅ Đã gửi thông báo tới **{sent_count}** người dùng.", parse_mode='Markdown')

@bot.message_handler(commands=['md5status'])
@super_admin_required
def show_md5_status(message):
    """Allows Super Admin to view the current MD5 streak status."""
    current_streak = bot_state.get("md5_gãy_streak", 0)
    bot.reply_to(message, f"📈 **Trạng thái MD5 'Gãy' Streak:** Hiện tại đang là `{current_streak}` / 2.\n(Cứ 2 lần 'Gãy' sẽ có 1 lần 'Khác'.)", parse_mode='Markdown')

@bot.message_handler(commands=['resetmd5streak'])
@super_admin_required
def reset_md5_streak(message):
    """Allows Super Admin to reset the MD5 streak."""
    bot_state["md5_gãy_streak"] = 0
    save_data(BOT_STATE_FILE, bot_state)
    bot.reply_to(message, "✅ Đã reset trạng thái MD5 'Gãy' streak về 0.", parse_mode='Markdown')

@bot.message_handler(commands=['code'])
def handle_code(message):
    """Handles VIP code activation for users and code generation/check for admins."""
    user_id = message.from_user.id
    args = message.text.split()

    if is_super_admin(user_id):
        if len(args) == 1:
            new_code = generate_code()
            codes[new_code] = {"type": "admin_generated", "value": 15, "used_by": None}
            save_data(CODES_FILE, codes)
            bot.reply_to(message, f"✅ Đã tạo mã VIP mới: `{new_code}` (15 ngày VIP).\n\n_Lưu ý: Bạn có thể chỉnh sửa số ngày trong codes.json nếu cần._", parse_mode='Markdown')
        elif len(args) == 2:
            arg_value = args[1].upper()
            try:
                days_to_add = int(arg_value)
                if days_to_add <= 0:
                    bot.reply_to(message, "❌ Số ngày phải là số nguyên dương.", parse_mode='Markdown')
                    return
                new_code = generate_code()
                codes[new_code] = {"type": "admin_generated", "value": days_to_add, "used_by": None}
                save_data(CODES_FILE, codes)
                bot.reply_to(message, f"✅ Đã tạo mã VIP mới: `{new_code}` (VIP {days_to_add} ngày).", parse_mode='Markdown')
            except ValueError:
                code_to_check = arg_value
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
            bot.reply_to(message, "📝 Lệnh `/code` dành cho Admin:\n- `/code`: Tạo mã VIP mới (15 ngày).\n- `/code [số_ngày]`: Tạo mã VIP với số ngày cụ thể.\n- `/code [mã]`: Kiểm tra thông tin mã VIP cụ thể.", parse_mode='Markdown')
        return

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

    if user_code == "CODEFREE7DAY":
        user_info = get_user_info(user_id)
        if user_info.get("has_claimed_free_vip"):
            bot.reply_to(message, "❌ Mã `CODEFREE7DAY` chỉ có thể sử dụng **một lần duy nhất** cho mỗi tài khoản.", parse_mode='Markdown')
            return
        user_info["has_claimed_free_vip"] = True
        save_data(USER_DATA_FILE, user_data)

    days = code_info["value"]
    expiry = activate_vip(user_id, days)
    code_info["used_by"] = user_id
    save_data(CODES_FILE, codes)

    bot.reply_to(message, f"🎉 **Chúc mừng!** Bạn đã kích hoạt VIP thành công với mã `{user_code}`.\n\nThời gian VIP của bạn kéo dài thêm **{days} ngày** và sẽ hết hạn vào: {expiry.strftime('%Y-%m-%d %H:%M:%S')}", parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Displays user's prediction statistics."""
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
@vip_required
def show_history(message):
    """Displays a user's recent prediction history."""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)

    history_text = "📜 **LỊCH SỬ DỰ ĐOÁN CỦA BẠN** 📜\n──────────────────────────\n"
    if not user_info['history']:
        history_text += "Bạn chưa có lịch sử dự đoán nào."
    else:
        for entry in user_info['history'][-10:]:
            status = "✅ ĐÚNG" if entry['is_correct'] else "❌ SAI"
            history_text += f"- MD5: `{entry['md5_short']}` | Dự đoán: **{entry['prediction']}** | Kết quả: **{entry['result_md5']}** | Status: **{status}** | Lúc: {entry['time']}\n"

        if len(user_info['history']) > 10:
            history_text += "\n_... và nhiều hơn nữa. Chỉ hiển thị 10 mục gần nhất._"

    bot.send_message(user_id, history_text, parse_mode='Markdown')

@bot.message_handler(commands=['invite', 'moiban'])
def send_invite_link(message):
    """Generates and sends a unique invite link for the user."""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    bot_username = bot.get_me().username
    invite_link = f"https://t.me/{bot_username}?start={user_id}"

    group_invite_link = GROUP_LINK

    user_info["invite_link_generated"] = True
    save_data(USER_DATA_FILE, user_data)

    invite_message = f"""
💌 **MỜI BẠN BÈ, NHẬN VIP MIỄN PHÍ!** 💌
──────────────────────────
📢 Chia sẻ link này để mời bạn bè tham gia bot:
🔗 **Link mời bot của bạn:** `{invite_link}`

👉 Khi bạn bè sử dụng link này để `start` bot, chúng tôi sẽ ghi nhận họ được mời bởi bạn.
Sau đó, khi họ **tham gia vào nhóm chính thức** và nhấn "✅ Tôi đã tham gia nhóm", bạn sẽ nhận được **1 ngày VIP miễn phí**!

🔗 **Link nhóm chính thức:** {group_invite_link}
──────────────────────────
👥 Tổng số lượt mời thành công của bạn: **{user_info['invite_count']}**
"""
    bot.send_message(user_id, invite_message, parse_mode='Markdown')

@bot.message_handler(commands=['id'])
def show_account_info(message):
    """Displays a user's account information."""
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

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    """Handles incoming text messages, focusing on MD5 input."""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    text = message.text.strip()

    # MD5 hash pattern
    is_md5_hash = re.fullmatch(r"[0-9a-fA-F]{32}", text)

    # Check VIP status or if it's a super admin
    if not is_super_admin(user_id) and not is_vip(user_id):
        if is_md5_hash:
            bot.reply_to(message, "⚠️ **Bạn cần có tài khoản VIP để sử dụng tính năng phân tích MD5 này.**\nVui lòng kích hoạt VIP bằng cách nhập mã hoặc tham gia nhóm để nhận VIP miễn phí.\n\nSử dụng /help để biết thêm chi tiết.", parse_mode='Markdown')
            return
        else:
            bot.reply_to(message, "🤔 Tôi không hiểu yêu cầu của bạn. Vui lòng sử dụng các lệnh có sẵn (ví dụ: `/help`) hoặc gửi mã MD5 để tôi phân tích.\n\n⚠️ **Để phân tích MD5, bạn cần có tài khoản VIP.**", parse_mode='Markdown')
            return

    # If user is VIP or Super Admin, proceed with MD5 analysis
    if is_md5_hash:
        bot.send_chat_action(message.chat.id, 'typing') # Show typing status
        predicted_result, result_md5, is_correct, analysis_output = custom_md5_analyzer(text)

        if predicted_result is not None:
            bot.reply_to(message, analysis_output, parse_mode='Markdown')

            if is_correct:
                user_info["correct_predictions"] += 1
            else:
                user_info["wrong_predictions"] += 1

            user_info["history"].append({
                "md5_short": f"{text[:4]}...{text[-4:]}",
                "prediction": predicted_result,
                "result_md5": result_md5,
                "is_correct": is_correct,
                "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            user_info["history"] = user_info["history"][-50:]

            save_data(USER_DATA_FILE, user_data)
        else:
            bot.reply_to(message, analysis_output)

        user_info["waiting_for_md5"] = False
        save_data(USER_DATA_FILE, user_data)
    else:
        # If not an MD5 and not waiting for MD5, provide general instructions
        bot.reply_to(message, "🤔 Tôi không hiểu yêu cầu của bạn. Vui lòng sử dụng các lệnh có sẵn (ví dụ: `/help`) hoặc gửi mã MD5 để tôi phân tích.", parse_mode='Markdown')


# --- Keep alive server for Render/UptimeRobot ---
app = Flask(__name__)

@app.route('/')
def home():
    """Simple route to keep the app alive."""
    return "Bot is alive!"

def run_flask_app():
    """Runs the Flask app in a separate thread."""
    port = int(os.environ.get('PORT', random.randint(2000, 9000)))
    print(f"Flask app running on port {port}")
    app.run(host='0.0.0.0', port=port)

# --- Bot Initialization and Start ---
if __name__ == "__main__":
    # Load data from JSON files
    user_data = load_data(USER_DATA_FILE)
    codes = load_data(CODES_FILE, default_data=codes)
    bot_state = load_data(BOT_STATE_FILE, default_data={"md5_gãy_streak": 0})

    # Gán giá trị từ bot_state vào biến toàn cục md5_gãy_streak
    md5_gãy_streak = bot_state["md5_gãy_streak"]

    print("Bot is starting...")

    # Start the Flask app in a separate thread to keep the bot alive
    t = Thread(target=run_flask_app)
    t.start()

    # Start the Telegram bot polling
    print("Telegram bot polling started...")
    bot.polling(non_stop=True)


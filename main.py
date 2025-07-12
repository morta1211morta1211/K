# main.py

import discord
from discord.ext import commands
import config
from flask import Flask, render_template, request, redirect, url_for
import threading
import asyncio

# --- إعدادات بوت ديسكورد ---
# تعريف الصلاحيات (Intents) التي سيحتاجها البوت
# مهم جدًا: يجب تفعيل هذه الصلاحيات في بوابة مطوري ديسكورد أيضًا
# (تحت قسم Bot -> Privileged Gateway Intents)
intents = discord.Intents.default()
intents.message_content = True  # لاستقبال محتوى الرسائل (لأوامر البوت النصية)
intents.members = True          # لإدارة الأعضاء (طرد، حظر)
intents.guilds = True           # للحصول على معلومات السيرفرات والقنوات والرتب

# تعريف البوت وتحديد البادئة (prefix) للأوامر
# هنا، الأوامر ستبدأ بـ '!', مثل '!hello'
bot = commands.Bot(command_prefix='!', intents=intents)

# --- إعدادات تطبيق Flask ---
app = Flask(__name__)

# --- حدث عند تشغيل البوت بنجاح ---
@bot.event
async def on_ready():
    print(f'تم تسجيل دخول البوت بنجاح باسم: {bot.user.name} ({bot.user.id})')
    print('-----------------------------------------')
    print('البوت جاهز لاستقبال الأوامر.')

# --- أوامر البوت الأساسية (يمكنك إضافة المزيد هنا) ---
@bot.command()
async def hello(ctx):
    """
    يرد البوت بتحية بسيطة.
    مثال للاستخدام: !hello
    """
    await ctx.send(f'أهلاً بك يا {ctx.author.display_name}!')

# --- وظائف تنفيذ الأوامر من لوحة التحكم (Dashboard) ---

async def delete_all_channels_func(guild_id):
    """يحذف جميع القنوات في السيرفر المحدد."""
    guild = bot.get_guild(guild_id)
    if not guild:
        return "السيرفر غير موجود أو البوت ليس فيه."

    deleted_count = 0
    # يمكن ترك قناة واحدة لضمان بقاء السيرفر قابلاً للاستخدام
    # على سبيل المثال، اترك أول قناة نصية يجدها البوت
    # ولكن لغرض المسح الكامل، سنحاول حذف الكل
    for channel in guild.channels:
        try:
            await channel.delete()
            deleted_count += 1
        except discord.Forbidden:
            print(f"لا أستطيع حذف القناة {channel.name} في سيرفر {guild.name} بسبب نقص الصلاحيات.")
        except Exception as e:
            print(f"حدث خطأ أثناء حذف القناة {channel.name} في سيرفر {guild.name}: {e}")
    return f"تم حذف {deleted_count} قناة في سيرفر {guild.name}."

async def kick_all_members_func(guild_id):
    """يطرد جميع الأعضاء من السيرفر المحدد."""
    guild = bot.get_guild(guild_id)
    if not guild:
        return "السيرفر غير موجود أو البوت ليس فيه."

    kicked_count = 0
    for member in guild.members:
        # لا تطرد البوت نفسه أو مالك السيرفر
        if member == bot.user or member == guild.owner:
            continue
        try:
            await member.kick(reason="تم الطرد من لوحة التحكم: إعادة تعيين السيرفر")
            kicked_count += 1
        except discord.Forbidden:
            print(f"لا أستطيع طرد العضو {member.display_name} في سيرفر {guild.name} بسبب نقص الصلاحيات.")
        except Exception as e:
            print(f"حدث خطأ أثناء طرد العضو {member.display_name} في سيرفر {guild.name}: {e}")
    return f"تم طرد {kicked_count} عضو من سيرفر {guild.name}."

async def delete_all_roles_func(guild_id):
    """يحذف جميع الرتب المخصصة في السيرفر المحدد."""
    guild = bot.get_guild(guild_id)
    if not guild:
        return "السيرفر غير موجود أو البوت ليس فيه."

    deleted_count = 0
    # الحصول على رتبة البوت لتجنب حذفها
    bot_member = guild.get_member(bot.user.id)
    bot_roles_ids = [role.id for role in bot_member.roles] if bot_member else []

    # فرز الرتب من الأعلى إلى الأقل للحذف (مهم لتجنب الأخطاء)
    sorted_roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)

    for role in sorted_roles:
        # لا تحذف رتبة @everyone ولا رتبة البوت
        if role.name == '@everyone' or role.id in bot_roles_ids:
            continue
        try:
            await role.delete()
            deleted_count += 1
        except discord.Forbidden:
            print(f"لا أستطيع حذف الرتبة {role.name} في سيرفر {guild.name} بسبب نقص الصلاحيات.")
        except Exception as e:
            print(f"حدث خطأ أثناء حذف الرتبة {role.name} في سيرفر {guild.name}: {e}")
    return f"تم حذف {deleted_count} رتبة من سيرفر {guild.name}."

# --- مسارات Flask (واجهة الويب) ---

@app.route('/')
async def index():
    """الصفحة الرئيسية للداشبورد تعرض قائمة السيرفرات."""
    guilds = []
    # تأكد أن البوت جاهز قبل محاولة الوصول إلى السيرفرات
    if bot.is_ready():
        for guild in bot.guilds:
            guilds.append({'id': guild.id, 'name': guild.name})
    return await asyncio.to_thread(render_template, 'index.html', guilds=guilds)

@app.route('/server/<int:guild_id>', methods=['GET', 'POST'])
async def server_control(guild_id):
    """صفحة التحكم بسيرفر محدد."""
    guild = bot.get_guild(guild_id)
    if not guild:
        return "السيرفر غير موجود أو البوت ليس فيه.", 404

    result_message = None
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'delete_channels':
            result_message = await delete_all_channels_func(guild_id)
        elif action == 'kick_members':
            result_message = await kick_all_members_func(guild_id)
        elif action == 'delete_roles':
            result_message = await delete_all_roles_func(guild_id)
        elif action == 'delete_emojis_stickers':
            # هذه العملية لا يمكن للبوت القيام بها مباشرة عبر API ديسكورد
            result_message = "لا يمكن للبوت حذف الإيموجي والستيكرات مباشرة عبر API ديسكورد. يجب عليك حذفها يدويًا من إعدادات السيرفر -> الإيموجي/الملصقات."
        else:
            result_message = "إجراء غير معروف."

    return await asyncio.to_thread(render_template, 'server_control.html', guild=guild, result=result_message)

# --- وظيفة لتشغيل البوت في خيط منفصل ---
def run_bot():
    """تشغيل بوت ديسكورد."""
    try:
        bot.run(config.BOT_TOKEN)
    except Exception as e:
        print(f"خطأ في تشغيل البوت: {e}")

# --- تشغيل Flask والبوت ---
if __name__ == '__main__':
    # تشغيل البوت في خيط منفصل للسماح لتطبيق Flask بالعمل
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    # تشغيل تطبيق Flask
    # يمكنك تغيير المنفذ (port) إذا كان 5000 مستخدمًا
    app.run(host='0.0.0.0', port=5000, debug=True) # debug=True مفيد للتطوير
